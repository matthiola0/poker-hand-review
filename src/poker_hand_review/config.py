"""全域組態：Hero、品質門檻、MC 樣本數、翻後後端。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .evaluate.quality import QualityThresholds


@dataclass(frozen=True)
class Config:
    hero: str = "Hero"
    mc_samples: int = 500
    postflop_backend: str = "equity"     # "equity"（預設）| "solver"（外部 adapter）
    solver_path: str | None = None       # 也可用 PHR_SOLVER_PATH/TEXAS_SOLVER_PATH
    color: bool = True
    thresholds: QualityThresholds = field(default_factory=QualityThresholds)


DEFAULT = Config()
