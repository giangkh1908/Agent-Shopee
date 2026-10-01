"""Schema + truy vấn. Postgres (pg8000) nếu có PG_DSN, ngược lại SQLite stdlib. Không ORM."""
from __future__ import annotations

import json
import queue
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import unquote, urlparse

from .config import DB_PATH, PG_DSN

USE_PG = bool(PG_DSN)

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS items (
  item_id     INTEGER PRIMARY KEY,
  shop_id     INTEGER NOT NULL,
  market      TEXT,
  name        TEXT,
  image       TEXT,
  url         TEXT,
  shop_name   TEXT,
  currency    TEXT,
  added_at    TEXT NOT NULL,
  last_scan_at TEXT,
  active      INTEGER NOT NULL DEFAULT 1,
  my_price    REAL,
  my_cost     REAL,
  my_link     TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id            INTEGER NOT NULL,
  shop_id            INTEGER,
  market             TEXT,
  captured_at        TEXT NOT NULL,
  source             TEXT NOT NULL,
  provider_run_id    TEXT,
  currency           TEXT,
  price_min          REAL,
  price_max          REAL,
  price_before_discount REAL,
  promo_price        REAL,
  strikethrough_price REAL,
  card_display_price REAL,
  discount_percent   REAL,
  final_price        REAL,
  final_price_calc   REAL,
  final_confidence   TEXT,
  card_match         INTEGER,
  breakdown          TEXT,
  shop_voucher       TEXT,
  platform_voucher   TEXT,
  ads_voucher        TEXT,
  has_voucher        INTEGER,
  is_flash_sale      INTEGER,
  stock              INTEGER,
  is_stock_hidden    INTEGER,
  rating             REAL,
  rating_count       INTEGER,
  liked_count        INTEGER,
  comment_count      INTEGER,
  sold               INTEGER,
  sold_displayed     TEXT,
  variants           TEXT,
  seller             TEXT,
  raw                TEXT
);

CREATE INDEX IF NOT EXISTS idx_snap_item_time ON snapshots(item_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS runs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at  TEXT NOT NULL,
  finished_at TEXT,
  kind        TEXT NOT NULL,
  url_count   INTEGER NOT NULL DEFAULT 0,
  ok_count    INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'running',
  error       TEXT,
  provider_run_id TEXT,
  usage_usd   REAL
);
"""

# Cùng schema cho Postgres: bỏ PRAGMA, id tự tăng, ID Shopee vượt int32 nên dùng BIGINT.
PG_SCHEMA = (
    SCHEMA.replace("PRAGMA journal_mode=WAL;", "")
    .replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
    .replace("item_id     INTEGER PRIMARY KEY", "item_id     BIGINT PRIMARY KEY")
    .replace("item_id            INTEGER NOT NULL", "item_id            BIGINT NOT NULL")
    .replace("shop_id     INTEGER NOT NULL", "shop_id     BIGINT NOT NULL")
    .replace("shop_id            INTEGER", "shop_id            BIGINT")
    .replace(" REAL", " DOUBLE PRECISION")
)

SNAPSHOT_COLUMNS = [
    "item_id", "shop_id", "market", "captured_at", "source", "provider_run_id", "currency",
    "price_min", "price_max", "price_before_discount", "promo_price", "strikethrough_price",
    "card_display_price", "discount_percent", "final_price", "final_price_calc",
    "final_confidence", "card_match", "breakdown", "shop_voucher", "platform_voucher",
    "ads_voucher", "has_voucher", "is_flash_sale", "stock", "is_stock_hidden",
    "rating", "rating_count", "liked_count", "comment_count", "sold", "sold_displayed",
    "variants", "seller", "raw",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_pool: queue.LifoQueue = queue.LifoQueue(maxsize=5)


def _pg_connect() -> Any:
    import pg8000.dbapi

    u = urlparse(PG_DSN)
    return pg8000.dbapi.connect(
        user=unquote(u.username or ""), password=unquote(u.password or ""),
        host=u.hostname, port=u.port or 5432, database=(u.path or "/").lstrip("/"),
        ssl_context=True, timeout=30,
    )


def _to_pg(sql: str, params: Any) -> tuple[str, list[Any]]:
    """Đổi cú pháp ? / :name của sqlite3 sang %s + list tham số cho pg8000."""
    if isinstance(params, dict):
        names: list[str] = []
        sql = re.sub(r"(?<![:\w]):([A-Za-z_]\w*)", lambda m: names.append(m.group(1)) or "%s", sql)
        return sql, [params[n] for n in names]
    return sql.replace("?", "%s"), list(params or [])


class _PgCursor:
    def __init__(self, cur: Any) -> None:
        self._cur = cur
        self._cols = [c[0] for c in cur.description] if cur.description else []

    def fetchone(self) -> dict[str, Any] | None:
        row = self._cur.fetchone()
        return dict(zip(self._cols, row)) if row is not None else None

    def fetchall(self) -> list[dict[str, Any]]:
        return [dict(zip(self._cols, r)) for r in self._cur.fetchall()]


class _PgConn:
    """Cho code truy vấn dùng chung cú pháp với sqlite3 (execute -> fetchone/fetchall)."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def execute(self, sql: str, params: Any = None) -> _PgCursor:
        sql, args = _to_pg(sql, params)
        cur = self._conn.cursor()
        cur.execute(sql, args)
        return _PgCursor(cur)


