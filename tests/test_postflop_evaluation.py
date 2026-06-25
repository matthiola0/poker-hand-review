from __future__ import annotations

import pytest

from poker_hand_review.analysis.equity import EquityResult
from poker_hand_review.enrich import Decision
from poker_hand_review.evaluate.evaluator import _explain, _postflop_ev_loss
from poker_hand_review.evaluate.postflop import EquityBackend, PostflopNode
from poker_hand_review.models import Action, ActionType, Street, parse_cards


def _node(*, to_call: int = 40, range_key: str | None = "balanced") -> PostflopNode:
    return PostflopNode(
        street=Street.FLOP,
        hero_hole=parse_cards("Ah Kh"),  # type: ignore[arg-type]
        board=parse_cards("As 7d 2c"),
        pot_before=100,
        to_call=to_call,
        eff_stack=1_000,
        villain_range_key=range_key,
        bb=20,
    )


def _decision(action_type: ActionType, *, amount: int = 0, to_call: int = 40) -> Decision:
    return Decision(
        street=Street.FLOP,
        facing="bet" if to_call else "checked",
        villain="villain",
        pot_before=100,
        to_call=to_call,
        hero_action=Action("Hero", action_type, amount=amount),
        pot_odds=to_call / (100 + to_call) if to_call else None,
    )


def test_equity_backend_exposes_structured_diagnostics(monkeypatch):
    def fake_equity(*args: object, samples: int) -> EquityResult:
        del args
        return EquityResult(win=0.45, tie=0.10, lose=0.45, samples=samples, exact=False)

    monkeypatch.setattr(
        "poker_hand_review.evaluate.postflop.equity_backend.equity_vs_range",
        fake_equity,
    )

    suggestion = EquityBackend(mc_samples=777).evaluate(_node())

    assert suggestion.detail["estimated_equity"] == pytest.approx(0.5)
    assert suggestion.detail["required_equity"] == pytest.approx(40 / 140)
    assert suggestion.detail["equity_edge"] == pytest.approx(0.5 - 40 / 140)
    assert suggestion.detail["villain_range_key"] == "balanced"
    assert suggestion.detail["villain_combo_count"] > 0
    assert suggestion.detail["mc_samples_requested"] == 777
    assert suggestion.detail["samples_evaluated"] == 777
    assert suggestion.detail["estimate_kind"] == "heuristic_severity_not_solver_ev"


@pytest.mark.parametrize(
    ("equity", "expected"),
    [
        (0.60, "call"),
        (0.28, "call"),
        (0.10, "fold"),
    ],
)
def test_equity_backend_distinguishes_profitable_marginal_and_clear_fold_spots(
    monkeypatch, equity: float, expected: str
):
    def fake_equity(*args: object, samples: int) -> EquityResult:
        del args
        return EquityResult(win=equity, tie=0.0, lose=1 - equity, samples=samples, exact=False)

    monkeypatch.setattr(
        "poker_hand_review.evaluate.postflop.equity_backend.equity_vs_range",
        fake_equity,
    )

    suggestion = EquityBackend(mc_samples=10).evaluate(_node())

    assert suggestion.best_action == expected


@pytest.mark.parametrize(
    ("equity", "expected"),
    [
        (0.72, "bet"),
        (0.58, "bet"),
        (0.35, "check"),
    ],
)
def test_equity_backend_distinguishes_check_and_bet_spots(
    monkeypatch, equity: float, expected: str
):
    def fake_equity(*args: object, samples: int) -> EquityResult:
        del args
        return EquityResult(win=equity, tie=0.0, lose=1 - equity, samples=samples, exact=False)

    monkeypatch.setattr(
        "poker_hand_review.evaluate.postflop.equity_backend.equity_vs_range",
        fake_equity,
    )

    suggestion = EquityBackend(mc_samples=10).evaluate(_node(to_call=0))

    assert suggestion.best_action == expected


def test_profile_range_can_change_recommendation(monkeypatch):
    def fake_equity(hero: object, villain_range: object, board: object, samples: int) -> EquityResult:
        del hero, board
        equity = 0.60 if len(villain_range) > 500 else 0.10  # type: ignore[arg-type]
        return EquityResult(win=equity, tie=0.0, lose=1 - equity, samples=samples, exact=False)

    monkeypatch.setattr(
        "poker_hand_review.evaluate.postflop.equity_backend.equity_vs_range",
        fake_equity,
    )
    backend = EquityBackend(mc_samples=10)

    tight = backend.evaluate(_node(range_key="tight"))
    wide = backend.evaluate(_node(range_key="wide_passive"))

    assert tight.best_action == "fold"
    assert wide.best_action == "call"


def test_postflop_severity_uses_estimated_equity_edge_and_action_risk(monkeypatch):
    equities = iter((0.60, 0.10, 0.10))

    def fake_equity(*args: object, samples: int) -> EquityResult:
        del args
        equity = next(equities)
        return EquityResult(win=equity, tie=0.0, lose=1 - equity, samples=samples, exact=False)

    monkeypatch.setattr(
        "poker_hand_review.evaluate.postflop.equity_backend.equity_vs_range",
        fake_equity,
    )
    backend = EquityBackend(mc_samples=10)

    profitable_call = backend.evaluate(_node())
    clear_fold = backend.evaluate(_node())
    clear_fold_for_raise = backend.evaluate(_node())

    overfold = _postflop_ev_loss(_decision(ActionType.FOLD), profitable_call, 20)
    overcall = _postflop_ev_loss(_decision(ActionType.CALL, amount=40), clear_fold, 20)
    spew = _postflop_ev_loss(_decision(ActionType.RAISE, amount=160), clear_fold_for_raise, 20)

    assert overfold > 0.5
    assert overcall > 0.5
    assert spew > overcall


def test_equity_explanation_labels_severity_as_non_solver_estimate(monkeypatch):
    def fake_equity(*args: object, samples: int) -> EquityResult:
        del args
        return EquityResult(win=0.10, tie=0.0, lose=0.90, samples=samples, exact=False)

    monkeypatch.setattr(
        "poker_hand_review.evaluate.postflop.equity_backend.equity_vs_range",
        fake_equity,
    )
    suggestion = EquityBackend(mc_samples=10).evaluate(_node(range_key="tight"))

    explanation = _explain(_decision(ActionType.CALL, amount=40), suggestion, 1.3)

    assert "estimated equity 10.0%" in explanation
    assert "tight range" in explanation
    assert "not exact solver EV" in explanation
