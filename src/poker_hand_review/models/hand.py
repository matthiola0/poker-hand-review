"""單手手牌的不可變資料結構。"""

from __future__ import annotations

from dataclasses import dataclass

from .action import Action
from .cards import Card
from .enums import Street
from .tournament import TournamentInfo


@dataclass(frozen=True)
class SeatInfo:
    seat: int
    player: str
    stack: int
    is_hero: bool


@dataclass(frozen=True)
class StreetState:
    street: Street
    board: tuple[Card, ...]          # 該街揭露後的完整公共牌
    actions: tuple[Action, ...]


@dataclass(frozen=True)
class ShowdownResult:
    player: str
    hole: tuple[Card, ...] | None    # None = 未亮牌 / muck
    won: int                          # 此玩家收得籌碼（0 表示沒贏）
    hand_rank_text: str               # "three of a kind, Aces"
    mucked: bool = False


@dataclass(frozen=True)
class Hand:
    hand_id: str                      # "TM6030071921"
    tournament: TournamentInfo
    table: str                        # "105"
    max_seats: int                    # 8
    button_seat: int
    seats: tuple[SeatInfo, ...]
    hero: str                         # 通常 "Hero"
    hero_hole: tuple[Card, Card]
    streets: tuple[StreetState, ...]
    final_board: tuple[Card, ...]
    showdowns: tuple[ShowdownResult, ...]
    total_pot: int
    raw_unparsed: tuple[str, ...] = ()  # 未知行，供除錯/回報

    @property
    def hero_seat(self) -> SeatInfo:
        return next(s for s in self.seats if s.is_hero)
