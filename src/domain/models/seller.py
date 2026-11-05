"""Seller (store) identifiers for store-scoped tasks."""
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

_SELLER_ID_RE = re.compile(r"^\d{5,20}$")


def parse_seller_id(value: Optional[str]) -> Optional[str]:
    """Accept a numeric userId or a goofish personal-page URL; return the userId or None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if _SELLER_ID_RE.match(text):
        return text
    try:
        parsed = urlparse(text if "//" in text else f"https://{text}")
    except ValueError:
        return None
    if not (parsed.hostname or "").endswith("goofish.com"):
        return None
    user_id = (parse_qs(parsed.query).get("userId") or [""])[0].strip()
    return user_id if _SELLER_ID_RE.match(user_id) else None
