"""Module phân tích chiến thuật giá bằng AI Copilot dùng Google Gemini 3.8 Flash (CommandCode)."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

from .config import COMMANDCODE_API_KEY, AI_MODEL, AI_BASE_URL


def analyze_pricing(
    item_name: str,
    comp_final: float,
    my_price: float,
    cost: float | None,
    comp_data: dict[str, Any],
    my_product_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    diff = my_price - comp_final
    diff_pct = (diff / comp_final * 100) if comp_final > 0 else 0.0
    stock = comp_data.get("stock")
    is_flash = bool(comp_data.get("is_flash_sale"))
    shop_voucher = comp_data.get("shop_voucher") or {}
    platform_voucher = comp_data.get("platform_voucher") or {}

    # Thông tin chi tiết sản phẩm của bạn nếu có cào được
    my_details = ""
    if my_product_data:
        my_sv = my_product_data.get("shop_voucher") or {}
        my_pv = my_product_data.get("platform_voucher") or {}
        my_flash = bool(my_product_data.get("is_flash_sale"))
        my_stock = my_product_data.get("stock")
        my_details = f"""
- SẢN PHẨM CỦA BẠN (CÀO TỪ LINK THẬT):
  + Tên: {my_product_data.get('name', 'Shop bạn')}
  + Giá niêm yết: ${my_product_data.get('price_before_discount') or my_product_data.get('price_min')}
  + Giá promo: ${my_product_data.get('promo_price')}
  + Giá cuối thực tế khách trả: ${my_price:g}
  + Flash Sale: {'ĐANG BẬT' if my_flash else 'Không'}
  + Tồn kho: {my_stock if my_stock is not None else 'Không rõ'}
  + Voucher Shop: {my_sv.get('voucherCode', 'Không')} (Giảm ${my_sv.get('voucherDiscount', 0)})
  + Voucher Shopee: {my_pv.get('voucherCode', 'Không')} (Giảm ${my_pv.get('voucherDiscount', 0)})
"""

    prompt = f"""Bạn là Giám đốc chiến lược định giá & E-commerce Shopee chuyên nghiệp bậc thầy.
Hãy phân tích sự đối đầu giữa sản phẩm của shop bạn và đối thủ cạnh tranh dưới đây, sau đó đưa ra chiến thuật định giá và marketing thực chiến nhất:

- SẢN PHẨM ĐỐI THỦ:
  + Tên: {item_name}
  + Shop đối thủ: {comp_data.get('shop_name', 'Đối thủ')}
  + Giá cuối đối thủ (sau voucher/flash sale): ${comp_final:g}
  + Flash Sale: {'CÓ ĐANG BẬT' if is_flash else 'Không'}
  + Tồn kho đối thủ: {stock if stock is not None else 'Không rõ'}
  + Voucher Shop đối thủ: {shop_voucher.get('voucherCode', 'Không')} (Giảm ${shop_voucher.get('voucherDiscount', 0)})
  + Voucher Sàn đối thủ: {platform_voucher.get('voucherCode', 'Không')} (Giảm ${platform_voucher.get('voucherDiscount', 0)})
{my_details if my_details else f'''
- SẢN PHẨM CỦA BẠN:
  + Giá bán hiện tại của bạn: ${my_price:g}
'''}
- TÌNH HÌNH TÀI CHÍNH & CHÊNH LỆCH:
  + Giá vốn / Giá sàn: {'$' + str(cost) if cost is not None else 'Chưa có thông tin'}
  + Chênh lệch giá cuối: Bạn đang {'ĐẮT HƠN' if diff > 0 else 'RẺ HƠN' if diff < 0 else 'BẰNG'} đối thủ ${abs(diff):.2f} ({abs(diff_pct):.1f}%)

