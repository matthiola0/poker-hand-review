"""決策評分核心：對每個 Hero 決策算 GTO 建議與 EV 損失，定 tier/顏色。

翻前查 GTO 範圍表；翻後委派注入的 PostflopBackend。Evaluator 不知道
背後是 equity 還是 solver——後端隱於介面之後，可切換、可測試。
"""

from __future__ import annotations

from collections.abc import Mapping

from ..enrich import Decision, HeroContext, assign_positions
from ..gto.preflop_charts import ChartKey, lookup_with_detail, stack_bucket
from ..models import (
    ActionType,
    DecisionEval,
    GtoSuggestion,
    Hand,
    HandEval,
    Position,
    QualityTier,
    Street,
)
from .postflop import PostflopBackend, PostflopNode
from .quality import QualityThresholds, hand_tier, tier_from_ev_loss


class DecisionEvaluator:
    def __init__(
        self,
        postflop: PostflopBackend,
        thresholds: QualityThresholds | None = None,
        opponent_range_keys: Mapping[str, str | None] | None = None,
    ) -> None:
        self.postflop = postflop
        self.thresholds = thresholds or QualityThresholds()
        self.opponent_range_keys = opponent_range_keys or {}

    def evaluate_hand(self, hand: Hand, ctx: HeroContext) -> HandEval:
        """評估一手所有 Hero 決策，回傳逐決策 + 整手色。"""
        decisions: list[DecisionEval] = []
        for decision in ctx.decisions:
            if decision.street == Street.PREFLOP:
                decisions.append(self._eval_preflop(hand, ctx, decision))
            else:
                decisions.append(self._eval_postflop(hand, ctx, decision))
        return HandEval(
            hand_id=hand.hand_id,
            decisions=tuple(decisions),
            hand_tier=hand_tier(decisions),
            net_chips=ctx.net,
        )

    def _eval_preflop(self, hand: Hand, ctx: HeroContext, decision: Decision) -> DecisionEval:
        action_kind = _chart_action(decision)
        chart_key = ChartKey(
            hero_pos=ctx.position,
            vs_pos=_villain_position(hand, decision),
            action=action_kind,
            stack_bucket=stack_bucket(ctx.eff_stack_bb),
        )
        chart = lookup_with_detail(chart_key)
        if chart is None:
            return _unknown(hand, decision, "翻前圖表尚未涵蓋此情境")

        freq = chart.range.frequency(*hand.hero_hole)
        best = _best_preflop_action(decision, freq)
        suggestion = GtoSuggestion(
            actions=_preflop_actions(best, freq),
            best_action=best,
            source="preflop_chart",
            detail={
                **chart.detail,
                "effective_stack_bb": round(ctx.eff_stack_bb, 1),
                "hand_frequency": freq,
            },
        )
        ev_loss = _preflop_ev_loss(decision, best, freq, ctx.eff_stack_bb)
        tier = tier_from_ev_loss(ev_loss, self.thresholds)
        return DecisionEval(
            hand_id=hand.hand_id,
            street=decision.street,
            hero_action=decision.hero_action,
            suggestion=suggestion,
            ev_loss_bb=ev_loss,
            tier=tier,
            explanation=_explain(decision, suggestion, ev_loss),
        )

    def _eval_postflop(self, hand: Hand, ctx: HeroContext, decision: Decision) -> DecisionEval:
        street = next((s for s in hand.streets if s.street == decision.street), None)
        if street is None:
            return _unknown(hand, decision, "找不到街段資料")

        node = PostflopNode(
            street=decision.street,
            hero_hole=hand.hero_hole,
            board=street.board,
            pot_before=decision.pot_before,
            to_call=decision.to_call,
            eff_stack=int(ctx.eff_stack_bb * hand.tournament.bb),
            villain_range_key=(
                self.opponent_range_keys.get(decision.villain)
                if decision.villain is not None
                else None
            ),
            bb=hand.tournament.bb,
        )
        suggestion = self.postflop.evaluate(node)
        ev_loss = _postflop_ev_loss(decision, suggestion, hand.tournament.bb)
        tier = tier_from_ev_loss(ev_loss, self.thresholds)
        return DecisionEval(
            hand_id=hand.hand_id,
            street=decision.street,
            hero_action=decision.hero_action,
            suggestion=suggestion,
            ev_loss_bb=ev_loss,
            tier=tier,
            explanation=_explain(decision, suggestion, ev_loss),
        )


def _unknown(hand: Hand, decision: Decision, reason: str) -> DecisionEval:
    return DecisionEval(
        hand_id=hand.hand_id,
        street=decision.street,
        hero_action=decision.hero_action,
        suggestion=GtoSuggestion(actions=(("unknown", 1.0),), best_action="unknown", source="unknown"),
        ev_loss_bb=0.0,
        tier=QualityTier.UNKNOWN,
        explanation=reason,
    )


