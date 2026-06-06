"""決策評分模型：tier（顏色）、GTO 建議、逐決策與整手評估結果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .action import Action
from .enums import Street


class QualityTier(Enum):
    """每個決策的品質等級；顏色即其視覺化。"""

    GOOD = "good"            # 綠：與 GTO 一致 / EV 損失可忽略
    INACCURACY = "inaccuracy"  # 黃：偏離 GTO 頻率但可辯護 / 小 EV 損失
    MISTAKE = "mistake"     # 紅：明顯 EV 損失 / 被支配的動作
    UNKNOWN = "unknown"     # 灰：資訊不足（如翻後後端未啟用）


# tier -> 顏色（rich 終端色名；Web 端另有對應，語意一致，見 SDD §6.3）
TIER_COLOR: dict[QualityTier, str] = {
    QualityTier.GOOD: "green",
    QualityTier.INACCURACY: "yellow",
    QualityTier.MISTAKE: "red",
    QualityTier.UNKNOWN: "grey50",
}


@dataclass(frozen=True)
class GtoSuggestion:
    actions: tuple[tuple[str, float], ...]  # [("raise", 0.7), ("call", 0.3)]
    best_action: str
    source: str                              # "preflop_chart"|"equity_backend"|"solver"
    detail: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionEval:
    hand_id: str
    street: Street
    hero_action: Action
    suggestion: GtoSuggestion
    ev_loss_bb: float          # GTO 最優 EV - Hero 動作 EV（BB 計，≥0）
    tier: QualityTier
    explanation: str

    @property
    def color(self) -> str:
        return TIER_COLOR[self.tier]


@dataclass(frozen=True)
class HandEval:
    hand_id: str
    decisions: tuple[DecisionEval, ...]
    hand_tier: QualityTier     # 整手色 = 最差決策（或加權，見 evaluate.quality）
    net_chips: int

    @property
    def color(self) -> str:
        return TIER_COLOR[self.hand_tier]
