"""EV 損失 -> QualityTier -> 顏色的分級邏輯，與整手色彙整。"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import DecisionEval, QualityTier


@dataclass(frozen=True)
class QualityThresholds:
    """EV 損失（BB）分級門檻，GTO 錨定、可調（見 SDD §4、§11）。"""

    inaccuracy_bb: float = 0.5   # ev_loss < 此 => GOOD
    mistake_bb: float = 2.0      # 此 ≤ ev_loss => MISTAKE，之間 => INACCURACY


def tier_from_ev_loss(ev_loss_bb: float, th: QualityThresholds) -> QualityTier:
    if ev_loss_bb < th.inaccuracy_bb:
        return QualityTier.GOOD
    if ev_loss_bb < th.mistake_bb:
        return QualityTier.INACCURACY
    return QualityTier.MISTAKE


_SEVERITY = {
    QualityTier.GOOD: 0,
    QualityTier.UNKNOWN: 1,
    QualityTier.INACCURACY: 2,
    QualityTier.MISTAKE: 3,
}


def hand_tier(decisions: list[DecisionEval]) -> QualityTier:
    """整手色 = 最差決策；無決策回 UNKNOWN。"""
    if not decisions:
        return QualityTier.UNKNOWN
    return max((d.tier for d in decisions), key=lambda t: _SEVERITY[t])
