"""Chuẩn hoá payload actor → snapshot lưu DB (mọi field có nguồn, null được phép)."""
from __future__ import annotations

import json
from typing import Any

from . import db, pricing


def _json_field(value: Any) -> Any:
    """Cột JSON trong DB là chuỗi; card trả về object đã giải mã."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _num(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _int(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def variants(item: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for model in item.get("models") or []:
        if not isinstance(model, dict):
            continue
        out.append(
            {
                "model_id": model.get("modelId"),
                "name": model.get("name"),
                "price": _num(model.get("price")),
                "price_before_discount": _num(model.get("priceBeforeDiscount")),
                "stock": _int(model.get("stock")),
            }
        )
    out.sort(key=lambda row: (row["price"] is None, row["price"] or 0))
    return out


def seller(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "shop_id": item.get("shopId"),
        "shop_name": item.get("shopName"),
        "rating": _num(item.get("shopRating")),
        "response_rate": _int(item.get("shopResponseRate")),
        "cancellation_rate": _int(item.get("shopCancellationRate")),
        "follower_count": _int(item.get("shopFollowerCount")),
        "location": item.get("shopLocation"),
        "is_official_shop": bool(item.get("isOfficialShop")),
        "is_verified_seller": bool(item.get("isVerifiedSeller")),
    }


def to_snapshot(item: dict[str, Any], *, target: dict[str, Any], source: str, run_id: str | None) -> dict[str, Any]:
    price = pricing.compute_final(item)
    images = item.get("images") or []
    variants_list = variants(item)

    return {
        "item_id": _int(item.get("itemId")) or int(target["item_id"]),
        "shop_id": _int(item.get("shopId")) or int(target["shop_id"]),
        "market": target.get("market"),
        "name": item.get("name"),
        "image": item.get("image") or (images[0] if images else None),
        "url": item.get("url") or target.get("url"),
        "shop_name": item.get("shopName"),
        "currency": item.get("currency"),
        "captured_at": item.get("scrapedAt") or db.now_iso(),
        "source": source,
        "provider_run_id": run_id,
        "price_min": _num(item.get("priceMin")),
        "price_max": _num(item.get("priceMax")),
        "price_before_discount": _num(item.get("priceBeforeDiscount")),
        "promo_price": _num(item.get("promoPrice")),
        "strikethrough_price": _num(item.get("strikethroughPrice")),
        "card_display_price": _num(item.get("cardDisplayPrice")),
        "discount_percent": _num(item.get("discountPercent")),
        "final_price": price["final_price"],
        "final_price_calc": price["final_price_calc"],
        "final_confidence": price["final_confidence"],
        "card_match": price["card_match"],
        "breakdown": json.dumps(price["breakdown"], ensure_ascii=False),
        "shop_voucher": json.dumps(item.get("shopVoucher"), ensure_ascii=False) if isinstance(item.get("shopVoucher"), dict) else None,
        "platform_voucher": json.dumps(item.get("platformVoucher"), ensure_ascii=False) if isinstance(item.get("platformVoucher"), dict) else None,
        "ads_voucher": json.dumps(item.get("adsVoucher"), ensure_ascii=False) if isinstance(item.get("adsVoucher"), dict) else None,
        "has_voucher": int(bool(item.get("hasVoucher"))),
        "is_flash_sale": int(bool(item.get("isOnFlashSale"))),
        "stock": _int(item.get("stock")),
        "is_stock_hidden": int(bool(item.get("isStockHidden"))),
        "rating": _num(item.get("rating")),
        "rating_count": _int(item.get("ratingCount")),
        "liked_count": _int(item.get("likedCount")),
        "comment_count": _int(item.get("commentCount")),
        "sold": _int(item.get("sold")),
        "sold_displayed": item.get("soldDisplayed") or item.get("historicalSold"),
        "variants": json.dumps(variants_list, ensure_ascii=False),
        "seller": json.dumps(seller(item), ensure_ascii=False),
        "raw": json.dumps(item, ensure_ascii=False),
    }


def item_card(snapshot: dict[str, Any], previous: dict[str, Any] | None, item_row: dict[str, Any] | None) -> dict[str, Any]:
    """Dữ liệu cho UI: snapshot mới nhất + delta + thông tin item."""
    return {
        "item_id": snapshot.get("item_id"),
        "shop_id": snapshot.get("shop_id"),
        "market": snapshot.get("market") or (item_row or {}).get("market"),
        "name": snapshot.get("name") or (item_row or {}).get("name"),
        "image": snapshot.get("image") or (item_row or {}).get("image"),
        "url": snapshot.get("url") or (item_row or {}).get("url"),
        "shop_name": snapshot.get("shop_name") or (item_row or {}).get("shop_name"),
        "currency": snapshot.get("currency") or (item_row or {}).get("currency"),
        "captured_at": snapshot.get("captured_at"),
        "source": snapshot.get("source"),
        "price_min": snapshot.get("price_min"),
        "price_max": snapshot.get("price_max"),
        "price_before_discount": snapshot.get("price_before_discount"),
        "promo_price": snapshot.get("promo_price"),
        "card_display_price": snapshot.get("card_display_price"),
        "discount_percent": snapshot.get("discount_percent"),
        "final_price": snapshot.get("final_price"),
        "final_price_calc": snapshot.get("final_price_calc"),
        "final_confidence": snapshot.get("final_confidence"),
        "card_match": snapshot.get("card_match"),
        "breakdown": _json_field(snapshot.get("breakdown")),
        "shop_voucher": _json_field(snapshot.get("shop_voucher")),
        "platform_voucher": _json_field(snapshot.get("platform_voucher")),
        "has_voucher": snapshot.get("has_voucher"),
        "is_flash_sale": snapshot.get("is_flash_sale"),
        "stock": snapshot.get("stock"),
        "rating": snapshot.get("rating"),
        "rating_count": snapshot.get("rating_count"),
        "liked_count": snapshot.get("liked_count"),
        "comment_count": snapshot.get("comment_count"),
        "liked_count": snapshot.get("liked_count"),
        "sold": snapshot.get("sold"),
        "variants": _json_field(snapshot.get("variants")),
        "seller": _json_field(snapshot.get("seller")),
        "my_price": (item_row or {}).get("my_price"),
        "my_cost": (item_row or {}).get("my_cost"),
        "my_link": (item_row or {}).get("my_link"),
        "delta": pricing.delta(snapshot, previous),
    }
