"""Regression tests for the SDD analysis pipeline."""

from __future__ import annotations

import json
import os
import sys

import pytest

from poker_hand_review.analysis.equity import EquityResult, equity_vs_hand
from poker_hand_review.analysis.stats import compute_stats
from poker_hand_review.enrich import build_context
from poker_hand_review.evaluate import DecisionEvaluator
from poker_hand_review.evaluate.postflop import EquityBackend, PostflopNode, SolverBackend, SolverBackendError
from poker_hand_review.gto import preflop_charts
from poker_hand_review.gto.preflop_charts import ChartKey, lookup_with_detail
from poker_hand_review.models import GtoSuggestion, Position, Street, parse_cards
from poker_hand_review.parser import parse_hand
from poker_hand_review.web_server import WebServerConfig, solve_payload


RFI_COLLECT = """Poker Hand #TMRFI: Tournament #1, Test $1 Hold'em No Limit - Level1(10/20(10)) - 2026/06/02 18:50:00
Table '1' 8-max Seat #1 is the button
Seat 1: Hero (1,000 in chips)
Seat 2: sb (1,000 in chips)
Seat 3: bb (1,000 in chips)
Hero: posts the ante 10
sb: posts the ante 10
bb: posts the ante 10
sb: posts small blind 10
bb: posts big blind 20
*** HOLE CARDS ***
Dealt to Hero [Ah Kh]
Hero: raises 100 to 200
sb: folds
bb: folds
*** SHOWDOWN ***
Hero collected 350 from pot
*** SUMMARY ***
Total pot 350 | Rake 0 | Jackpot 0
"""


THREE_BET = """Poker Hand #TM3BET: Tournament #1, Test $1 Hold'em No Limit - Level1(10/20(10)) - 2026/06/02 18:51:00
Table '1' 8-max Seat #1 is the button
Seat 1: villain (1,000 in chips)
Seat 2: sb (1,000 in chips)
Seat 3: Hero (1,000 in chips)
villain: posts the ante 10
sb: posts the ante 10
Hero: posts the ante 10
sb: posts small blind 10
Hero: posts big blind 20
*** HOLE CARDS ***
Dealt to Hero [As Ad]
villain: raises 20 to 40
sb: folds
Hero: raises 80 to 120
villain: folds
*** SHOWDOWN ***
Hero collected 180 from pot
*** SUMMARY ***
Total pot 180 | Rake 0 | Jackpot 0
"""


POSTFLOP_BET = """Poker Hand #TMPOST: Tournament #1, Test $1 Hold'em No Limit - Level1(10/20(10)) - 2026/06/02 18:52:00
Table '1' 8-max Seat #1 is the button
Seat 1: villain (1,000 in chips)
Seat 2: sb (1,000 in chips)
Seat 3: Hero (1,000 in chips)
villain: posts the ante 10
sb: posts the ante 10
Hero: posts the ante 10
sb: posts small blind 10
Hero: posts big blind 20
*** HOLE CARDS ***
Dealt to Hero [Kd Qd]
villain: raises 20 to 40
sb: folds
Hero: calls 20
*** FLOP *** [Kh 7d 2c]
villain: bets 60
Hero: folds
*** SHOWDOWN ***
villain collected 150 from pot
*** SUMMARY ***
Total pot 150 | Rake 0 | Jackpot 0
"""


def test_context_uses_collect_for_non_showdown_wins_and_keeps_ante_out_of_to_call():
    hand = parse_hand(RFI_COLLECT)
    ctx = build_context(hand)

    assert ctx.net == 140
    assert ctx.invested == 210
    assert ctx.preflop_role == "open"
    assert ctx.decisions[0].facing == "unopened"
    assert ctx.decisions[0].to_call == 20


