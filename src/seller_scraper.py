"""
Seller (store) scoped scraping.

A seller task skips the keyword search and instead reads the item list that the
Goofish personal page ("https://www.goofish.com/personal?userId=...") loads, then
hands those items to the regular detail/AI-analysis pipeline.
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Optional

from src.domain.models.seller import parse_seller_id  # noqa: F401  (re-exported)

SELLER_PAGE_URL = "https://www.goofish.com/personal?userId={seller_id}"
SELLER_ITEM_LIST_API = "mtop.idle.web.xyh.item.list"
ITEM_URL = "https://www.goofish.com/item?id={item_id}"

def build_seller_url(seller_id: str) -> str:
    return SELLER_PAGE_URL.format(seller_id=seller_id)


def _format_price(raw_price: Any) -> str:
    text = str(raw_price if raw_price is not None else "").strip()
    if not text:
        return "价格异常"
    return text if text.startswith("¥") else f"¥{text}"


def _format_publish_time(card_data: dict) -> str:
    for key in ("publishTime", "gmtCreate", "firstModified"):
        value = card_data.get(key)
        if value and str(value).isdigit():
            try:
                return datetime.fromtimestamp(int(value) / 1000).strftime("%Y-%m-%d %H:%M")
            except (ValueError, OSError):
                continue
    return "未知时间"


def seller_card_to_basic_item(card: dict, seller_name: str = "") -> Optional[dict]:
    """Convert one personal-page card into the same shape the search parser returns."""
    data = (card or {}).get("cardData") or {}
    item_id = data.get("id")
    if not item_id:
        return None
    if data.get("itemStatus") not in (0, None):  # 0 = on sale; skip sold/removed
        return None
    price_info = data.get("priceInfo") or {}
    return {
        "商品标题": data.get("title") or "未知标题",
        "当前售价": _format_price(price_info.get("price")),
        "商品原价": _format_price(price_info.get("oriPrice")) if price_info.get("oriPrice") else "暂无",
        "“想要”人数": data.get("wantNum", "NaN"),
        "商品标签": [],
        "发货地区": data.get("area") or "地区未知",
        "卖家昵称": seller_name or "匿名卖家",
        "商品链接": ITEM_URL.format(item_id=item_id),
        "发布时间": _format_publish_time(data),
        "商品ID": str(item_id),
        "商品主图链接": (data.get("picInfo") or {}).get("picUrl") or "",
    }


def title_matches_keyword(title: str, keyword: str) -> bool:
    """Every whitespace-separated keyword token must appear in the title (case-insensitive)."""
    tokens = [token for token in (keyword or "").lower().split() if token]
    haystack = (title or "").lower()
    return all(token in haystack for token in tokens)


def filter_seller_items(
    cards: list,
    *,
    keyword: str = "",
    seller_name: str = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> list[dict]:
    """Drop sold items, de-duplicate by id, and apply the optional title/price filters."""
    items: list[dict] = []
    seen: set[str] = set()
    for card in cards:
        item = seller_card_to_basic_item(card, seller_name)
        if not item or item["商品ID"] in seen:
            continue
        if not title_matches_keyword(item["商品标题"], keyword):
            continue
        price_match = re.search(r"\d+(?:\.\d+)?", item["当前售价"].replace(",", ""))
        if price_match:
            price = float(price_match.group())
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
        seen.add(item["商品ID"])
        items.append(item)
    return items


async def collect_seller_cards(
    page,
    seller_id: str,
    *,
    max_scrolls: int = 10,
    scroll_timeout: float = 8.0,
) -> tuple[list, str]:
    """
    Open the seller's personal page and scroll until the item list API reports no
    more pages. Returns (raw cards, seller display name when available).
    """
    cards: list = []
    seller_name = ""
    done = asyncio.Event()
    loaded_pages = 0

    async def on_response(response):
        nonlocal seller_name, loaded_pages
        url = response.url
        try:
            if SELLER_ITEM_LIST_API in url:
                payload = await response.json()
                data = payload.get("data", {}) or {}
                cards.extend(data.get("cardList", []) or [])
                loaded_pages += 1
                if not data.get("nextPage", True):
                    done.set()
            elif "mtop.idle.web.user.page.head" in url and not seller_name:
                payload = await response.json()
                base = (((payload.get("data") or {}).get("module") or {}).get("base") or {})
                seller_name = base.get("displayName") or ""
        except Exception:
            done.set()

    page.on("response", on_response)
    try:
        await page.goto(
            build_seller_url(seller_id), wait_until="domcontentloaded", timeout=30000
        )
        await asyncio.sleep(3)
        scrolls = 0
        while not done.is_set() and scrolls < max_scrolls:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            scrolls += 1
            try:
                await asyncio.wait_for(done.wait(), timeout=scroll_timeout)
            except asyncio.TimeoutError:
                break
    finally:
        page.remove_listener("response", on_response)
    return cards, seller_name
