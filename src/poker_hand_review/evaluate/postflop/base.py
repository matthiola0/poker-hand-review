"""翻後評估後端介面。Equity 與 solver 後端皆實作此協定。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ...models import Card, GtoSuggestion, Street


@dataclass(frozen=True)
class PostflopNode:
    """一個翻後決策情境的最小輸入。"""

    street: Street
    hero_hole: tuple[Card, Card]
    board: tuple[Card, ...]
    pot_before: int
    to_call: int
    eff_stack: int
    villain_range_key: str | None   # 由 Opponent Profiler 提供的假設範圍識別
    bb: int


class PostflopBackend(Protocol):
    """可插拔翻後後端：EquityBackend（預設）/ SolverBackend（選用）。"""

    name: str

    def evaluate(self, node: PostflopNode) -> GtoSuggestion: ...
