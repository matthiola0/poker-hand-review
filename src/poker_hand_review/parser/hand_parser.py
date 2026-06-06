"""原始手牌區塊 -> Hand 物件的逐行狀態機。

策略：已知 token 嚴格解析；未知行記入 raw_unparsed 但不中斷，
以容忍不同賽事/版本的格式差異（見 SDD §2.4）。
"""

from __future__ import annotations

from datetime import datetime

from ..models import (
    Action,
    ActionType,
    Card,
    Hand,
    SeatInfo,
    ShowdownResult,
    Street,
    StreetState,
    TournamentInfo,
    parse_cards,
)
from . import patterns as P

_STREET_BY_MARKER = {
    "HOLE CARDS": Street.PREFLOP,
    "FLOP": Street.FLOP,
    "TURN": Street.TURN,
    "RIVER": Street.RIVER,
    "SHOWDOWN": Street.SHOWDOWN,
}


class HandParseError(ValueError):
    """無法解析最基本的標頭資訊時拋出。"""


def parse_hand(block: str, hero_name: str = "Hero") -> Hand:
    """把一個原始手牌字串解析為 Hand。

    TODO(M1): 完成各街動作累積與 SUMMARY 對帳；目前為架構骨架，
    已解析標頭/座位/Hero 底牌，街段動作以狀態機填入。
    """
    lines = block.splitlines()
    raw_unparsed: list[str] = []

    header = _parse_header(lines[0])
    table, max_seats, button = _parse_table(lines[1])

    seats: list[SeatInfo] = []
    hero_hole: tuple[Card, ...] = ()
    streets: dict[Street, list[Action]] = {}
    boards: dict[Street, tuple[Card, ...]] = {}
    showdowns: list[ShowdownResult] = []
    total_pot = 0
    current = Street.PREFLOP
    in_summary = False

    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue

        if m := P.STREET_MARKER.match(line):
            name = m.group("name").strip()
            if name == "SUMMARY":
                in_summary = True
                continue
            if name in _STREET_BY_MARKER:
                current = _STREET_BY_MARKER[name]
                streets.setdefault(current, [])
                if cards := m.group("cards"):
                    boards[current] = parse_cards(cards)
            continue

        if in_summary:
            _parse_summary(line, total_pot, showdowns, raw_unparsed)
            if mt := P.TOTAL_POT.match(line):
                total_pot = P.to_int(mt.group("amt"))
            continue

        # 座位
        if m := P.SEAT.match(line):
            player = m.group("player")
            seats.append(
                SeatInfo(int(m.group("seat")), player, P.to_int(m.group("stack")),
                         player == hero_name)
            )
            continue

        # Hero 底牌
        if m := P.DEALT.match(line):
            if m.group("player") == hero_name and m.group("cards"):
                hero_hole = parse_cards(m.group("cards"))
            continue

        # 一般動作
        action = _parse_action(line)
        if action is not None:
            streets.setdefault(current, []).append(action)
            continue

        raw_unparsed.append(line)

    street_states = tuple(
        StreetState(s, boards.get(s, ()), tuple(streets.get(s, [])))
        for s in (Street.PREFLOP, Street.FLOP, Street.TURN, Street.RIVER, Street.SHOWDOWN)
        if s in streets
    )
    final_board = boards.get(Street.RIVER) or boards.get(Street.TURN) or boards.get(Street.FLOP, ())

    if len(hero_hole) != 2:
        raise HandParseError(f"{header.tid}/{lines[0][:40]}: 找不到 Hero 底牌")

    return Hand(
        hand_id=_hand_id(lines[0]),
        tournament=header,
        table=table,
        max_seats=max_seats,
        button_seat=button,
        seats=tuple(seats),
        hero=hero_name,
        hero_hole=(hero_hole[0], hero_hole[1]),
        streets=street_states,
        final_board=final_board,
        showdowns=tuple(showdowns),
        total_pot=total_pot,
        raw_unparsed=tuple(raw_unparsed),
    )


