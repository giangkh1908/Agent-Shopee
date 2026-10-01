"""Agent-Shopee MVP — FastAPI + SQLite + UI 1 trang. Dùng cá nhân, không auth."""
from __future__ import annotations

import base64
import logging
import secrets
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, normalize, parsing
from .config import APIFY_ACTOR_ID, APIFY_TOKEN, APP_PASSWORD, APP_USER, WEB_DIR
from .providers import apify

log = logging.getLogger("agent_shopee")

app = FastAPI(title="Agent-Shopee MVP", version="0.1.0")
# Cho phép UI mở từ Live Server / file:// gọi API này; chỉ localhost nên không mở ra ngoài.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|null",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    """Bật khi đặt APP_PASSWORD (deploy public); để trống thì bỏ qua (chạy local)."""
    if not APP_PASSWORD or request.url.path == "/api/health" or request.method == "OPTIONS":
        return await call_next(request)
    header = request.headers.get("authorization", "")
    if header.lower().startswith("basic "):
        try:
            user, _, pw = base64.b64decode(header[6:]).decode("utf-8").partition(":")
        except Exception:  # noqa: BLE001
            user = pw = ""
        if secrets.compare_digest(user, APP_USER) and secrets.compare_digest(pw, APP_PASSWORD):
            return await call_next(request)
    return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="Agent-Shopee"'})


db.init()


class ScanRequest(BaseModel):
    text: str | None = Field(default=None, description="Dán nhiều link, cách nhau bằng dòng trắng/dấu phẩy")
    urls: list[str] | None = None


class UpdateMyPriceRequest(BaseModel):
    my_price: float | None = None
    my_cost: float | None = None
    my_link: str | None = None


class FetchMyProductRequest(BaseModel):
    item_id: int
    my_link: str


class AnalyzePriceRequest(BaseModel):
    item_id: int
    my_price: float | None = None
    my_cost: float | None = None
    my_link: str | None = None

