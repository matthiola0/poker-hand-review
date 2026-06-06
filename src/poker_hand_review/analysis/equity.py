"""權益 / EV 引擎：牌力評估、勝率、底池賠率、EV。

純函式、無狀態，方便用已知勝率牌局做單元測試（見 tests/test_equity.py）。
牌力評估採 treys（7 張快速評估器）。
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations
from dataclasses import dataclass
import random

from ..models import Card


@dataclass(frozen=True)
class EquityResult:
    win: float
    tie: float
    lose: float
    samples: int          # 精確列舉時 = 列舉數；MC 時 = 樣本數
    exact: bool


def equity_vs_hand(
    hero: tuple[Card, ...],
    villain: tuple[Card, ...],
    board: tuple[Card, ...],
) -> EquityResult:
    """已知雙方底牌，對剩餘公共牌精確列舉勝率。"""
    known = tuple(hero) + tuple(villain) + tuple(board)
    _assert_unique(known)
    missing = 5 - len(board)
    if missing < 0:
        raise ValueError("board 最多只能有 5 張")

    wins = ties = losses = samples = 0
    deck = [c for c in _deck() if c not in known]
    for runout in combinations(deck, missing):
        outcome = _compare(hero, villain, tuple(board) + tuple(runout))
        samples += 1
        if outcome > 0:
            wins += 1
        elif outcome == 0:
            ties += 1
        else:
            losses += 1
    return _result(wins, ties, losses, samples, exact=True)


def equity_vs_range(
    hero: tuple[Card, ...],
    villain_range: list[tuple[Card, ...]],
    board: tuple[Card, ...],
    samples: int = 20_000,
) -> EquityResult:
    """對假設範圍做 Monte Carlo 勝率估計。"""
    known = tuple(hero) + tuple(board)
    _assert_unique(known)
    candidates = [
        tuple(v)
        for v in villain_range
        if len(v) == 2 and not set(v).intersection(known) and len(set(v)) == 2
    ]
    if not candidates:
        return EquityResult(0.0, 0.0, 0.0, 0, exact=False)

    rng = random.Random(0)
    wins = ties = losses = 0
    target = max(1, samples)
    for _ in range(target):
        villain = rng.choice(candidates)
        used = set(known).union(villain)
        deck = [c for c in _deck() if c not in used]
        runout = tuple(rng.sample(deck, 5 - len(board))) if len(board) < 5 else ()
        outcome = _compare(hero, villain, tuple(board) + runout)
        if outcome > 0:
            wins += 1
        elif outcome == 0:
            ties += 1
        else:
            losses += 1
    return _result(wins, ties, losses, target, exact=False)


def pot_odds(to_call: int, pot_before: int) -> float:
    """跟注所需的底池賠率 = to_call / (pot_before + to_call)。"""
    denom = pot_before + to_call
    return to_call / denom if denom else 0.0


def ev_call(equity: float, pot_before: int, to_call: int) -> float:
    """跟注 EV = equity*(pot_before+to_call) - (1-equity)*to_call。"""
    return equity * (pot_before + to_call) - (1 - equity) * to_call


def _deck() -> tuple[Card, ...]:
    ranks = "23456789TJQKA"
    suits = "shdc"
    return tuple(Card(rank, suit) for rank in ranks for suit in suits)


def _assert_unique(cards: Sequence[Card]) -> None:
    if len(set(cards)) != len(cards):
        raise ValueError("牌組中有重複牌")


def _compare(hero: tuple[Card, ...], villain: tuple[Card, ...], board: tuple[Card, ...]) -> int:
    treys = _treys()
    if treys is not None:
        evaluator, treys_card = treys
        hero_score = evaluator.evaluate(_to_treys(board, treys_card), _to_treys(hero, treys_card))
        villain_score = evaluator.evaluate(_to_treys(board, treys_card), _to_treys(villain, treys_card))
        if hero_score < villain_score:
            return 1
        if hero_score == villain_score:
            return 0
        return -1

    hero_score = _best_score(tuple(hero) + tuple(board))
    villain_score = _best_score(tuple(villain) + tuple(board))
    if hero_score > villain_score:
        return 1
    if hero_score == villain_score:
        return 0
    return -1


def _to_treys(cards: tuple[Card, ...], treys_card: object) -> list[int]:
    return [treys_card.new(str(card)) for card in cards]  # type: ignore[attr-defined]


def _treys() -> tuple[object, object] | None:
    try:
        from treys import Card as TreysCard
        from treys import Evaluator
    except ImportError:
        return None
    return Evaluator(), TreysCard


def _result(wins: int, ties: int, losses: int, samples: int, exact: bool) -> EquityResult:
    if samples == 0:
        return EquityResult(0.0, 0.0, 0.0, 0, exact=exact)
    return EquityResult(wins / samples, ties / samples, losses / samples, samples, exact)


def _best_score(cards: tuple[Card, ...]) -> tuple[int, tuple[int, ...]]:
    return max(_five_card_score(tuple(combo)) for combo in combinations(cards, 5))


def _five_card_score(cards: tuple[Card, ...]) -> tuple[int, tuple[int, ...]]:
    ranks = sorted((_rank_value(card.rank) for card in cards), reverse=True)
    counts: dict[int, int] = {}
    for rank in ranks:
        counts[rank] = counts.get(rank, 0) + 1

    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    flush = len({card.suit for card in cards}) == 1
    straight_high = _straight_high(ranks)

    if flush and straight_high:
        return (8, (straight_high,))
    if groups[0][1] == 4:
        quad = groups[0][0]
        kicker = max(rank for rank in ranks if rank != quad)
        return (7, (quad, kicker))
    if groups[0][1] == 3 and groups[1][1] == 2:
        return (6, (groups[0][0], groups[1][0]))
    if flush:
        return (5, tuple(ranks))
    if straight_high:
        return (4, (straight_high,))
    if groups[0][1] == 3:
        trips = groups[0][0]
        kickers = tuple(rank for rank in ranks if rank != trips)
        return (3, (trips,) + kickers)
    if groups[0][1] == 2 and groups[1][1] == 2:
        high_pair, low_pair = sorted((groups[0][0], groups[1][0]), reverse=True)
        kicker = max(rank for rank in ranks if rank not in {high_pair, low_pair})
        return (2, (high_pair, low_pair, kicker))
    if groups[0][1] == 2:
        pair = groups[0][0]
        kickers = tuple(rank for rank in ranks if rank != pair)
        return (1, (pair,) + kickers)
    return (0, tuple(ranks))


def _straight_high(ranks: list[int]) -> int | None:
    unique = sorted(set(ranks), reverse=True)
    if {14, 5, 4, 3, 2}.issubset(unique):
        return 5
    for i in range(len(unique) - 4):
        window = unique[i : i + 5]
        if window[0] - window[-1] == 4:
            return window[0]
    return None


def _rank_value(rank: str) -> int:
    return "23456789TJQKA".index(rank) + 2