def parse_hands(blocks: list[str], hero_name: str = "Hero") -> list[Hand]:
    return [parse_hand(b, hero_name) for b in blocks]


# --- 內部輔助 -------------------------------------------------------------

def _hand_id(header_line: str) -> str:
    m = P.HEADER.match(header_line)
    if not m:
        raise HandParseError(f"無法解析標頭: {header_line[:60]}")
    return m.group("hand_id")


def _parse_header(line: str) -> TournamentInfo:
    m = P.HEADER.match(line)
    if not m:
        raise HandParseError(f"無法解析標頭: {line[:60]}")
    name = m.group("name")
    buyin = next((tok for tok in name.split() if tok.startswith("$")), "")
    return TournamentInfo(
        tid=m.group("tid"),
        name=name,
        buyin=buyin,
        level=int(m.group("level")),
        sb=P.to_int(m.group("sb")),
        bb=P.to_int(m.group("bb")),
        ante=P.to_int(m.group("ante") or "0"),
        ts=datetime.strptime(m.group("ts"), "%Y/%m/%d %H:%M:%S"),
    )


def _parse_table(line: str) -> tuple[str, int, int]:
    m = P.TABLE.match(line)
    if not m:
        raise HandParseError(f"無法解析桌資訊: {line[:60]}")
    return m.group("table"), int(m.group("max")), int(m.group("button"))


def _parse_action(line: str) -> Action | None:
    if m := P.A_ANTE.match(line):
        return Action(m.group("player"), ActionType.ANTE, P.to_int(m.group("amt")))
    if m := P.A_SB.match(line):
        return Action(m.group("player"), ActionType.POST_SB, P.to_int(m.group("amt")))
    if m := P.A_BB.match(line):
        return Action(m.group("player"), ActionType.POST_BB, P.to_int(m.group("amt")))
    if m := P.A_FOLD.match(line):
        return Action(m.group("player"), ActionType.FOLD)
    if m := P.A_CHECK.match(line):
        return Action(m.group("player"), ActionType.CHECK)
    if m := P.A_CALL.match(line):
        return Action(m.group("player"), ActionType.CALL, P.to_int(m.group("amt")),
                      all_in=bool(m.group("allin")))
    if m := P.A_BET.match(line):
        return Action(m.group("player"), ActionType.BET, P.to_int(m.group("amt")),
                      all_in=bool(m.group("allin")))
    if m := P.A_RAISE.match(line):
        return Action(m.group("player"), ActionType.RAISE, P.to_int(m.group("amt")),
                      to_amount=P.to_int(m.group("to")), all_in=bool(m.group("allin")))
    if m := P.A_SHOW.match(line):
        return Action(m.group("player"), ActionType.SHOW)
    if m := P.UNCALLED.match(line):
        return Action(m.group("player"), ActionType.UNCALLED, P.to_int(m.group("amt")))
    if m := P.COLLECT.match(line):
        return Action(m.group("player"), ActionType.COLLECT, P.to_int(m.group("amt")))
    return None


def _parse_summary(
    line: str, total_pot: int, showdowns: list[ShowdownResult], raw: list[str]
) -> None:
    """解析 SUMMARY 區的 'Seat N: player ...' 攤牌結果。

    TODO(M1): 完整解析 'showed [..] and won (X) with <牌型>' / 'and lost with'
    / 'mucked' / 'folded ...'，填入 showdowns。目前僅擷取已亮牌者。
    """
    if m := P.SUMMARY_SEAT.match(line):
        rest = m.group("rest")
        if "showed [" in rest:
            cards_part = rest.split("showed [", 1)[1].split("]", 1)[0]
            won = 0
            if "won (" in rest:
                won = P.to_int(rest.split("won (", 1)[1].split(")", 1)[0])
            rank = rest.split(" with ", 1)[1] if " with " in rest else ""
            showdowns.append(
                ShowdownResult(m.group("player"), parse_cards(cards_part), won, rank)
            )