@contextmanager
def _pg_session() -> Iterator[_PgConn]:
    try:
        conn = _pool.get_nowait()
    except queue.Empty:
        conn = _pg_connect()
    try:
        yield _PgConn(conn)
        conn.commit()
    except BaseException:
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001 — kết nối hỏng thì bỏ, lần sau mở mới
            conn = None
        raise
    finally:
        if conn is not None:
            try:
                _pool.put_nowait(conn)
            except queue.Full:
                conn.close()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db() -> Iterator[Any]:
    """Connection + commit, luôn trả/đóng (tránh rò kết nối trong server chạy dài)."""
    if USE_PG:
        with _pg_session() as conn:
            yield conn
        return
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Thêm cột mới cho DB đã tạo trước đó (giữ nguyên dữ liệu cũ)."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
    for column, ddl in (("provider_run_id", "TEXT"), ("usage_usd", "REAL")):
        if column not in existing:
            conn.execute(f"ALTER TABLE runs ADD COLUMN {column} {ddl}")

    existing = {row["name"] for row in conn.execute("PRAGMA table_info(snapshots)")}
    for column, ddl in (("shop_id", "INTEGER"), ("market", "TEXT")):
        if column not in existing:
            conn.execute(f"ALTER TABLE snapshots ADD COLUMN {column} {ddl}")

    existing = {row["name"] for row in conn.execute("PRAGMA table_info(items)")}
    for column, ddl in (("my_price", "REAL"), ("my_cost", "REAL"), ("my_link", "TEXT")):
        if column not in existing:
            conn.execute(f"ALTER TABLE items ADD COLUMN {column} {ddl}")


def init() -> None:
    with db() as conn:
        if USE_PG:
            for stmt in PG_SCHEMA.split(";"):
                if stmt.strip():
                    conn.execute(stmt)
            return
        conn.executescript(SCHEMA)
        _migrate(conn)


def start_run(kind: str, url_count: int) -> int:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO runs (started_at, kind, url_count, status) VALUES (?, ?, ?, 'running') RETURNING id",
            (now_iso(), kind, url_count),
        )
        return int(cur.fetchone()["id"])


def finish_run(
    run_id: int,
    *,
    ok: int,
    failed: int,
    status: str = "done",
    error: str | None = None,
    provider_run_id: str | None = None,
    usage_usd: float | None = None,
) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE runs SET finished_at=?, ok_count=?, failed_count=?, status=?, error=?, "
            "provider_run_id=?, usage_usd=? WHERE id=?",
            (now_iso(), ok, failed, status, error, provider_run_id, usage_usd, run_id),
        )


def upsert_item(snapshot: dict[str, Any]) -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO items (item_id, shop_id, market, name, image, url, shop_name, currency, added_at, last_scan_at, active)
            VALUES (:item_id, :shop_id, :market, :name, :image, :url, :shop_name, :currency, :now, :now, 1)
            ON CONFLICT(item_id) DO UPDATE SET
              shop_id=excluded.shop_id,
              name=COALESCE(excluded.name, items.name),
              image=COALESCE(excluded.image, items.image),
              url=COALESCE(excluded.url, items.url),
              shop_name=COALESCE(excluded.shop_name, items.shop_name),
              currency=COALESCE(excluded.currency, items.currency),
              last_scan_at=excluded.last_scan_at,
              active=1
            """,
            {**snapshot, "now": now_iso()},
        )


def update_my_price_and_cost(item_id: int, my_price: float | None, my_cost: float | None, my_link: str | None = None) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE items SET my_price = ?, my_cost = ?, my_link = COALESCE(?, my_link) WHERE item_id = ?",
            (my_price, my_cost, my_link, item_id)
        )


def insert_snapshot(snapshot: dict[str, Any]) -> int:
    payload = {key: int(v) if isinstance(v := snapshot.get(key), bool) else v for key in SNAPSHOT_COLUMNS}
    columns = ", ".join(SNAPSHOT_COLUMNS)
    placeholders = ", ".join(f":{key}" for key in SNAPSHOT_COLUMNS)
    with db() as conn:
        cur = conn.execute(f"INSERT INTO snapshots ({columns}) VALUES ({placeholders}) RETURNING id", payload)
        return int(cur.fetchone()["id"])


def _row_to_snapshot(row: Any) -> dict[str, Any]:
    data = dict(row)
    for key in ("breakdown", "shop_voucher", "platform_voucher", "ads_voucher", "variants", "seller", "raw"):
        if data.get(key):
            try:
                data[key] = json.loads(data[key])
            except json.JSONDecodeError:
                pass
    return data


def latest_snapshots(limit: int = 500) -> dict[int, dict[str, Any]]:
    """Snapshot mới nhất của mỗi item."""
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.* FROM snapshots s
            JOIN (SELECT item_id, MAX(id) AS max_id FROM snapshots GROUP BY item_id) t
              ON t.item_id = s.item_id AND t.max_id = s.id
            ORDER BY s.captured_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {int(row["item_id"]): _row_to_snapshot(row) for row in rows}


def previous_snapshots(limit: int = 500) -> dict[int, dict[str, Any]]:
    """Snapshot áp chót của mỗi item (để tính delta)."""
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.* FROM snapshots s
            JOIN (
              SELECT item_id, MAX(id) AS max_id FROM snapshots
              WHERE id NOT IN (SELECT MAX(id) FROM snapshots GROUP BY item_id)
              GROUP BY item_id
            ) t ON t.item_id = s.item_id AND t.max_id = s.id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {int(row["item_id"]): _row_to_snapshot(row) for row in rows}


def history(item_id: int, limit: int = 200) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE item_id=? ORDER BY id DESC LIMIT ?", (item_id, limit)
        ).fetchall()
    return [_row_to_snapshot(row) for row in reversed(rows)]


def list_items() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM items WHERE active=1 ORDER BY shop_id, item_id").fetchall()
    return [dict(row) for row in rows]


def snapshot_count() -> int:
    with db() as conn:
        return int(conn.execute("SELECT COUNT(*) AS n FROM snapshots").fetchone()["n"])


def recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]
