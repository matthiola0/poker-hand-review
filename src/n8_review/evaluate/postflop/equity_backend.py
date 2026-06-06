"""預設翻後後端：以 equity vs 假設範圍 + EV + 啟發法給建議。

離線、快、抓明顯失誤。不是完整 GTO solver，但對「明顯被支配的動作」可靠。
"""

from __future__ import annotations

from itertools import combinations

from ...analysis.equity import equity_vs_range, pot_odds
from ...models import Card
from ...models import GtoSuggestion
from .base import PostflopNode


class EquityBackend:
    name = "equity_backend"

    def __init__(self, mc_samples: int = 20_000) -> None:
        self.mc_samples = mc_samples

    def evaluate(self, node: PostflopNode) -> GtoSuggestion:
        """以對手假設範圍算勝率，搭配底池賠率給出快速建議。"""
        villain_range = _villain_range(node.hero_hole, node.board, node.villain_range_key)
        result = equity_vs_range(
            node.hero_hole,
            villain_range,
            node.board,
            samples=max(1, self.mc_samples),
        )
        equity = result.win + result.tie * 0.5

        if node.to_call > 0:
            required = pot_odds(node.to_call, node.pot_before)
            if equity >= required + 0.12:
                return GtoSuggestion(
                    actions=(("raise", 0.25), ("call", 0.75)),
                    best_action="call",
                    source="equity_backend",
                )
            if equity >= required - 0.03:
                return GtoSuggestion(
                    actions=(("call", 0.75), ("fold", 0.25)),
                    best_action="call",
                    source="equity_backend",
                )
            return GtoSuggestion(
                actions=(("fold", 1.0),),
                best_action="fold",
                source="equity_backend",
            )

        if equity >= 0.62:
            return GtoSuggestion(
                actions=(("bet", 0.7), ("check", 0.3)),
                best_action="bet",
                source="equity_backend",
            )
        return GtoSuggestion(
            actions=(("check", 1.0),),
            best_action="check",
            source="equity_backend",
        )


def _villain_range(
    hero: tuple[Card, Card],
    board: tuple[Card, ...],
    range_key: str | None,
) -> list[tuple[Card, Card]]:
    dead = set(hero).union(board)
    deck = [card for card in _deck() if card not in dead]
    combos: list[tuple[Card, Card]] = []
    for c1, c2 in combinations(deck, 2):
        key = _hand_key(c1, c2)
        if _is_playable(key, range_key or "balanced"):
            combos.append((c1, c2))
    return combos


def _deck() -> tuple[Card, ...]:
    return tuple(Card(rank, suit) for rank in "23456789TJQKA" for suit in "shdc")


def _hand_key(c1: Card, c2: Card) -> str:
    order = "AKQJT98765432"
    if c1.rank == c2.rank:
        return c1.rank + c2.rank
    hi, lo = sorted((c1.rank, c2.rank), key=order.index)
    return f"{hi}{lo}{'s' if c1.suit == c2.suit else 'o'}"


def _is_playable(key: str, range_key: str) -> bool:
    if len(key) == 2:
        return _pair_rank(key[0]) >= _min_pair(range_key)
    high = key[0]
    low = key[1]
    suited = key.endswith("s")
    if range_key == "tight":
        return key in {
            "AKs",
            "AQs",
            "AJs",
            "KQs",
            "AKo",
            "AQo",
        }
    if range_key == "wide_passive":
        return high in "AKQJT" or suited or key in {"98o", "87o", "76o"}
    if range_key == "wide_aggressive":
        return high in "AKQJT" or (suited and high in "9876") or key in {"K9o", "Q9o", "J9o"}
    return high in "AKQJ" or (suited and high in "T987") or (high == "T" and low == "9")


def _pair_rank(rank: str) -> int:
    return "23456789TJQKA".index(rank) + 2


def _min_pair(range_key: str) -> int:
    if range_key == "tight":
        return 9
    if range_key in {"wide_passive", "wide_aggressive"}:
        return 2
    return 5
