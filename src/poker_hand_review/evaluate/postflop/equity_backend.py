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
        range_key = node.villain_range_key or "balanced"
        required = pot_odds(node.to_call, node.pot_before) if node.to_call > 0 else None
        equity_edge = equity - required if required is not None else None
        call_ev_bb = (
            equity_edge * (node.pot_before + node.to_call) / max(node.bb, 1)
            if equity_edge is not None
            else None
        )
        detail: dict[str, object] = {
            "estimated_equity": equity,
            "required_equity": required,
            "equity_edge": equity_edge,
            "estimated_call_ev_bb": call_ev_bb,
            "villain_range_key": range_key,
            "villain_combo_count": len(villain_range),
            "mc_samples_requested": max(1, self.mc_samples),
            "samples_evaluated": result.samples,
            "estimate_kind": "heuristic_severity_not_solver_ev",
        }
        actions: tuple[tuple[str, float], ...]

        if node.to_call > 0:
            assert required is not None
            if equity >= required + 0.15:
                actions = (("call", 0.70), ("raise", 0.30))
                best = "call"
            elif equity >= required + 0.03:
                actions = (("call", 0.90), ("fold", 0.10))
                best = "call"
            elif equity >= required - 0.02:
                actions = (("call", 0.60), ("fold", 0.40))
                best = "call"
            else:
                actions = (("fold", 1.0),)
                best = "fold"
            return GtoSuggestion(
                actions=actions,
                best_action=best,
                source="equity_backend",
                detail=detail,
            )

        if equity >= 0.68:
            actions = (("bet", 0.80), ("check", 0.20))
            best = "bet"
        elif equity >= 0.55:
            actions = (("bet", 0.60), ("check", 0.40))
            best = "bet"
        else:
            actions = (("check", 1.0),)
            best = "check"
        return GtoSuggestion(
            actions=actions,
            best_action=best,
            source="equity_backend",
            detail=detail,
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
