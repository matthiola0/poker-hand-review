"""決策評分模型：tier（顏色）、GTO 建議、逐決策與整手評估結果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .action import Action
from .enums import Street


class QualityTier(Enum):
    """每個決策的品質等級；顏色即其視覺化。"""

    GOOD = "good"            # 綠：目前模型未標示明顯偏差
    INACCURACY = "inaccuracy"  # 黃：估算偏差較小，值得複查
    MISTAKE = "mistake"     # 紅：估算偏差較大，優先複查
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
    ev_loss_bb: float          # 相容欄位名：BB 尺度的嚴重度估算，並非 solver 動作 EV 差
    tier: QualityTier
    explanation: str           # 字面文字（CLI 用；維持原語言）
    explanation_key: str = ""  # i18n key；Web 端依介面語言翻譯，缺則退回 explanation
    explanation_params: dict[str, object] = field(default_factory=dict)
    ev_loss_kind: str = "heuristic_severity"  # "unavailable" 表示未評分

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
