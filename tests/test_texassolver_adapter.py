"""Tests for the TexasSolver adapter (tools/texassolver_adapter.py).

No solver binary required: these lock the input-file builder and the dumped-tree
parser against the documented TexasSolver console format.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ADAPTER_PATH = Path(__file__).resolve().parents[1] / "tools" / "texassolver_adapter.py"
_spec = importlib.util.spec_from_file_location("texassolver_adapter", _ADAPTER_PATH)
assert _spec and _spec.loader
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)


def _node(**overrides):
    node = {
        "contract": "poker_hand_review.solver_node.v1",
        "street": "flop",
        "hero_hole": ["Ah", "Kh"],
        "board": ["As", "7d", "2c"],
        "pot_before": 130,
        "to_call": 30,
        "eff_stack": 1000,
        "villain_range_key": "tight",
        "bb": 20,
        "candidate_actions": ["fold", "call", "raise"],
    }
    node.update(overrides)
    return node


def test_input_builder_facing_bet():
    text, hero = adapter._build_input(_node(), dump_path="out.json")
    assert hero == "AhKh"
    # set_pot = pot_before - to_call = 100; villain bet % = 30 / 100 * 100 = 30
    assert "set_pot 100" in text
    assert "set_board As,7d,2c" in text
    # TexasSolver ranges use hand classes (AhKh -> AKs), not raw 4-char combos
    assert "set_range_ip AKs" in text
    assert "set_bet_sizes oop,flop,bet,30" in text
    assert "dump_result out.json" in text


def test_range_class_maps_combos_to_solver_tokens():
    assert adapter._range_class("6s6d") == "66"
    assert adapter._range_class("AhKh") == "AKs"
    assert adapter._range_class("AhKs") == "AKo"


def test_bet_child_closest_picks_matching_size():
    # root with a normal bet and an all-in; to_call should select the normal bet
    root = {
        "childrens": {
            "BET 1440.000000": {"tag": "normal"},
            "BET 8683.000000": {"tag": "allin"},
            "CHECK": {"tag": "check"},
        }
    }
    assert adapter._bet_child_closest(root, 1440)["tag"] == "normal"
    assert adapter._bet_child_closest(root, 9000)["tag"] == "allin"


def test_match_combo_is_card_order_independent():
    table = {"6d6s": [0.1, 0.9]}
    assert adapter._match_combo(table, "6s6d") == [0.1, 0.9]


def test_expand_range_removes_plus_notation():
    # TexasSolver v0.2.0 rejects '+'; the adapter must enumerate.
    assert adapter._expand_range("22+").startswith("22,33,44")
    assert adapter._expand_range("22+").endswith("KK,AA")
    assert adapter._expand_range("A2s+") == (
        "A2s,A3s,A4s,A5s,A6s,A7s,A8s,A9s,ATs,AJs,AQs,AKs"
    )
    assert adapter._expand_range("ATo+") == "ATo,AJo,AQo,AKo"
    assert adapter._expand_range("76s,KQo") == "76s,KQo"  # no '+' passes through
    # every preset villain range must be free of '+' after expansion
    for key in adapter.VILLAIN_RANGES:
        assert "+" not in adapter._expand_range(adapter.VILLAIN_RANGES[key])


def test_input_builder_no_bet_turn():
    text, _ = adapter._build_input(
        _node(street="turn", board=["As", "7d", "2c", "Th"], to_call=0, pot_before=200),
        dump_path="out.json",
    )
    assert "set_pot 200" in text
    assert "set_bet_sizes oop,turn,bet,50" in text  # default size when not facing a bet


# --- parser: TexasSolver Form A (nested {actions, strategy:{combo:[freqs]}}) ---

_BET_DUMP = {
    "actions": ["CHECK", "BET 30"],
    "childrens": {
        "CHECK": {"actions": ["CHECK"], "childrens": {}},
        "BET 30": {
            "strategy": {
                "actions": ["FOLD", "CALL", "RAISE 60", "ALLIN"],
                "strategy": {"AhKh": [0.10, 0.60, 0.20, 0.10]},
            },
            "childrens": {},
        },
    },
}

_CHECK_DUMP = {
    "actions": ["CHECK", "BET 100"],
    "childrens": {
        "CHECK": {
            "strategy": {
                "actions": ["CHECK", "BET 100", "ALLIN"],
                "strategy": {"QsQd": [0.30, 0.55, 0.15]},
            },
            "childrens": {},
        },
        "BET 100": {"actions": ["FOLD", "CALL"], "childrens": {}},
    },
}


def test_parse_facing_bet_aggregates_raise_and_allin():
    out = adapter._strategy_from_dump(_BET_DUMP, _node())
    assert out["actions"]["fold"] == pytest.approx(0.10)
    assert out["actions"]["call"] == pytest.approx(0.60)
    assert out["actions"]["raise"] == pytest.approx(0.30)  # raise 0.20 + allin 0.10
    assert out["best_action"] == "call"


def test_parse_no_bet_aggregates_bet_and_allin():
    node = _node(street="turn", board=["As", "7d", "2c", "Th"], to_call=0,
                 hero_hole=["Qs", "Qd"], villain_range_key="balanced")
    out = adapter._strategy_from_dump(_CHECK_DUMP, node)
    assert out["actions"]["check"] == pytest.approx(0.30)
    assert out["actions"]["bet"] == pytest.approx(0.70)  # bet 0.55 + allin 0.15
    assert out["best_action"] == "bet"


def test_parse_missing_combo_fails_clearly():
    with pytest.raises(SystemExit):
        adapter._strategy_from_dump(_BET_DUMP, _node(hero_hole=["2c", "2d"]))


def test_label_kind_normalizes_solver_labels():
    assert adapter._label_kind("BET 50") == "BET"
    assert adapter._label_kind("All-In") == "ALLIN"
    assert adapter._label_kind("Raise 60") == "RAISE"
    assert adapter._label_kind("CHECK") == "CHECK"


def test_wrong_contract_rejected(tmp_path):
    bad = tmp_path / "node.json"
    bad.write_text('{"contract": "nope"}', encoding="utf-8")
    with pytest.raises(SystemExit):
        adapter._load_node(str(bad))