def test_stats_use_preflop_opportunity_denominators():
    hands = [parse_hand(RFI_COLLECT), parse_hand(THREE_BET)]
    contexts = [build_context(hand) for hand in hands]
    stats = compute_stats(hands, contexts)

    assert contexts[0].decisions[0].facing == "unopened"
    assert contexts[1].decisions[0].facing == "raise"
    assert contexts[1].preflop_role == "3bet"
    assert stats.three_bet == pytest.approx(1.0)
    assert stats.pfr == pytest.approx(1.0)
    assert stats.net_chips == 190


def test_equity_backend_respects_configured_sample_count(monkeypatch):
    seen: dict[str, int] = {}

    def fake_equity_vs_range(*args: object, samples: int) -> EquityResult:
        del args
        seen["samples"] = samples
        return EquityResult(win=0.7, tie=0.0, lose=0.3, samples=samples, exact=False)

    monkeypatch.setattr(
        "poker_hand_review.evaluate.postflop.equity_backend.equity_vs_range",
        fake_equity_vs_range,
    )
    backend = EquityBackend(mc_samples=777)
    node = PostflopNode(
        street=Street.FLOP,
        hero_hole=parse_cards("Ah Kh"),  # type: ignore[arg-type]
        board=parse_cards("As 7d 2c"),
        pot_before=100,
        to_call=0,
        eff_stack=1_000,
        villain_range_key=None,
        bb=20,
    )

    backend.evaluate(node)

    assert seen["samples"] == 777


def test_evaluator_passes_profile_range_key_to_postflop_backend():
    captured: dict[str, str | None] = {}

    class CaptureBackend:
        name = "capture"

        def evaluate(self, node: PostflopNode) -> GtoSuggestion:
            captured["range_key"] = node.villain_range_key
            return GtoSuggestion(
                actions=(("fold", 1.0),),
                best_action="fold",
                source="capture",
            )

    hand = parse_hand(POSTFLOP_BET)
    ctx = build_context(hand)
    flop_decision = next(d for d in ctx.decisions if d.street == Street.FLOP)

    assert flop_decision.villain == "villain"

    evaluator = DecisionEvaluator(
        CaptureBackend(),
        opponent_range_keys={"villain": "tight"},
    )
    evaluator.evaluate_hand(hand, ctx)

    assert captured["range_key"] == "tight"


def test_preflop_chart_decision_carries_chart_detail():
    hand = parse_hand(RFI_COLLECT)
    ctx = build_context(hand)
    evaluator = DecisionEvaluator(EquityBackend(mc_samples=1))

    hand_eval = evaluator.evaluate_hand(hand, ctx)
    decision = hand_eval.decisions[0]

    assert decision.suggestion.source == "preflop_chart"
    assert decision.suggestion.detail["chart_source_type"] == "built_in_approx"
    assert decision.suggestion.detail["chart_id"] == "rfi_BTN_40bb"
    assert decision.suggestion.detail["stack_bucket"] == "40bb"
    assert decision.suggestion.detail["effective_stack_bb"] == 50.0
    assert decision.suggestion.detail["hand_frequency"] == pytest.approx(1.0)


