"""
Title triage: decide from the search list alone which listings are worth opening.

Opening an item's detail page is what makes Goofish start asking for verification,
and it is also what costs the image analysis. One cheap text-only call per page of
results can drop the obvious mismatches (other models, accessories, wanted-to-buy
posts, bulk lots) before any detail page is requested.

Fail-open by design: any error (no AI configured, bad reply, network) keeps every
listing, so the triage can only ever save requests, never lose a run.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

BATCH_SIZE = 40
MAX_TITLE_CHARS = 90
MAX_DESCRIPTION_CHARS = 1500

SYSTEM_PROMPT = (
    "You pre-screen second-hand marketplace listings (Goofish / Xianyu; titles are mostly "
    "Chinese) for a buyer. Using only each listing's title, price and region, decide which "
    "ones are worth opening for a detailed review.\n"
    "Be inclusive when unsure: opening a listing is cheap, missing a good one is not.\n"
    "Exclude only listings that clearly cannot match the buyer's requirement: a different "
    "product, model or specification than the one wanted; accessories or spare parts when a "
    "device is wanted; wanted-to-buy or recycling posts (收 / 求购 / 回收); bulk or wholesale "
    "lots when the buyer wants a single unit; and anything that contradicts a hard "
    "requirement stated by the buyer.\n"
    'Reply with JSON only, exactly in this shape: {"open": [<i>, ...]} where each <i> is the '
    '"i" of a listing to open.'
)


@dataclass
class TriageResult:
    kept: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    error: Optional[str] = None


def _clip(text: Any, limit: int) -> str:
    value = str(text or "").strip()
    return value if len(value) <= limit else value[: limit - 1] + "…"


def build_triage_messages(description: str, keyword: str, items: list[dict]) -> list[dict]:
    listings = [
        {
            "i": index,
            "title": _clip(item.get("商品标题"), MAX_TITLE_CHARS),
            "price": str(item.get("当前售价") or ""),
            "region": str(item.get("发货地区") or ""),
        }
        for index, item in enumerate(items)
    ]
    payload = {
        "buyer_requirement": _clip(description, MAX_DESCRIPTION_CHARS),
        "search_keyword": keyword,
        "listings": listings,
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def parse_triage_response(text: str, total: int) -> Optional[set[int]]:
    """Indices (0..total-1) the model wants opened, or None when the reply is unusable."""
    if not text:
        return None
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return None
    opened = data.get("open") if isinstance(data, dict) else None
    if not isinstance(opened, list):
        return None
    indices: set[int] = set()
    for value in opened:
        if isinstance(value, bool):
            continue
        if isinstance(value, str) and value.strip().isdigit():
            value = int(value.strip())
        if isinstance(value, (int, float)) and 0 <= int(value) < total:
            indices.add(int(value))
    return indices


def build_triage_client():
    """
    AIClient for the triage. AI_TRIAGE_MODEL_NAME switches it on; AI_TRIAGE_BASE_URL and
    AI_TRIAGE_API_KEY let it point at a different provider (e.g. a cheap text-only model)
    and fall back to the main AI settings when unset. Returns None when AI is unusable.
    """
    from src.infrastructure.external.ai_client import AIClient

    client = AIClient()
    triage_model = (os.getenv("AI_TRIAGE_MODEL_NAME") or "").strip()
    if triage_model and client.settings is not None:
        updates = {"model_name": triage_model}
        base_url = (os.getenv("AI_TRIAGE_BASE_URL") or "").strip()
        api_key = (os.getenv("AI_TRIAGE_API_KEY") or "").strip()
        if base_url:
            updates["base_url"] = base_url
        if api_key:
            updates["api_key"] = api_key
        client.settings = client.settings.model_copy(update=updates)
        client.client = client._initialize_client()
    return client if client.is_available() else None


async def triage_items(
    items: list[dict], *, description: str, keyword: str, client=None
) -> TriageResult:
    """Split `items` into the ones to open and the ones to skip. Never raises."""
    if not items:
        return TriageResult()
    owns_client = client is None
    try:
        if client is None:
            client = build_triage_client()
        if client is None:
            return TriageResult(kept=list(items), error="AI client unavailable")

        kept_indices: set[int] = set()
        for offset in range(0, len(items), BATCH_SIZE):
            batch = items[offset : offset + BATCH_SIZE]
            reply = await client._call_ai(
                build_triage_messages(description, keyword, batch),
                temperature=0.0,
                max_output_tokens=1200,
                enable_json_output=True,
            )
            opened = parse_triage_response(reply, len(batch))
            if opened is None:
                # unusable reply for this batch: keep all of it
                opened = set(range(len(batch)))
            kept_indices |= {offset + index for index in opened}

        kept = [item for index, item in enumerate(items) if index in kept_indices]
        skipped = [item for index, item in enumerate(items) if index not in kept_indices]
        return TriageResult(kept=kept, skipped=skipped)
    except Exception as exc:  # noqa: BLE001 - fail open on purpose
        return TriageResult(kept=list(items), error=f"{type(exc).__name__}: {exc}")
    finally:
        if owns_client and client is not None:
            try:
                await client.close()
            except Exception:  # noqa: BLE001
                pass
