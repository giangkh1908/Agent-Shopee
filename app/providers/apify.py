"""Provider Apify (Zen Studio Shopee Product Detail) — nguồn giá đối thủ chính.

Chạy actor ở chế độ async để biết chắc run_id + chi phí thật:
  POST /v2/acts/{actor}/runs → poll /v2/actor-runs/{id} → GET /v2/datasets/{id}/items

Kiểm chứng thật 2026-09-29: 8/8 SKU, 186 field/SKU, waterfall khớp cardDisplayPrice.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from .. import db
from ..config import APIFY_ACTOR_ID, APIFY_BASE, APIFY_TOKEN

RUN_TIMEOUT_SECS = 900
POLL_INTERVAL_SECS = 3
TERMINAL_STATES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}


class ProviderError(RuntimeError):
    pass


class ProviderLimitError(ProviderError):
    """Actor từ chối chạy vì hết lượt miễn phí — user cần nhập key Apify khác."""


def current_token() -> str:
    """Key nhập từ web (lưu DB) ưu tiên hơn APIFY_TOKEN trong .env; đổi có hiệu lực ngay, không cần restart."""
    return (db.get_setting("apify_token") or APIFY_TOKEN or "").strip()


def verify_token(token: str) -> str:
    """Trả username Apify nếu key hợp lệ, ngược lại ProviderError."""
    try:
        r = httpx.get(f"{APIFY_BASE}/users/me", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    except httpx.HTTPError as exc:
        raise ProviderError(f"Không kết nối được Apify: {exc}") from exc
    if r.status_code != 200:
        raise ProviderError("Key Apify không hợp lệ")
    return (r.json().get("data") or {}).get("username", "")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {current_token()}"}


def _limit_reached(run_id: str) -> bool:
    try:
        log = httpx.get(f"{APIFY_BASE}/actor-runs/{run_id}/log", headers=_headers(), timeout=30).text
    except httpx.HTTPError:
        return False
    return "limit reached" in log.lower()


def fetch_items(urls: list[str], *, timeout: int = RUN_TIMEOUT_SECS) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Chạy actor, trả (items, meta có run_id/chi phí thật)."""
    if not current_token():
        raise ProviderLimitError("Chưa có key Apify — bấm 🔑 Apify key để nhập")
    if not urls:
        return [], {"url_count": 0}

    body = {
        "startUrls": [{"url": url} for url in urls],
        "includeReviews": False,
        "maxItems": len(urls) + 2,
    }

    try:
        start = httpx.post(
            f"{APIFY_BASE}/acts/{APIFY_ACTOR_ID}/runs",
            params={"timeout": timeout},
            headers={**_headers(), "Content-Type": "application/json"},
            json=body,
            timeout=60,
        )
    except httpx.HTTPError as exc:
        raise ProviderError(f"Không khởi động được run Apify: {exc}") from exc

    if start.status_code >= 400:
        raise ProviderError(f"Apify trả HTTP {start.status_code} khi start run: {start.text[:300]}")

    run = start.json().get("data") or {}
    run_id = run.get("id")
    dataset_id = run.get("defaultDatasetId")
    if not run_id or not dataset_id:
        raise ProviderError(f"Apify không trả run id/dataset: {str(run)[:300]}")

    status = run.get("status", "READY")
    deadline = time.monotonic() + timeout
    usage: dict[str, Any] = {}
    while status not in TERMINAL_STATES:
        if time.monotonic() > deadline:
            raise ProviderError(f"Run {run_id} quá thời gian chờ ({timeout}s), trạng thái {status}")
        time.sleep(POLL_INTERVAL_SECS)
        try:
            poll = httpx.get(f"{APIFY_BASE}/actor-runs/{run_id}", headers=_headers(), timeout=60)
            poll.raise_for_status()
            data = poll.json().get("data") or {}
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Poll run {run_id} thất bại: {exc}") from exc
        status = data.get("status", status)
        usage = {
            "usage_total_usd": data.get("usageTotalUsd"),
            "charged_events": data.get("chargedEventCounts"),
            "finished_at": data.get("finishedAt"),
        }

    if status != "SUCCEEDED":
        raise ProviderError(f"Run {run_id} kết thúc với trạng thái {status}")

    try:
        items_response = httpx.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"format": "json", "clean": "true"},
            headers=_headers(),
            timeout=120,
        )
        items_response.raise_for_status()
        items = items_response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError(f"Không tải được dataset {dataset_id}: {exc}") from exc

    if not isinstance(items, list):
        raise ProviderError(f"Dataset trả về {type(items).__name__}, cần list")

    if not items and _limit_reached(run_id):
        raise ProviderLimitError("Key Apify này đã hết lượt miễn phí của actor (Free tier limit reached) — nhập key khác")

    meta = {
        "actor": APIFY_ACTOR_ID,
        "run_id": run_id,
        "dataset_id": dataset_id,
        "status": status,
        "url_count": len(urls),
        "item_count": len(items),
        **usage,
    }
    return items, meta
