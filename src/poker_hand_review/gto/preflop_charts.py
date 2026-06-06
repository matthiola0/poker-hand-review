"""翻前 GTO 範圍表查詢。

依（位置組合、有效籌碼分桶、面對動作）查表，回傳該情境的 GTO 範圍/頻率。
圖表資料以資料檔內建於 charts/，來源與版本見 charts/CHARTS.md。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from ..models import Position
from .ranges import Range

CHART_DIR = Path(__file__).resolve().parent / "charts"


@dataclass(frozen=True)
class ChartKey:
    hero_pos: Position
    vs_pos: Position | None     # None = 未開鍋（RFI）
    action: str                 # "rfi" | "vs_rfi" | "3bet" | "vs_3bet" ...
    stack_bucket: str           # "60bb+" | "40bb" | "25bb" | "15bb" | "push_fold"


@dataclass(frozen=True)
class ChartLookup:
    range: Range
    detail: dict[str, object]


def stack_bucket(eff_bb: float) -> str:
    """有效籌碼（BB）-> 圖表分桶。"""
    if eff_bb <= 12:
        return "push_fold"
    if eff_bb <= 20:
        return "15bb"
    if eff_bb <= 32:
        return "25bb"
    if eff_bb <= 50:
        return "40bb"
    return "60bb+"


def lookup(key: ChartKey) -> Range | None:
    """查表回傳範圍；查無回 None（呼叫端視為 UNKNOWN）。"""
    result = lookup_with_detail(key)
    return result.range if result else None


def lookup_with_detail(key: ChartKey) -> ChartLookup | None:
    """查表回傳範圍與來源細節；JSON solver chart 優先於內建 fallback。"""
    loaded = _load_json_chart(key)
    if loaded is not None:
        return loaded
    if key.vs_pos is not None:
        generic = _load_json_chart(
            ChartKey(
                hero_pos=key.hero_pos,
                vs_pos=None,
                action=key.action,
                stack_bucket=key.stack_bucket,
            )
        )
        if generic is not None:
            return generic
    if key.action == "rfi":
        return _builtin_lookup(key, _rfi_freqs(key.hero_pos, key.stack_bucket))
    if key.action in {"vs_rfi", "vs_3bet"}:
        return _builtin_lookup(
            key,
            _continue_freqs(key.hero_pos, key.stack_bucket, tight=key.action == "vs_3bet"),
        )
    if key.action == "push_fold":
        return _builtin_lookup(key, _push_fold_freqs(key.hero_pos))
    return None


def _load_json_chart(key: ChartKey) -> ChartLookup | None:
    path = CHART_DIR / f"{_chart_id(key)}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    freqs = data.get("freqs")
    if not isinstance(freqs, dict):
        raise ValueError(f"chart {path.name} missing freqs object")
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    return ChartLookup(
        range=Range({str(hand): float(freq) for hand, freq in freqs.items()}),
        detail=_chart_detail(key, source_type="solver_chart", source_file=path.name, meta=meta),
    )


def _builtin_lookup(key: ChartKey, freqs: dict[str, float]) -> ChartLookup:
    return ChartLookup(
        range=Range(freqs),
        detail=_chart_detail(
            key,
            source_type="built_in_approx",
            source_file=None,
            meta={
                "source": "n8 built-in approximate MTT ranges",
                "version": "0.1",
                "format": "8-max MTT ante",
            },
        ),
    )


def _chart_detail(
    key: ChartKey,
    *,
    source_type: str,
    source_file: str | None,
    meta: dict[str, Any],
) -> dict[str, object]:
    detail: dict[str, object] = {
        "chart_id": _chart_id(key),
        "chart_source_type": source_type,
        "chart_source": str(meta.get("source", "")),
        "chart_version": str(meta.get("version", "")),
        "chart_format": str(meta.get("format", "")),
        "source_file": source_file or "",
        "hero_pos": key.hero_pos.value,
        "vs_pos": key.vs_pos.value if key.vs_pos else "",
        "action": key.action,
        "stack_bucket": key.stack_bucket,
    }
    return detail


def _chart_id(key: ChartKey) -> str:
    parts = [key.action, key.hero_pos.value]
    if key.vs_pos is not None:
        parts.extend(["vs", key.vs_pos.value])
    parts.append(key.stack_bucket)
    return "_".join(parts)


def _rfi_freqs(position: Position, bucket: str) -> dict[str, float]:
    ranges: dict[Position, tuple[str, ...]] = {
        Position.UTG: _pairs("55") + _suited("AJs", "KQs") + ("AQo", "AKo"),
        Position.UTG1: _pairs("44") + _suited("ATs", "KQs", "KJs", "QJs") + ("AJo", "AQo", "AKo", "KQo"),
        Position.MP: _pairs("33") + _suited("A9s", "KTs", "QTs", "JTs", "T9s") + ("ATo", "AJo", "AQo", "AKo", "KQo"),
        Position.HJ: _pairs("22") + _suited("A2s", "K9s", "Q9s", "J9s", "T9s", "98s") + ("A9o", "ATo", "AJo", "AQo", "AKo", "KJo", "KQo", "QJo"),
        Position.CO: _pairs("22") + _suited("A2s", "K7s", "Q8s", "J8s", "T8s", "98s", "87s", "76s") + ("A7o", "A8o", "A9o", "ATo", "AJo", "AQo", "AKo", "KTo", "KJo", "KQo", "QTo", "QJo", "JTo"),
        Position.BTN: _pairs("22") + _suited("A2s", "K2s", "Q5s", "J7s", "T7s", "97s", "86s", "75s", "65s", "54s") + ("A2o", "A5o", "A7o", "A8o", "A9o", "ATo", "AJo", "AQo", "AKo", "K8o", "KTo", "KJo", "KQo", "Q9o", "QTo", "QJo", "J9o", "JTo", "T9o"),
        Position.SB: _pairs("22") + _suited("A2s", "K2s", "Q4s", "J6s", "T6s", "96s", "85s", "75s", "64s", "54s") + ("A2o", "A5o", "A7o", "A8o", "A9o", "ATo", "AJo", "AQo", "AKo", "K7o", "KTo", "KJo", "KQo", "Q9o", "QTo", "QJo", "J9o", "JTo", "T9o"),
        Position.BB: (),
    }
    base = set(ranges.get(position, ()))
    if bucket in {"15bb", "push_fold"}:
        base = {h for h in base if h[0] in "AKQJT" or (len(h) == 2 and h[0] in "23456789TJQKA")}
        base.update(_pairs("22"))
    return {hand: 1.0 for hand in base}


def _continue_freqs(position: Position, bucket: str, tight: bool) -> dict[str, float]:
    del position
    hands = set(_pairs("99") + _suited("AQs", "AKs") + ("AQo", "AKo"))
    if not tight:
        hands.update(_pairs("66") + _suited("AJs", "KQs", "KJs", "QJs", "JTs", "T9s") + ("AJo", "KQo"))
    if bucket in {"15bb", "push_fold"}:
        hands.update(_pairs("22") + _suited("A2s", "KTs") + ("ATo",))
    return {hand: 1.0 for hand in hands}


def _push_fold_freqs(position: Position) -> dict[str, float]:
    hands = set(_continue_freqs(position, "push_fold", tight=False))
    if position in {Position.BTN, Position.SB, Position.CO}:
        hands.update(_suited("A2s", "K7s", "QTs", "JTs", "T9s", "98s") + ("A8o", "KTo", "QJo"))
    return {hand: 1.0 for hand in hands}


def _pairs(from_pair: str) -> tuple[str, ...]:
    ranks = "23456789TJQKA"
    start = ranks.index(from_pair[0])
    return tuple(rank + rank for rank in ranks[start:])


def _suited(*hands: str) -> tuple[str, ...]:
    ranks = "23456789TJQKA"
    expanded: list[str] = []
    for hand in hands:
        if len(hand) != 3 or hand[2] != "s":
            expanded.append(hand)
            continue
        high, low = hand[0], hand[1]
        high_index = ranks.index(high)
        low_index = ranks.index(low)
        expanded.extend(f"{high}{ranks[index]}s" for index in range(low_index, high_index))
    return tuple(dict.fromkeys(expanded))
