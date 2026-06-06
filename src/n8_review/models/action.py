"""單一玩家動作。"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import ActionType


@dataclass(frozen=True)
class Action:
    player: str
    type: ActionType
    amount: int = 0          # 此動作投入金額（call/bet/post/ante）
    to_amount: int = 0       # raise X to Y 的 Y
    all_in: bool = False
