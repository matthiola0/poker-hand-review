"""對手群像：跨手聚合對手傾向，產生剝削建議與假設範圍。

樣本內對手匿名 ID 在同賽事穩定可聚合；跨賽事不保證同人，故以賽事為界。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import ActionType, Hand, Street


@dataclass(frozen=True)
class OpponentProfile:
    player: str
    hands: int
    vpip: float
    pfr: float
    three_bet: float
    fold_to_cbet: float
    tags: tuple[str, ...] = ()        # 如 ("loose-passive",)
    exploit_notes: tuple[str, ...] = ()
    assumed_range_key: str | None = None  # 餵給翻後 EquityBackend


@dataclass
class ProfileSet:
    by_player: dict[str, OpponentProfile] = field(default_factory=dict)

    def range_key_for(self, player: str) -> str | None:
        p = self.by_player.get(player)
        return p.assumed_range_key if p else None


def build_profiles(hands: list[Hand], hero: str = "Hero") -> ProfileSet:
    """以對手 ID 聚合傾向。"""
    seen: dict[str, int] = {}
    vpip: dict[str, int] = {}
    pfr: dict[str, int] = {}
    three_bet: dict[str, int] = {}

    for hand in hands:
        for seat in hand.seats:
            if seat.player != hero:
                seen[seat.player] = seen.get(seat.player, 0) + 1
        preflop = next((s for s in hand.streets if s.street == Street.PREFLOP), None)
        if preflop is None:
            continue
        voluntary: set[str] = set()
        raisers: list[str] = []
        for action in preflop.actions:
            if action.player == hero:
                continue
            if action.type in {ActionType.CALL, ActionType.BET, ActionType.RAISE}:
                voluntary.add(action.player)
            if action.type == ActionType.RAISE:
                if raisers:
                    three_bet[action.player] = three_bet.get(action.player, 0) + 1
                raisers.append(action.player)
        for player in voluntary:
            vpip[player] = vpip.get(player, 0) + 1
        for player in set(raisers):
            pfr[player] = pfr.get(player, 0) + 1

    profiles: dict[str, OpponentProfile] = {}
    for player, count in seen.items():
        vp = vpip.get(player, 0) / count if count else 0.0
        pf = pfr.get(player, 0) / count if count else 0.0
        tb = three_bet.get(player, 0) / count if count else 0.0
        tags, notes, range_key = _labels(vp, pf, tb)
        profiles[player] = OpponentProfile(
            player=player,
            hands=count,
            vpip=vp,
            pfr=pf,
            three_bet=tb,
            fold_to_cbet=0.0,
            tags=tags,
            exploit_notes=notes,
            assumed_range_key=range_key,
        )
    return ProfileSet(profiles)


def _labels(vpip: float, pfr: float, three_bet: float) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    tags: list[str] = []
    notes: list[str] = []
    range_key = "balanced"
    if vpip >= 0.35 and pfr < 0.16:
        tags.append("loose-passive")
        notes.append("可用較薄價值下注懲罰過度跟注")
        range_key = "wide_passive"
    elif vpip >= 0.30 and pfr >= 0.20:
        tags.append("loose-aggressive")
        notes.append("面對頻繁加注時擴大價值 3bet，降低邊緣 bluff")
        range_key = "wide_aggressive"
    elif vpip <= 0.15 and pfr <= 0.12:
        tags.append("tight")
        notes.append("偷盲可略加頻率，但被反擊時收斂")
        range_key = "tight"
    else:
        tags.append("balanced")
        notes.append("樣本尚未顯示明顯偏差")
    if three_bet >= 0.08:
        tags.append("3bet-heavy")
    return tuple(tags), tuple(notes), range_key