Hãy trả về JSON DUY NHẤT theo cấu trúc này (không bọc markdown, không thêm text bên ngoài):
{{
  "badge": "warning" | "danger" | "success" | "info",
  "summary": "1-2 câu tóm tắt tình thế cạnh tranh hiện tại giữa 2 shop",
  "margin_info": "Nhận xét cụ thể về biên lợi nhuận, an toàn vốn",
  "tactics": [
    {{
      "action": "TÊN HÀNH ĐỘNG CỤ THỂ",
      "reason": "Lý do vì sao nên làm vậy",
      "suggestion": "Cách thực hiện chi tiết (voucher bao nhiêu, tặng quà gì, chỉnh ads ra sao)"
    }}
  ]
}}"""

    if COMMANDCODE_API_KEY:
        try:
            body = {
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            req = urllib.request.Request(
                f"{AI_BASE_URL}/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {COMMANDCODE_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "omp/18.3.2"
                }
            )
            with urllib.request.urlopen(req, timeout=25) as res:
                raw_json = json.loads(res.read().decode("utf-8"))
                choice = raw_json["choices"][0]["message"]["content"]
                result = json.loads(choice)
                result["status"] = "success"
                result["diff"] = round(diff, 2)
                result["diff_pct"] = round(diff_pct, 1)
                result["generated_by"] = f"Gemini 3.8 Flash ({AI_MODEL})"
                return result
        except Exception:
            pass

    # Fallback rule-based nếu mạng hoặc key lỗi
    return _fallback_rule_analysis(item_name, comp_final, my_price, cost, diff, diff_pct, stock, is_flash)


def _fallback_rule_analysis(item_name: str, comp_final: float, my_price: float, cost: float | None, diff: float, diff_pct: float, stock: int | None, is_flash: bool) -> dict[str, Any]:
    tactics = []
    if diff > 0:
        badge = "warning"
        summary = f"Bạn đang cao hơn đối thủ ${diff:.2f} ({diff_pct:.1f}%). Giá cuối đối thủ là ${comp_final:g}."
        if cost and cost >= comp_final:
            badge = "danger"
            tactics.append({
                "action": "KHÔNG HẠ GIÁ THEO ĐỐI THỦ",
                "reason": f"Giá cuối đối thủ (${comp_final:g}) thấp hơn hoặc bằng giá vốn (${cost:g}).",
                "suggestion": "Tặng quà kèm (shaker, sample) hoặc cải thiện hình ảnh, freeship hỏa tốc để giữ giá."
            })
        else:
            tactics.append({
                "action": f"CÀI VOUCHER SHOP GIẢM ${round(diff, 1):g}",
                "reason": "Kéo giá cuối về ngang đối thủ mà không cần hạ giá niêm yết.",
                "suggestion": f"Tạo voucher shop giảm ${round(diff, 1):g} cho sản phẩm này."
            })
    elif diff < 0:
        badge = "success"
        summary = f"Bạn đang rẻ hơn đối thủ ${abs(diff):.2f} ({abs(diff_pct):.1f}%). Đang có lợi thế cạnh tranh rất lớn!"
        tactics.append({
            "action": "TĂNG NGÂN SÁCH QUẢNG CÁO ĐẨY TOP",
            "reason": "Lợi thế giá rẻ hơn giúp tỷ lệ chuyển đổi (CVR) tăng vọt.",
            "suggestion": "Tăng bid Shopee Ads cho các từ khóa chính của sản phẩm này."
        })
    else:
        badge = "info"
        summary = f"Giá của bạn (${my_price:g}) đang ngang bằng giá cuối đối thủ."
        tactics.append({
            "action": "CẠNH TRANH BẰNG QUÀ TẶNG & DỊCH VỤ",
            "reason": "Bằng giá thì khách hàng chọn bên có quà tặng hoặc ship nhanh hơn.",
            "suggestion": "Gắn quà tặng kèm hoặc bật Freeship Xtra."
        })

    return {
        "status": "success",
        "badge": badge,
        "summary": summary,
        "margin_info": f"Giá vốn: ${cost:g}" if cost else "Chưa có thông tin giá vốn",
        "diff": round(diff, 2),
        "diff_pct": round(diff_pct, 1),
        "tactics": tactics,
        "generated_by": "Rule Engine (Offline Fallback)"
    }
