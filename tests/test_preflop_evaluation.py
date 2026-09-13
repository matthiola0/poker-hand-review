import pytest

from poker_hand_review.enrich import Decision
from poker_hand_review.evaluate.evaluator import _preflop_ev_loss_profile
from poker_hand_review.models import Action, ActionType, Street


@pytest.mark.parametrize(
    ("all_in", "profile", "supported"),
    [
        (True, {"raise": 1.0, "allin": 0.0}, False),
        (False, {"raise": 0.0, "allin": 1.0}, False),
        (True, {"raise": 0.0, "allin": 1.0}, True),
        (False, {"raise": 1.0, "allin": 0.0}, True),
        (True, {"raise": 0.04, "allin": 0.04, "fold": 0.92}, False),
    ],
)
def test_preflop_raise_and_allin_use_separate_chart_frequencies(all_in, profile, supported):
    decision = Decision(
        street=Street.PREFLOP,
        facing="unopened",
        villain=None,
        pot_before=150,
        to_call=0,
        hero_action=Action("Hero", ActionType.RAISE, amount=3000, all_in=all_in),
        pot_odds=None,
    )

    loss = _preflop_ev_loss_profile(decision, profile, 30.0)

    assert (loss == 0.0) is supported
