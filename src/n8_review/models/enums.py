"""列舉型別：街段、位置、動作種類、嚴重度。"""

from __future__ import annotations

from enum import Enum


class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


class Position(Enum):
    """8-max 位置；實際指派依在座人數與按鈕位置由 enrich 層動態決定。"""

    BTN = "BTN"
    SB = "SB"
    BB = "BB"
    UTG = "UTG"
    UTG1 = "UTG+1"
    MP = "MP"
    HJ = "HJ"
    CO = "CO"


class ActionType(Enum):
    ANTE = "ante"
    POST_SB = "small_blind"
    POST_BB = "big_blind"
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    SHOW = "show"
    COLLECT = "collect"
    UNCALLED = "uncalled"


class Severity(Enum):
    INFO = "info"
    WARN = "warn"
    LEAK = "leak"
