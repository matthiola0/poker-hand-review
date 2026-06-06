"""漏洞彙整：把重複出現的紅/黃決策歸類成可行動的「漏洞」清單。

取代舊版獨立規則引擎，改為消費 Decision Evaluator 產出的 DecisionEval。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import DecisionEval, HandEval, QualityTier


@dataclass(frozen=True)
class Leak:
    pattern: str           # 如 "BTN 對 3bet 過度跟注"
    count: int
    total_ev_loss_bb: float
    example_hand_ids: tuple[str, ...]


def aggregate_leaks(hand_evals: list[HandEval]) -> list[Leak]:
    """把所有非 GOOD 決策依「情境特徵」分群、計次、累計 EV 損失、排序。"""
    buckets: dict[str, list[DecisionEval]] = {}
    for decision in _flatten(hand_evals):
        if decision.tier not in {QualityTier.INACCURACY, QualityTier.MISTAKE}:
            continue
        pattern = (
            f"{decision.street.value}: {decision.hero_action.type.value} "
            f"vs 建議 {decision.suggestion.best_action}"
        )
        buckets.setdefault(pattern, []).append(decision)

    leaks = [
        Leak(
            pattern=pattern,
            count=len(items),
            total_ev_loss_bb=sum(d.ev_loss_bb for d in items),
            example_hand_ids=tuple(dict.fromkeys(d.hand_id for d in items))[:3],
        )
        for pattern, items in buckets.items()
    ]
    return sorted(leaks, key=lambda leak: leak.total_ev_loss_bb, reverse=True)


def _flatten(hand_evals: list[HandEval]) -> list[DecisionEval]:
    return [d for he in hand_evals for d in he.decisions]
