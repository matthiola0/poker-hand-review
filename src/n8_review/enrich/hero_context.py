"""從 Hand 衍生 Hero 視角上下文：位置、有效籌碼、M、決策節點。"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Action, ActionType, Hand, Position, Street


@dataclass(frozen=True)
class Decision:
    """Hero 面對的一個決策節點。"""

    street: Street
    facing: str            # 'unopened' | 'raise' | 'bet' | '3bet' | 'allin' ...
    villain: str | None    # Hero 此決策面對的主要對手/最後攻擊者
    pot_before: int
    to_call: int
    hero_action: Action
    pot_odds: float | None


@dataclass(frozen=True)
class HeroContext:
    hand_id: str
    position: Position
    eff_stack_bb: float
    m_ratio: float
    preflop_role: str      # 'open'|'3bet'|'call'|'limp'|'fold'|'check'
    invested: int
    net: int
    saw_flop: bool
    saw_showdown: bool
    decisions: tuple[Decision, ...]


def build_context(hand: Hand) -> HeroContext:
    """從一手建立 HeroContext。

    Pot tracking intentionally stays conservative: it models visible
    contributions in the hand history and is accurate enough for decision
    context, stats, and the lightweight evaluator.
    """
    positions = assign_positions(hand)
    hero_stack = hand.hero_seat.stack
    villain_stacks = [s.stack for s in hand.seats if not s.is_hero]
    bb = hand.tournament.bb or 1
    eff_stack = min(hero_stack, max(villain_stacks, default=hero_stack))
    orbit_cost = hand.tournament.sb + hand.tournament.bb + hand.tournament.ante * len(hand.seats)

    decisions: list[Decision] = []
    invested_by_player = {s.player: 0 for s in hand.seats}
    pot = 0
    preflop_role = "fold"

    for street in hand.streets:
        committed = {s.player: 0 for s in hand.seats}
        raises_seen = 0
        max_commit = 0
        current_aggressor: str | None = None
        for action in street.actions:
            if action.player == hand.hero and action.type in _DECISION_ACTIONS:
                hero_commit = committed.get(hand.hero, 0)
                to_call = max(0, max_commit - hero_commit)
                facing = _facing(street.street, to_call, raises_seen)
                decisions.append(
                    Decision(
                        street=street.street,
                        facing=facing,
                        villain=current_aggressor if current_aggressor != hand.hero else None,
                        pot_before=pot,
                        to_call=to_call,
                        hero_action=action,
                        pot_odds=_pot_odds(to_call, pot) if to_call else None,
                    )
                )
                if street.street == Street.PREFLOP and preflop_role == "fold":
                    preflop_role = _preflop_role(action, facing)

            delta = _action_delta(action, committed)
            if delta:
                if action.type != ActionType.ANTE:
                    committed[action.player] = committed.get(action.player, 0) + delta
                invested_by_player[action.player] = invested_by_player.get(action.player, 0) + delta
                pot += delta
                max_commit = max(max_commit, committed[action.player])
            if action.type in {ActionType.BET, ActionType.RAISE}:
                raises_seen += 1
                current_aggressor = action.player
            elif action.type == ActionType.UNCALLED:
                returned = min(action.amount, committed.get(action.player, 0))
                committed[action.player] = committed.get(action.player, 0) - returned
                invested_by_player[action.player] = invested_by_player.get(action.player, 0) - returned
                pot -= returned

    hero_won = sum(
        action.amount
        for street in hand.streets
        for action in street.actions
        if action.player == hand.hero and action.type == ActionType.COLLECT
    )
    invested = invested_by_player.get(hand.hero, 0)
    return HeroContext(
        hand_id=hand.hand_id,
        position=positions.get(hand.hero, Position.BTN),
        eff_stack_bb=eff_stack / bb,
        m_ratio=hero_stack / orbit_cost if orbit_cost else 0.0,
        preflop_role=preflop_role,
        invested=invested,
        net=hero_won - invested,
        saw_flop=any(s.street == Street.FLOP for s in hand.streets),
        saw_showdown=any(s.player == hand.hero and s.hole for s in hand.showdowns),
        decisions=tuple(decisions),
    )


def assign_positions(hand: Hand) -> dict[str, Position]:
    """依按鈕與在座人數，回傳 player -> Position 對照表。"""
    seats = sorted(hand.seats, key=lambda s: s.seat)
    if not seats:
        return {}

    button_idx = next((i for i, s in enumerate(seats) if s.seat == hand.button_seat), 0)
    ordered = seats[button_idx:] + seats[:button_idx]
    position_order = _positions_for_count(len(ordered))
    return {seat.player: position_order[i] for i, seat in enumerate(ordered)}


_DECISION_ACTIONS = {
    ActionType.FOLD,
    ActionType.CHECK,
    ActionType.CALL,
    ActionType.BET,
    ActionType.RAISE,
}


def _positions_for_count(count: int) -> tuple[Position, ...]:
    by_count: dict[int, tuple[Position, ...]] = {
        2: (Position.BTN, Position.BB),
        3: (Position.BTN, Position.SB, Position.BB),
        4: (Position.BTN, Position.SB, Position.BB, Position.CO),
        5: (Position.BTN, Position.SB, Position.BB, Position.UTG, Position.CO),
        6: (Position.BTN, Position.SB, Position.BB, Position.UTG, Position.HJ, Position.CO),
        7: (Position.BTN, Position.SB, Position.BB, Position.UTG, Position.MP, Position.HJ, Position.CO),
        8: (
            Position.BTN,
            Position.SB,
            Position.BB,
            Position.UTG,
            Position.UTG1,
            Position.MP,
            Position.HJ,
            Position.CO,
        ),
    }
    if count in by_count:
        return by_count[count]
    return by_count[8][:count]


def _facing(street: Street, to_call: int, raises_seen: int) -> str:
    if street == Street.PREFLOP and raises_seen == 0:
        return "unopened"
    if to_call <= 0:
        return "checked"
    if raises_seen >= 2:
        return "3bet"
    return "raise" if street == Street.PREFLOP else "bet"


def _preflop_role(action: Action, facing: str) -> str:
    if action.type == ActionType.RAISE:
        return "open" if facing == "unopened" else "3bet"
    if action.type == ActionType.CALL:
        return "call"
    if action.type == ActionType.CHECK:
        return "check"
    return "fold"


def _action_delta(action: Action, committed: dict[str, int]) -> int:
    if action.type in {ActionType.ANTE, ActionType.POST_SB, ActionType.POST_BB, ActionType.CALL, ActionType.BET}:
        return action.amount
    if action.type == ActionType.RAISE:
        return max(0, action.to_amount - committed.get(action.player, 0))
    return 0


def _pot_odds(to_call: int, pot_before: int) -> float:
    denom = pot_before + to_call
    return to_call / denom if denom else 0.0