def _scan_targets(targets: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    run_id = db.start_run(kind, len(targets))
    by_item = {int(t["item_id"]): t for t in targets}
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    provider_meta: dict[str, Any] = {}

    try:
        items, provider_meta = apify.fetch_items([str(t["url"]) for t in targets])
    except apify.ProviderError as exc:
        db.finish_run(run_id, ok=0, failed=len(targets), status="failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    for item in items:
        item_id = item.get("itemId")
        target = by_item.get(int(item_id)) if item_id else None
        if target is None:
            target = {
                "item_id": item_id,
                "shop_id": item.get("shopId"),
                "market": None,
                "url": item.get("url"),
            }
        try:
            snapshot = normalize.to_snapshot(
                item, target=target, source="apify:zen-studio", run_id=provider_meta.get("run_id")
            )
            db.upsert_item(snapshot)
            db.insert_snapshot(snapshot)
            previous = db.history(int(snapshot["item_id"]), limit=2)
            prev = previous[0] if len(previous) > 1 else None
            card = normalize.item_card(snapshot, prev, None)
            results.append(card)
        except Exception as exc:  # noqa: BLE001 — 1 SKU lỗi không làm fail cả run
            log.exception("normalize failed for item %s", item_id)
            errors.append({"input": str(item.get("url") or item_id), "error": f"chuẩn hoá thất bại: {exc}"})

    returned = {int(r["item_id"]) for r in results}
    for item_id, target in by_item.items():
        if item_id not in returned:
            errors.append({"input": str(target["url"]), "error": "provider không trả về SKU này"})

    db.finish_run(
        run_id,
        ok=len(results),
        failed=len(errors),
        status="done",
        provider_run_id=provider_meta.get("run_id"),
        usage_usd=provider_meta.get("usage_total_usd"),
    )
    return {
        "run_id": run_id,
        "provider": provider_meta,
        "ok": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "provider": APIFY_ACTOR_ID,
        "token_set": bool(APIFY_TOKEN),
        "items": len(db.list_items()),
        "snapshots": db.snapshot_count(),
    }


@app.post("/api/scan")
def scan(request: ScanRequest) -> dict[str, Any]:
    raw_text = request.text or "\n".join(request.urls or [])
    targets, errors = parsing.parse_many(raw_text)
    if not targets:
        raise HTTPException(status_code=400, detail={"message": "Không có link Shopee hợp lệ", "errors": errors})
    payload = _scan_targets(targets, kind="scan_paste")
    payload["errors"] = errors + payload["errors"]
    payload["parsed"] = len(targets)
    return payload


@app.post("/api/scan/all")
def scan_all() -> dict[str, Any]:
    rows = db.list_items()
    targets = [
        {"item_id": row["item_id"], "shop_id": row["shop_id"], "market": row.get("market"), "url": row["url"]}
        for row in rows
        if row.get("url")
    ]
    if not targets:
        raise HTTPException(status_code=400, detail="Chưa có SKU nào để quét lại")
    return _scan_targets(targets, kind="scan_all")


@app.get("/api/items")
def items() -> dict[str, Any]:
    latest = db.latest_snapshots()
    previous = db.previous_snapshots()
    rows = {int(row["item_id"]): row for row in db.list_items()}
    cards = [
        normalize.item_card(snapshot, previous.get(item_id), rows.get(item_id))
        for item_id, snapshot in sorted(latest.items())
    ]
    cards.sort(key=lambda card: (card.get("shop_name") or "", card.get("name") or ""))
    return {"count": len(cards), "items": cards}


@app.get("/api/items/{item_id}/history")
def item_history(item_id: int, limit: int = 200) -> dict[str, Any]:
    rows = db.history(item_id, limit=limit)
    if not rows:
        raise HTTPException(status_code=404, detail="Chưa có snapshot cho SKU này")
    return {
        "item_id": item_id,
        "history": [
            {
                "captured_at": row["captured_at"],
                "final_price": row["final_price"],
                "promo_price": row["promo_price"],
                "stock": row["stock"],
                "is_flash_sale": row["is_flash_sale"],
                "shop_voucher": row["shop_voucher"],
                "platform_voucher": row["platform_voucher"],
                "rating_count": row["rating_count"],
            }
            for row in rows
        ],
    }


@app.get("/api/items/{item_id}/raw")
def item_raw(item_id: int) -> dict[str, Any]:
    rows = db.history(item_id, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Chưa có snapshot cho SKU này")
    snapshot = rows[-1]
    return {
        "item_id": item_id,
        "captured_at": snapshot["captured_at"],
        "source": snapshot["source"],
        "raw": snapshot.get("raw"),
    }




@app.post("/api/items/{item_id}/my-pricing")
def update_pricing(item_id: int, req: UpdateMyPriceRequest) -> dict[str, Any]:
    db.update_my_price_and_cost(item_id, req.my_price, req.my_cost, req.my_link)
    return {"ok": True, "item_id": item_id, "my_price": req.my_price, "my_cost": req.my_cost, "my_link": req.my_link}


@app.post("/api/items/{item_id}/fetch-my-product")
def fetch_my_product(item_id: int, req: FetchMyProductRequest) -> dict[str, Any]:
    """Cào sản phẩm shop của bạn từ link thật bằng Apify để lấy giá cuối + voucher + tồn kho"""
    try:
        target = parsing.parse_url(req.my_link)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Link sản phẩm không hợp lệ: {exc}")

    try:
        items, meta = apify.fetch_items([req.my_link])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Không cào được dữ liệu link của bạn: {exc}")

    if not items:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin sản phẩm từ link này")

    item_data = items[0]
    snap = normalize.to_snapshot(item_data, target=target, source="apify:my-shop", run_id=meta.get("run_id"))
    
    # Lưu vào database nếu chưa có để lưu lịch sử
    db.upsert_item(snap)
    db.insert_snapshot(snap)

    # Cập nhật giá tự động cho item_id đối thủ
    my_final_price = snap.get("final_price") or snap.get("promo_price") or snap.get("price_min")
    items_dict = {int(r["item_id"]): r for r in db.list_items()}
    current_item = items_dict.get(item_id, {})
    my_cost = current_item.get("my_cost")

    db.update_my_price_and_cost(item_id, my_final_price, my_cost, req.my_link)

    return {
        "ok": True,
        "my_final_price": my_final_price,
        "my_cost": my_cost,
        "my_product": snap,
    }


@app.post("/api/analyze-pricing")
def analyze_pricing_endpoint(req: AnalyzePriceRequest) -> dict[str, Any]:
    from .ai_copilot import analyze_pricing
    snaps = db.history(req.item_id, limit=1)
    if not snaps:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm đối thủ")
    snap = snaps[-1]
    comp_final = snap.get("final_price") or snap.get("promo_price") or snap.get("price_min") or 0.0
    items_dict = {int(r["item_id"]): r for r in db.list_items()}
    item_info = items_dict.get(req.item_id, {})
    item_name = item_info.get("name") or snap.get("name") or f"Item #{req.item_id}"
    
    my_link = req.my_link or item_info.get("my_link")
    my_price = req.my_price or item_info.get("my_price")
    my_cost = req.my_cost or item_info.get("my_cost")

    my_product_data = None
    # Nếu có link shop của mình, kiểm tra xem đã cào snapshot của link đó chưa
    if my_link:
        try:
            my_target = parsing.parse_url(my_link)
            my_snaps = db.history(int(my_target["item_id"]), limit=1)
            if my_snaps:
                my_product_data = my_snaps[-1]
                if not my_price:
                    my_price = my_product_data.get("final_price") or my_product_data.get("promo_price")
        except Exception:
            pass

    if not my_price or my_price <= 0:
        raise HTTPException(status_code=400, detail="Vui lòng nhập 'Giá của bạn' hoặc dán 'Link của bạn' để AI có dữ liệu phân tích")

    # Lưu lại my_price, my_cost, my_link
    db.update_my_price_and_cost(req.item_id, my_price, my_cost, my_link)

    analysis = analyze_pricing(
        item_name=item_name,
        comp_final=comp_final,
        my_price=float(my_price),
        cost=float(my_cost) if my_cost else None,
        comp_data=snap,
        my_product_data=my_product_data
    )
    return analysis
@app.get("/api/runs")
def runs(limit: int = 20) -> dict[str, Any]:
    return {"runs": db.recent_runs(limit=limit)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


# Phục vụ toàn bộ web/ ở gốc để index.html gọi được /js/*.js (API đã đăng ký trước nên không bị che).
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
