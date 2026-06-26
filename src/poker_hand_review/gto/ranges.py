"""手牌範圍表示：13×13 矩陣、組合鍵、Hero 手牌歸屬查詢。"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Card

RANK_ORDER = "AKQJT98765432"


def hand_key(c1: Card, c2: Card) -> str:
    """兩張底牌 -> 範圍鍵，如 'AKs' / 'AKo' / 'TT'。"""
    r1, r2 = c1.rank, c2.rank
    if r1 == r2:
        return r1 + r2
    hi, lo = sorted((r1, r2), key=RANK_ORDER.index)
    suited = "s" if c1.suit == c2.suit else "o"
    return f"{hi}{lo}{suited}"


@dataclass(frozen=True)
class Range:
    """範圍：鍵 -> 進入頻率（0..1）。

    `actions` 為可選的逐手四動作頻率（raise/allin/call/fold），供需要區分
    raise vs call vs allin 的評分使用；未提供時退回 `freqs` 的單一進入頻率。
    """

    freqs: dict[str, float]
    actions: dict[str, dict[str, float]] | None = None

    def frequency(self, c1: Card, c2: Card) -> float:
        return self.freqs.get(hand_key(c1, c2), 0.0)

    def action_profile(self, c1: Card, c2: Card) -> dict[str, float]:
        """逐手四動作頻率；無四動作資料時回空 dict。"""
        if self.actions is None:
            return {}
        return dict(self.actions.get(hand_key(c1, c2), {"fold": 1.0}))

    def contains(self, c1: Card, c2: Card, threshold: float = 0.0) -> bool:
        return self.frequency(c1, c2) > threshold
