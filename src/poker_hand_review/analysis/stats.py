"""統計引擎：在決策評分之上聚合 + 傳統撲克指標。

MTT 以籌碼 / BB 計（非 cash $bb/100）。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..enrich import HeroContext
from ..models import ActionType, Hand, HandEval, QualityTier, Street


@dataclass(frozen=True)
class StatsReport:
    hands: int
    # --- 在 DecisionEval 之上的 GTO 指標 ---
    gto_accuracy: float            # GOOD 決策比例
    ev_loss_per_100: float         # 每百手累計 EV 損失（BB）
    mistakes: int                  # MISTAKE 決策數
    # --- 傳統指標 ---
    vpip: float
    pfr: float
    three_bet: float
    fold_to_three_bet: float
    cbet: float
    wtsd: float
    wsd: float
    aggression_factor: float
    net_chips: int
    by_position_net: dict[str, int]


def compute_stats(
    hands: list[Hand],
    contexts: list[HeroContext],
    hand_evals: list[HandEval] | None = None,
) -> StatsReport:
    """聚合 Hero 指標。"""
    total = len(hands)
    vpip = sum(1 for c in contexts if c.preflop_role in {"open", "3bet", "call", "limp"})
    pfr = sum(1 for c in contexts if c.preflop_role in {"open", "3bet"})
    three_bet_opportunities = sum(
        1
        for c in contexts
        for d in c.decisions
        if d.street == Street.PREFLOP and d.facing == "raise"
    )
    three_bet = sum(
        1
        for c in contexts
        for d in c.decisions
        if d.street == Street.PREFLOP and d.facing == "raise" and d.hero_action.type == ActionType.RAISE
    )
    fold_to_three_bet_opportunities = sum(
        1
        for c in contexts
        for d in c.decisions
        if d.street == Street.PREFLOP and d.facing == "3bet"
    )
    fold_to_three_bet = sum(
        1
        for c in contexts
        for d in c.decisions
        if d.street == Street.PREFLOP and d.facing == "3bet" and d.hero_action.type == ActionType.FOLD
    )
    cbet_opportunities = 0
    cbets = 0
    aggression = 0
    calls = 0
    for hand, ctx in zip(hands, contexts):
        for street in hand.streets:
            if street.street in {Street.PREFLOP, Street.SHOWDOWN}:
                continue
            hero_actions = [a for a in street.actions if a.player == hand.hero]
            if street.street == Street.FLOP and ctx.preflop_role == "open" and ctx.saw_flop:
                cbet_opportunities += 1
                if hero_actions and hero_actions[0].type in {ActionType.BET, ActionType.RAISE}:
                    cbets += 1
            if not hero_actions:
                continue
            aggression += sum(1 for a in hero_actions if a.type in {ActionType.BET, ActionType.RAISE})
            calls += sum(1 for a in hero_actions if a.type == ActionType.CALL)

    saw_flop = sum(1 for c in contexts if c.saw_flop)
    went_showdown = sum(1 for c in contexts if c.saw_showdown)
    won_showdown = sum(
        1
        for hand, ctx in zip(hands, contexts)
        if ctx.saw_showdown
        and any(
            action.player == hand.hero and action.type == ActionType.COLLECT and action.amount > 0
            for street in hand.streets
            for action in street.actions
        )
    )
    evals = hand_evals or []
    decisions = [d for he in evals for d in he.decisions if d.tier != QualityTier.UNKNOWN]
    good = sum(1 for d in decisions if d.tier == QualityTier.GOOD)
    mistakes = sum(1 for d in decisions if d.tier == QualityTier.MISTAKE)
    total_ev_loss = sum(d.ev_loss_bb for d in decisions)
    by_position: dict[str, int] = {}
    for ctx in contexts:
        by_position[ctx.position.value] = by_position.get(ctx.position.value, 0) + ctx.net

    return StatsReport(
        hands=total,
        gto_accuracy=good / len(decisions) if decisions else 0.0,
        ev_loss_per_100=(total_ev_loss / total * 100) if total else 0.0,
        mistakes=mistakes,
        vpip=vpip / total if total else 0.0,
        pfr=pfr / total if total else 0.0,
        three_bet=three_bet / three_bet_opportunities if three_bet_opportunities else 0.0,
        fold_to_three_bet=(
            fold_to_three_bet / fold_to_three_bet_opportunities
            if fold_to_three_bet_opportunities
            else 0.0
        ),
        cbet=cbets / cbet_opportunities if cbet_opportunities else 0.0,
        wtsd=went_showdown / saw_flop if saw_flop else 0.0,
        wsd=won_showdown / went_showdown if went_showdown else 0.0,
        aggression_factor=aggression / calls if calls else float(aggression),
        net_chips=sum(c.net for c in contexts),
        by_position_net=by_position,
    )