def test_preflop_lookup_prefers_solver_chart_json(tmp_path, monkeypatch):
    chart_path = tmp_path / "vs_rfi_BB_vs_BTN_60bb+.json"
    chart_path.write_text(
        json.dumps(
            {
                "meta": {
                    "source": "unit-test solver",
                    "version": "v1",
                    "format": "test format",
                },
                "freqs": {"72o": 0.25, "AA": 1.0},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(preflop_charts, "CHART_DIR", tmp_path)

    chart = lookup_with_detail(
        ChartKey(
            hero_pos=Position.BB,
            vs_pos=Position.BTN,
            action="vs_rfi",
            stack_bucket="60bb+",
        )
    )

    assert chart is not None
    assert chart.range.freqs["72o"] == pytest.approx(0.25)
    assert chart.detail["chart_source_type"] == "solver_chart"
    assert chart.detail["chart_source"] == "unit-test solver"
    assert chart.detail["chart_id"] == "vs_rfi_BB_vs_BTN_60bb+"


def test_equity_backend_changes_candidate_range_by_profile_key(monkeypatch):
    lengths: list[int] = []

    def fake_equity_vs_range(*args: object, samples: int) -> EquityResult:
        del samples
        lengths.append(len(args[1]))  # villain_range
        return EquityResult(win=0.5, tie=0.0, lose=0.5, samples=1, exact=False)

    monkeypatch.setattr(
        "poker_hand_review.evaluate.postflop.equity_backend.equity_vs_range",
        fake_equity_vs_range,
    )
    backend = EquityBackend(mc_samples=1)
    base = dict(
        street=Street.FLOP,
        hero_hole=parse_cards("Ah Kh"),
        board=parse_cards("As 7d 2c"),
        pot_before=100,
        to_call=0,
        eff_stack=1_000,
        bb=20,
    )

    backend.evaluate(PostflopNode(**base, villain_range_key="tight"))  # type: ignore[arg-type]
    backend.evaluate(PostflopNode(**base, villain_range_key="wide_passive"))  # type: ignore[arg-type]

    assert lengths[1] > lengths[0]


def test_solver_backend_calls_external_adapter_and_parses_strategy(tmp_path):
    capture_path = tmp_path / "payload.json"
    solver_script = tmp_path / "fake_solver.py"
    solver_script.write_text(
        "\n".join(
            [
                "import json, pathlib, sys",
                "payload = json.loads(pathlib.Path(sys.argv[-1]).read_text(encoding='utf-8'))",
                f"pathlib.Path({str(capture_path)!r}).write_text(json.dumps(payload), encoding='utf-8')",
                "print(json.dumps({'actions': {'call': 0.7, 'fold': 0.3}}))",
            ]
        ),
        encoding="utf-8",
    )
    backend = SolverBackend(solver_path=sys.executable, solver_args=(str(solver_script),))
    node = PostflopNode(
        street=Street.FLOP,
        hero_hole=parse_cards("Ah Kh"),  # type: ignore[arg-type]
        board=parse_cards("As 7d 2c"),
        pot_before=100,
        to_call=40,
        eff_stack=1_000,
        villain_range_key="tight",
        bb=20,
    )

    suggestion = backend.evaluate(node)
    payload = json.loads(capture_path.read_text(encoding="utf-8"))

    assert payload["contract"] == "poker_hand_review.solver_node.v1"
    assert payload["candidate_actions"] == ["fold", "call", "raise"]
    assert payload["villain_range_key"] == "tight"
    assert suggestion.best_action == "call"
    assert suggestion.actions == (("call", 0.7), ("fold", 0.3))
    assert suggestion.source == "solver"


def test_solver_backend_requires_solver_path(monkeypatch):
    monkeypatch.delenv("PHR_SOLVER_PATH", raising=False)
    monkeypatch.delenv("TEXAS_SOLVER_PATH", raising=False)
    backend = SolverBackend(solver_path=None)
    node = PostflopNode(
        street=Street.FLOP,
        hero_hole=parse_cards("Ah Kh"),  # type: ignore[arg-type]
        board=parse_cards("As 7d 2c"),
        pot_before=100,
        to_call=0,
        eff_stack=1_000,
        villain_range_key=None,
        bb=20,
    )

    with pytest.raises(SolverBackendError, match="solver 後端需要"):
        backend.evaluate(node)


def test_web_solver_payload_returns_decision_eval(tmp_path):
    adapter = _fake_solver_adapter(tmp_path, {"raise": 0.9, "call": 0.1})
    config = WebServerConfig(
        root=tmp_path,
        report_path=None,
        solver_path=adapter,
        solver_timeout_sec=30,
    )
    payload = {
        "hand_id": "TMPOST",
        "decision_index": 0,
        "node": {
            "street": "flop",
            "hero_hole": ["Kd", "Qd"],
            "board": ["Kh", "7d", "2c"],
            "pot_before": 150,
            "to_call": 60,
            "eff_stack": 1000,
            "villain_range_key": "tight",
            "bb": 20,
        },
        "decision": {
            "street": "flop",
            "facing": "bet",
            "villain": "villain",
            "pot_before": 150,
            "to_call": 60,
            "hero_action": {
                "player": "Hero",
                "type": "fold",
                "amount": 0,
                "to_amount": 0,
                "all_in": False,
            },
            "pot_odds": 0.285,
        },
    }

    result = solve_payload(payload, config)
    decision_eval = result["decision_eval"]

    assert decision_eval["hand_id"] == "TMPOST"
    assert decision_eval["suggestion"]["source"] == "solver"
    assert decision_eval["suggestion"]["best_action"] == "raise"
    assert decision_eval["tier"] == "mistake"


def test_web_solver_payload_persists_report(tmp_path):
    adapter = _fake_solver_adapter(tmp_path, {"raise": 0.9, "call": 0.1})
    report_path = tmp_path / "report.json"
    old_decision = {
        "hand_id": "TMPOST",
        "street": "flop",
        "hero_action": {
            "player": "Hero",
            "type": "fold",
            "amount": 0,
            "to_amount": 0,
            "all_in": False,
        },
        "suggestion": {
            "actions": [["fold", 1.0]],
            "best_action": "fold",
            "source": "equity_backend",
        },
        "ev_loss_bb": 0.0,
        "tier": "good",
        "explanation": "old equity result",
    }
    report_path.write_text(
        json.dumps(
            {
                "schema": "0.1",
                "hands": [{"hand_id": "TMPOST"}],
                "hand_evals": [
                    {
                        "hand_id": "TMPOST",
                        "decisions": [old_decision],
                        "hand_tier": "good",
                        "net_chips": 0,
                    }
                ],
                "stats": {
                    "hands": 1,
                    "gto_accuracy": 1.0,
                    "ev_loss_per_100": 0.0,
                    "mistakes": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    config = WebServerConfig(
        root=tmp_path,
        report_path=report_path,
        solver_path=adapter,
        solver_timeout_sec=30,
    )
    payload = {
        "hand_id": "TMPOST",
        "decision_index": 0,
        "node": {
            "street": "flop",
            "hero_hole": ["Kd", "Qd"],
            "board": ["Kh", "7d", "2c"],
            "pot_before": 150,
            "to_call": 60,
            "eff_stack": 1000,
            "villain_range_key": "tight",
            "bb": 20,
        },
        "decision": {
            "street": "flop",
            "facing": "bet",
            "villain": "villain",
            "pot_before": 150,
            "to_call": 60,
            "hero_action": old_decision["hero_action"],
            "pot_odds": 0.285,
        },
    }

    result = solve_payload(payload, config)
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    saved_decision = saved["hand_evals"][0]["decisions"][0]

    assert result["saved"] is True
    assert saved_decision["suggestion"]["source"] == "solver"
    assert saved_decision["suggestion"]["best_action"] == "raise"
    assert saved_decision["solver_delta"]["status"] == "changed"
    assert saved["hand_evals"][0]["hand_tier"] == "mistake"
    assert saved["stats"]["mistakes"] == 1
    assert saved["stats"]["gto_accuracy"] == 0.0


def _fake_solver_adapter(tmp_path, actions: dict[str, float]):
    script = tmp_path / "fake_solver.py"
    script.write_text(
        "\n".join(
            [
                "import json",
                f"print(json.dumps({{'actions': {actions!r}}}))",
            ]
        ),
        encoding="utf-8",
    )
    if os.name == "nt":
        cmd = tmp_path / "fake_solver.cmd"
        cmd.write_text(f'@echo off\n"{sys.executable}" "{script}" %*\n', encoding="utf-8")
        return cmd
    script.write_text(f"#!{sys.executable}\n" + script.read_text(encoding="utf-8"), encoding="utf-8")
    script.chmod(0o755)
    return script


def test_equity_exact_river_without_treys_dependency():
    result = equity_vs_hand(
        parse_cards("As 5s"),
        parse_cards("Ah Ad"),
        parse_cards("2c 3d 4h Ks Qc"),
    )

    assert result.exact
    assert result.samples == 1
    assert result.win == pytest.approx(1.0)
