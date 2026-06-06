"""Equity 引擎測試（M3）。以教科書已知勝率驗證。"""

from __future__ import annotations

import pytest

from poker_hand_review.analysis import equity
from poker_hand_review.models import parse_cards


@pytest.mark.skip(reason="M3 待實作")
def test_aa_vs_kk_preflop():
    aa = parse_cards("As Ah")
    kk = parse_cards("Ks Kh")
    result = equity.equity_vs_hand(aa, kk, ())
    assert result.win == pytest.approx(0.82, abs=0.01)


def test_pot_odds():
    # 跟注 100 進 200 底池 -> 100 / 300
    assert equity.pot_odds(100, 200) == pytest.approx(1 / 3)


def test_ev_call_positive_when_equity_high():
    assert equity.ev_call(0.8, 200, 100) > 0
