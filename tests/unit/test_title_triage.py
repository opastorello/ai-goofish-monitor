import asyncio
import json

import pytest

from src.title_triage import (
    BATCH_SIZE,
    TriageResult,
    build_triage_messages,
    parse_triage_response,
    triage_items,
)


def _items(n):
    return [
        {"商品标题": f"Tesla V100 32G #{i}", "当前售价": f"¥{3000 + i}", "发货地区": "上海"}
        for i in range(n)
    ]


class FakeClient:
    def __init__(self, replies=None, error=None):
        self.replies = list(replies or [])
        self.error = error
        self.calls = []

    async def _call_ai(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if self.error:
            raise self.error
        return self.replies.pop(0)


def test_prompt_carries_requirement_and_compact_listings():
    items = _items(2)
    items[0]["商品标题"] = "x" * 300
    system, user = build_triage_messages("quero V100 32GB", "V100 PCIE 32G", items)
    assert system["role"] == "system" and "JSON only" in system["content"]
    payload = json.loads(user["content"])
    assert payload["buyer_requirement"] == "quero V100 32GB"
    assert payload["search_keyword"] == "V100 PCIE 32G"
    assert [row["i"] for row in payload["listings"]] == [0, 1]
    assert len(payload["listings"][0]["title"]) <= 90
    assert payload["listings"][1]["price"] == "¥3001"


@pytest.mark.parametrize(
    "text,total,expected",
    [
        ('{"open": [0, 2]}', 3, {0, 2}),
        ('Sure!\n```json\n{"open": ["1", 2]}\n```', 3, {1, 2}),
        ('{"open": [0, 9, -1, true, 1.0]}', 3, {0, 1}),   # out of range / bool ignored
        ('{"open": []}', 3, set()),                          # nothing worth opening is valid
        ("not json", 3, None),
        ('{"keep": [0]}', 3, None),
        ("", 3, None),
    ],
)
def test_parse_triage_response(text, total, expected):
    assert parse_triage_response(text, total) == expected


def test_triage_splits_kept_and_skipped():
    items = _items(4)
    client = FakeClient(['{"open": [0, 3]}'])
    result = asyncio.run(triage_items(items, description="d", keyword="k", client=client))
    assert result.kept == [items[0], items[3]] and result.skipped == [items[1], items[2]]
    assert result.error is None
    assert client.calls[0][1]["enable_json_output"] is True


def test_triage_is_batched():
    items = _items(BATCH_SIZE + 5)
    client = FakeClient(['{"open": [0]}', '{"open": [1]}'])
    result = asyncio.run(triage_items(items, description="d", keyword="k", client=client))
    assert len(client.calls) == 2
    assert result.kept == [items[0], items[BATCH_SIZE + 1]]


def test_triage_fails_open_on_errors_and_bad_replies():
    items = _items(3)
    boom = asyncio.run(triage_items(items, description="d", keyword="k", client=FakeClient(error=RuntimeError("down"))))
    assert boom.kept == items and boom.skipped == [] and "RuntimeError" in boom.error
    garbage = asyncio.run(triage_items(items, description="d", keyword="k", client=FakeClient(["???"])))
    assert garbage.kept == items and garbage.skipped == []


def test_triage_without_items_does_nothing():
    assert asyncio.run(triage_items([], description="d", keyword="k", client=FakeClient())) == TriageResult()
