from src.seller_stats import extract_seller_stats, meets_min_level, parse_level
from src.skip_cache import SkipCache


def test_parse_level_variants():
    assert parse_level("L7") == 7
    assert parse_level(7) == 7
    assert parse_level("卖家等级7") == 7
    assert parse_level(None) is None
    assert parse_level("x") is None
    assert parse_level(True) is None


def test_extract_stats_reads_goofish_mcp_shape():
    seller = {
        "idleFishCreditTag": {"trackParams": {"sellerLevel": "7"}},
        "goodSellerTag": {"text": "Top"},
        "hasSoldNumInteger": 120,
        "newGoodRatioRate": "99%",
        "replyRatio24h": "95%",
        "userRegDay": 900,
        "remarkDO": {"sellerGoodRemarkCnt": 50, "sellerBadRemarkCnt": 0},
        "emptyField": "",
    }
    stats = extract_seller_stats(seller)
    assert stats["level"] == 7
    assert stats["badge"] == "Top"
    assert stats["good_remarks"] == 50
    assert stats["bad_remarks"] == 0
    assert "avg_reply" not in stats


def test_extract_stats_tolerates_garbage():
    assert extract_seller_stats(None) == {}
    assert extract_seller_stats({"remarkDO": "x"}) == {}


def test_min_level_is_fail_open():
    assert meets_min_level(7, 7)
    assert meets_min_level(8, 7)
    assert not meets_min_level(5, 7)
    assert meets_min_level(None, 7)  # unknown level: do not reject
    assert meets_min_level(3, None)
    assert meets_min_level(3, 0)
    assert meets_min_level(3, "abc")


def test_skip_cache_expires(tmp_path):
    cache = SkipCache(str(tmp_path / "skip.json"), ttl_seconds=100)
    cache.add("t", "k", now=1000)
    assert cache.has("t", "k", now=1050)
    assert not cache.has("t", "k", now=1200)
    assert not cache.has("other", "k", now=1050)
