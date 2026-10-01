"""Waterfall giá cuối — mô hình đã kiểm chứng 8/8 SKU (PLAN §2.5.2, §3.3).

final = promo_price − shop_voucher (nếu promo_price >= min_spend) − platform_voucher
Đối chiếu chéo với `cardDisplayPrice` mà Shopee hiển thị trên card sản phẩm.
Toàn bộ tính bằng float tiền tệ đã làm tròn 2 chữ số; không dùng LLM.
"""
from __future__ import annotations

from typing import Any

EPS = 0.011


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def _round(value: float | None) -> float | None:
    return None if value is None else round(value + 1e-9, 2)


def compute_final(item: dict[str, Any]) -> dict[str, Any]:
    """Trả về final_price, breakdown, confidence, card_match."""
    promo = _num(item.get("promoPrice")) or _num(item.get("priceMin")) or _num(item.get("price"))
    price_min = _num(item.get("priceMin")) or _num(item.get("price"))
    base = promo if promo is not None else price_min

    breakdown: list[dict[str, Any]] = [
        {
            "step": "promo_price",
            "label": "Giá đang bán (promo)",
            "amount": _round(base),
        }
    ]
    deducted = 0.0

    if base is not None:
        for key, label in (("shopVoucher", "Voucher shop"), ("platformVoucher", "Voucher Shopee")):
            voucher = item.get(key)
            if not isinstance(voucher, dict):
                continue
            discount = _num(voucher.get("voucherDiscount")) or 0.0
            min_spend = _num(voucher.get("minSpend")) or 0.0
            entry: dict[str, Any] = {
                "step": key,
                "label": label,
                "code": voucher.get("voucherCode"),
                "discount": _round(discount),
                "min_spend": _round(min_spend),
                "applied": bool(discount > 0 and base >= min_spend),
            }
            if entry["applied"]:
                deducted += discount
                entry["amount"] = _round(-discount)
            elif discount > 0:
                entry["reason"] = f"chưa đủ min_spend {min_spend:g}"
            breakdown.append(entry)

    calc = None if base is None else max(0.0, base - deducted)

    card = _num(item.get("cardDisplayPrice"))
    if calc is not None and card is not None and abs(card - calc) <= EPS:
        confidence, final = "exact", card
    elif card is not None and calc is not None:
        confidence, final = "card_override", card
    elif card is not None:
        confidence, final = "card_only", card
    elif calc is not None:
        confidence, final = "partial", calc
    else:
        confidence, final = "unknown", None

    if final is not None:
        breakdown.append({"step": "final_price", "label": "Giá cuối", "amount": _round(final)})

    return {
        "final_price": _round(final),
        "final_price_calc": _round(calc),
        "final_confidence": confidence,
        "card_match": int(bool(calc is not None and card is not None and abs(card - calc) <= EPS)),
        "breakdown": breakdown,
    }


def delta(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    """So sánh 2 snapshot cùng item."""
    if not previous:
        return {"is_new": True}
    cur_final, prev_final = _num(current.get("final_price")), _num(previous.get("final_price"))
    change = None
    pct = None
    if cur_final is not None and prev_final not in (None, 0):
        change = _round(cur_final - prev_final)
        pct = round((cur_final - prev_final) / prev_final * 100, 2)
    cur_stock, prev_stock = current.get("stock"), previous.get("stock")
    return {
        "is_new": False,
        "prev_final_price": _round(prev_final),
        "final_change": change,
        "final_change_pct": pct,
        "flash_started": bool(current.get("is_flash_sale")) and not bool(previous.get("is_flash_sale")),
        "flash_ended": bool(previous.get("is_flash_sale")) and not bool(current.get("is_flash_sale")),
        "voucher_changed": (current.get("shop_voucher") or {}) != (previous.get("shop_voucher") or {})
        or (current.get("platform_voucher") or {}) != (previous.get("platform_voucher") or {}),
        "stock_change": None if cur_stock is None or prev_stock is None else int(cur_stock) - int(prev_stock),
        "restocked": bool(cur_stock and prev_stock == 0),
        "out_of_stock": cur_stock == 0 and bool(prev_stock),
    }
