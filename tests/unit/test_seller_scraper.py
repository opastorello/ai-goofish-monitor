from src.seller_scraper import (
    build_seller_url,
    filter_seller_items,
    parse_seller_id,
    seller_card_to_basic_item,
    title_matches_keyword,
)


def _card(item_id, title, price, status=0, **extra):
    return {
        "cardData": {
            "id": item_id,
            "title": title,
            "priceInfo": {"price": price},
            "picInfo": {"picUrl": "https://img/x.jpg"},
            "itemStatus": status,
            **extra,
        }
    }


def test_parse_seller_id_accepts_url_and_plain_id():
    assert parse_seller_id("https://www.goofish.com/personal?userId=391299371") == "391299371"
    assert parse_seller_id("www.goofish.com/personal?userId=391299371&x=1") == "391299371"
    assert parse_seller_id(" 391299371 ") == "391299371"


def test_parse_seller_id_rejects_invalid_values():
    assert parse_seller_id("") is None
    assert parse_seller_id(None) is None
    assert parse_seller_id("abc") is None
    assert parse_seller_id("https://example.com/personal?userId=391299371") is None
    assert parse_seller_id("https://www.goofish.com/personal") is None


def test_build_seller_url():
    assert build_seller_url("391299371") == "https://www.goofish.com/personal?userId=391299371"


def test_card_to_basic_item_matches_search_item_shape():
    item = seller_card_to_basic_item(_card(111, "iPhone 14", "3999"), "Loja")
    assert item["商品ID"] == "111"
    assert item["当前售价"] == "¥3999"
    assert item["商品链接"] == "https://www.goofish.com/item?id=111"
    assert item["卖家昵称"] == "Loja"
    for key in ("商品标题", "商品原价", "“想要”人数", "商品标签", "发货地区", "发布时间"):
        assert key in item


def test_card_to_basic_item_skips_sold_and_idless_cards():
    assert seller_card_to_basic_item(_card(1, "x", "1", status=1)) is None
    assert seller_card_to_basic_item({"cardData": {"title": "x"}}) is None


def test_title_matches_keyword_requires_every_token():
    assert title_matches_keyword("全新 iPhone 14 国行", "iphone 14")
    assert not title_matches_keyword("iPhone 13", "iphone 14")
    assert title_matches_keyword("anything", "")


def test_filter_seller_items_dedupes_and_filters():
    cards = [
        _card(1, "iPhone 14 无锁", "3999"),
        _card(1, "iPhone 14 无锁", "3999"),
        _card(2, "iPhone 13", "2999"),
        _card(3, "iPad", "1999"),
        _card(4, "iPhone 14 已售", "3500", status=1),
        _card(5, "iPhone 14 Pro", "9999"),
    ]
    items = filter_seller_items(cards, keyword="iphone", max_price=5000)
    assert [i["商品ID"] for i in items] == ["1", "2"]
    items = filter_seller_items(cards, keyword="iphone", min_price=3000)
    assert [i["商品ID"] for i in items] == ["1", "5"]
