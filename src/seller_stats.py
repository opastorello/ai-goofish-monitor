"""
Seller quality signals taken from the item-detail API's ``sellerDO``.

Shape cross-checked against the goofish-mcp reference (a live-tested client):
the seller's level sits at ``idleFishCreditTag.trackParams.sellerLevel``; the rest
are plain fields. Everything is optional: a missing value is None, never a guess.
"""
from __future__ import annotations

import re
from typing import Any, Optional


def _get(data: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def parse_level(raw: Any) -> Optional[int]:
    """'L7', '7', 7 -> 7. Anything without a digit -> None."""
    if raw is None or isinstance(raw, bool):
        return None
    match = re.search(r"\d+", str(raw))
    return int(match.group()) if match else None


def extract_seller_stats(seller_do: Any) -> dict:
    """Compact, JSON-friendly seller stats (None for what the API did not return)."""
    seller_do = seller_do if isinstance(seller_do, dict) else {}
    remark = seller_do.get("remarkDO") if isinstance(seller_do.get("remarkDO"), dict) else {}
    stats = {
        "level": parse_level(_get(seller_do, "idleFishCreditTag", "trackParams", "sellerLevel")),
        "badge": _get(seller_do, "goodSellerTag", "text"),
        "sold_count": seller_do.get("hasSoldNumInteger"),
        "positive_rate": seller_do.get("newGoodRatioRate"),
        "reply_rate_24h": seller_do.get("replyRatio24h"),
        "avg_reply": seller_do.get("replyInterval"),
        "days_registered": seller_do.get("userRegDay"),
        "seller_type": seller_do.get("sellerTypeString"),
        "zhima_verified": seller_do.get("zhimaAuth"),
        "good_remarks": remark.get("sellerGoodRemarkCnt"),
        "bad_remarks": remark.get("sellerBadRemarkCnt"),
    }
    return {key: value for key, value in stats.items() if value not in (None, "")}


def meets_min_level(level: Optional[int], minimum: Any) -> bool:
    """Fail-open: only reject when both a minimum and a known level exist and level < minimum."""
    try:
        floor = int(minimum) if minimum is not None else None
    except (TypeError, ValueError):
        floor = None
    if floor is None or floor <= 0 or level is None:
        return True
    return level >= floor
