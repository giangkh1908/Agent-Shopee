"""Parse link Shopee → (shop_id, item_id, market). Deterministic, không dùng LLM."""
from __future__ import annotations

import re
from urllib.parse import urlparse

# /product/<shop_id>/<item_id>
PATH_RE = re.compile(r"/product/(\d+)/(\d+)")
# slug-i.<shop_id>.<item_id>
IID_RE = re.compile(r"-i\.(\d+)\.(\d+)")
# i.<shop_id>.<item_id> ở bất kỳ đâu
GENERIC_RE = re.compile(r"\bi\.(\d+)\.(\d+)\b")

MARKETS = {
    "shopee.sg": "sg", "shopee.com.my": "my", "shopee.co.id": "id", "shopee.co.th": "th",
    "shopee.ph": "ph", "shopee.vn": "vn", "shopee.tw": "tw", "shopee.com.br": "br",
    "shopee.com.mx": "mx", "shopee.com.co": "co", "shopee.cl": "cl",
    "shopeekh.com": "kh", "shopee.com.la": "la", "shopee.com.ar": "ar",
}

SHORT_HOSTS = ("s.shopee.sg", "shp.ee", "s.shopee.com.my", "s.shopee.co.id", "s.shopee.vn", "s.shopee.co.th", "s.shopee.ph", "s.shopee.tw", "s.shopee.com.br")


class ParseError(ValueError):
    pass


def parse_url(url: str) -> dict[str, object]:
    url = (url or "").strip()
    if not url:
        raise ParseError("link rỗng")
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]

    market = MARKETS.get(host)
    if market is None:
        if host in SHORT_HOSTS:
            raise ParseError(f"link rút gọn ({host}) cần mở trong trình duyệt để lấy link đầy đủ")
        raise ParseError(f"không nhận diện được sàn từ host '{host}'")

    path = parsed.path or ""
    for regex in (PATH_RE, IID_RE, GENERIC_RE):
        match = regex.search(path) or regex.search(url)
        if match:
            shop_id, item_id = match.groups()
            return {
                "shop_id": int(shop_id),
                "item_id": int(item_id),
                "market": market,
                "url": f"https://{host}/product/{shop_id}/{item_id}",
            }
    raise ParseError(f"không tìm thấy shop_id/item_id trong link: {url}")


def parse_many(raw_text: str) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    """Nhận text nhiều dòng, trả (targets hợp lệ đã dedupe, errors)."""
    seen: set[int] = set()
    targets: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    for line in re.split(r"[\s,;]+", raw_text or ""):
        line = line.strip()
        if not line:
            continue
        try:
            target = parse_url(line)
        except ParseError as exc:
            errors.append({"input": line, "error": str(exc)})
            continue
        item_id = int(target["item_id"])
        if item_id in seen:
            continue
        seen.add(item_id)
        targets.append(target)
    return targets, errors
