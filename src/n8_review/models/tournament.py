"""錦標賽與級別中介資料。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TournamentInfo:
    tid: str            # "287580360"
    name: str           # "Bounty Hunters Special $10.80 Hold'em No Limit"
    buyin: str          # "$10.80"
    level: int          # 6
    sb: int             # 150
    bb: int             # 300
    ante: int           # 45
    ts: datetime        # 2026-06-02 18:50:00
