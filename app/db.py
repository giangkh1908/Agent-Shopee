"""SQLite: schema + truy vấn. Dùng stdlib sqlite3, không ORM."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from .config import DB_PATH

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


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    """Connection + commit, luôn đóng (tránh rò kết nối trong server chạy dài)."""
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
        conn.executescript(SCHEMA)
        _migrate(conn)


def start_run(kind: str, url_count: int) -> int:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO runs (started_at, kind, url_count, status) VALUES (?, ?, ?, 'running')",
            (now_iso(), kind, url_count),
        )
        return int(cur.lastrowid)


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
    payload = {key: snapshot.get(key) for key in SNAPSHOT_COLUMNS}
    columns = ", ".join(SNAPSHOT_COLUMNS)
    placeholders = ", ".join(f":{key}" for key in SNAPSHOT_COLUMNS)
    with db() as conn:
        cur = conn.execute(f"INSERT INTO snapshots ({columns}) VALUES ({placeholders})", payload)
        return int(cur.lastrowid)


def _row_to_snapshot(row: sqlite3.Row) -> dict[str, Any]:
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
        return int(conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])


def recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]