def _chart_action(decision: Decision) -> str:
    if decision.facing == "unopened":
        return "rfi"
    if decision.facing == "3bet":
        return "vs_3bet"
    return "vs_rfi"


def _villain_position(hand: Hand, decision: Decision) -> Position | None:
    if decision.villain is None or decision.facing == "unopened":
        return None
    return assign_positions(hand).get(decision.villain)


def _best_preflop_action(decision: Decision, freq: float) -> str:
    if freq <= 0:
        return "check" if decision.facing == "unopened" and decision.hero_action.type == ActionType.CHECK else "fold"
    if decision.facing == "unopened":
        return "raise"
    if decision.facing == "3bet" and freq >= 0.8:
        return "raise"
    return "call"


def _preflop_actions(best: str, freq: float) -> tuple[tuple[str, float], ...]:
    if best in {"fold", "check"}:
        return ((best, 1.0),)
    passive = "fold" if best in {"call", "raise"} else "check"
    return ((best, max(freq, 0.5)), (passive, max(0.0, 1.0 - freq)))


def _preflop_ev_loss(decision: Decision, best: str, freq: float, eff_stack_bb: float) -> float:
    hero = decision.hero_action.type.value
    if hero == best or (best == "call" and hero == "raise" and freq >= 0.8):
        return 0.0
    if freq <= 0 and hero in {"call", "raise", "bet"}:
        return 2.2 if decision.facing in {"raise", "3bet"} else 1.0
    if freq > 0 and hero in {"fold", "check"}:
        return min(2.5, max(0.7, eff_stack_bb / 40))
    return 0.8


def _postflop_ev_loss(decision: Decision, suggestion: GtoSuggestion, bb: int) -> float:
    hero = decision.hero_action.type.value
    suggested = {action for action, freq in suggestion.actions if freq > 0.0}
    if hero in suggested or hero == suggestion.best_action:
        return 0.0
    equity = _detail_float(suggestion, "estimated_equity")
    required = _detail_float(suggestion, "required_equity")
    if suggestion.source == "equity_backend" and equity is not None:
        if decision.to_call and required is not None:
            call_ev_bb = (
                (equity - required)
                * (decision.pot_before + decision.to_call)
                / max(bb, 1)
            )
            if hero == "fold":
                return min(5.0, max(0.0, call_ev_bb))
            if hero == "call":
                return min(5.0, max(0.0, -call_ev_bb))
            if hero in {"bet", "raise"}:
                risk_bb = max(
                    decision.hero_action.amount,
                    decision.hero_action.to_amount,
                    decision.to_call,
                ) / max(bb, 1)
                if suggestion.best_action == "fold":
                    return min(
                        5.0,
                        max(-call_ev_bb, risk_bb * (0.5 + max(0.0, required - equity))),
                    )
                return min(5.0, max(0.5, risk_bb * 0.35))
        if hero in {"bet", "raise"} and suggestion.best_action == "check":
            risk_bb = max(
                decision.hero_action.amount,
                decision.hero_action.to_amount,
                decision.pot_before // 2,
            ) / max(bb, 1)
            return min(5.0, max(0.5, risk_bb * (0.5 + max(0.0, 0.55 - equity))))
        if hero == "check" and suggestion.best_action == "bet":
            opportunity_bb = decision.pot_before / max(bb, 1)
            return min(5.0, max(0.5, opportunity_bb * max(0.0, equity - 0.55)))
    if decision.to_call:
        return min(3.0, max(0.5, decision.to_call / max(bb, 1) * 0.75))
    return 0.8


def _detail_float(suggestion: GtoSuggestion, key: str) -> float | None:
    value = suggestion.detail.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _explain(decision: Decision, suggestion: GtoSuggestion, ev_loss: float) -> str:
    if suggestion.best_action == "unknown":
        return "資訊不足，暫不評分"
    if ev_loss < 0.01:
        if suggestion.source == "equity_backend":
            return _explain_equity(suggestion, aligned=True, ev_loss=ev_loss)
        return f"符合目前 {suggestion.source} 建議"
    if suggestion.source == "equity_backend":
        return _explain_equity(suggestion, aligned=False, ev_loss=ev_loss)
    return f"建議 {suggestion.best_action}；目前動作偏離約 {ev_loss:.2f}bb"


def _explain_equity(suggestion: GtoSuggestion, *, aligned: bool, ev_loss: float) -> str:
    equity = _detail_float(suggestion, "estimated_equity")
    required = _detail_float(suggestion, "required_equity")
    range_key = suggestion.detail.get("villain_range_key", "balanced")
    equity_text = f"estimated equity {equity:.1%}" if equity is not None else "estimated equity unavailable"
    required_text = f" vs {required:.1%} required" if required is not None else ""
    verdict = "action aligns" if aligned else f"recommend {suggestion.best_action}"
    return (
        f"{equity_text}{required_text} against {range_key} range; {verdict}. "
        f"Severity estimate {ev_loss:.2f}bb; not exact solver EV."
    )
