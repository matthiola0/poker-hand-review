#!/usr/bin/env python3
"""TexasSolver adapter for poker-hand-review's optional `solver` postflop backend.

Implements the contract in docs/SOLVER_ADAPTER.md:

    python texassolver_adapter.py <node.json>      # -> strategy JSON on stdout

Pipeline: read the poker-hand-review node -> emit a TexasSolver console input file ->
run console_solver -> parse the dumped game-tree JSON -> print poker-hand-review
strategy JSON to stdout.

The poker-hand-review core stays solver-agnostic; this file is the only place that knows
TexasSolver's command syntax and output shape. Point poker-hand-review at it with:

    poker-hand-review hand <hh> --id <id> --postflop solver \\
        --solver-path "python" ... (see docs: use a small wrapper, below)

Because the core invokes `<solver-path> <input.json>` with no extra args, the
simplest setup is a 2-line launcher that calls this script. See
docs/SOLVER_ADAPTER.md "TexasSolver setup".

--------------------------------------------------------------------------------
Modeling assumptions (documented, honest approximations)
--------------------------------------------------------------------------------
The v1 node contract carries Hero's exact hand, the board, pot/to_call/stack, and
a coarse villain range key -- but NOT who is in position. So this adapter models:

  * Hero IN POSITION (IP) with his exact 2 cards as a 1-combo range.
  * Villain OUT OF POSITION (OOP) with a preset range chosen by villain_range_key.
  * A single villain bet size ~= to_call (so the "facing a bet" node is unambiguous).
  * to_call == 0  -> read Hero's node after villain checks (check/bet decision).
    to_call  > 0  -> read Hero's node after villain bets   (fold/call/raise decision).

This yields a genuine GTO solve of Hero's hand vs the assumed range, which is the
point of the solver backend, but it is an approximation of the real table spot
(true positions, multiway, exact sizing). Treat it as a strong second opinion.

Config via environment variables:
  TEXAS_SOLVER_CONSOLE  path to console_solver(.exe)   (required to actually solve)
  PHR_SOLVER_THREADS     thread count           (default 8)
  PHR_SOLVER_ACCURACY    exploitability target  (default 0.5, % of pot)
  PHR_SOLVER_MAX_ITER    max CFR iterations     (default 150)

CLI helper modes (do not need the binary):
  --dry-run <node.json>              print the generated TexasSolver input, exit
  --parse <solver_output.json> <node.json>
                                     parse an existing dump and print strategy
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT = "poker_hand_review.solver_node.v1"

# villain_range_key -> a reasonable postflop continuing range (TexasSolver notation).
# Coarse on purpose; these mirror the equity backend's range buckets.
VILLAIN_RANGES: dict[str, str] = {
    "tight": "AA,KK,QQ,JJ,TT,AKs,AKo,AQs,AJs,KQs",
    "balanced": (
        "AA,KK,QQ,JJ,TT,99,88,77,66,55,AKs,AKo,AQs,AQo,AJs,ATs,KQs,KJs,KTs,"
        "QJs,QTs,JTs,T9s,98s,87s,76s,65s,54s"
    ),
    "wide_passive": (
        "22+,A2s+,A7o+,K6s+,K9o+,Q8s+,Q9o+,J8s+,J9o+,T8s+,97s+,86s+,75s+,"
        "64s+,54s,ATo,KTo,QTo,JTo"
    ),
    "wide_aggressive": (
        "22+,A2s+,A5o+,K7s+,KTo+,Q8s+,QTo+,J8s+,JTo,T8s+,97s+,86s+,76s,65s,"
        "54s,43s"
    ),
}
DEFAULT_RANGE_KEY = "balanced"

# Aggregate TexasSolver action labels into poker-hand-review's vocabulary.
#   facing a bet (to_call > 0): fold / call / raise
#   no bet      (to_call == 0): check / bet
AGG_FACING_BET = {"FOLD": "fold", "CALL": "call", "RAISE": "raise", "ALLIN": "raise"}
AGG_NO_BET = {"CHECK": "check", "BET": "raise_as_bet", "ALLIN": "raise_as_bet"}


def main(argv: list[str]) -> int:
    if not argv:
        _fail("usage: texassolver_adapter.py <node.json> | --dry-run <node.json> | "
              "--parse <out.json> <node.json>")

    if argv[0] == "--dry-run":
        node = _load_node(argv[1])
        sys.stdout.write(_build_input(node, dump_path="output_result.json")[0])
        return 0

    if argv[0] == "--parse":
        dump = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        node = _load_node(argv[2])
        _emit(_strategy_from_dump(dump, node))
        return 0

    node = _load_node(argv[0])
    dump = _run_solver(node)
    _emit(_strategy_from_dump(dump, node))
    return 0


# --- input building -------------------------------------------------------

def _load_node(path: str) -> dict[str, Any]:
    node = json.loads(Path(path).read_text(encoding="utf-8"))
    if node.get("contract") != CONTRACT:
        _fail(f"unexpected contract: {node.get('contract')!r} (want {CONTRACT})")
    return node


def _hero_combo(node: dict[str, Any]) -> str:
    hole = node.get("hero_hole") or []
    if len(hole) != 2:
        _fail("node.hero_hole must have 2 cards")
    return f"{hole[0]}{hole[1]}"


def _build_input(node: dict[str, Any], dump_path: str) -> tuple[str, str]:
    """Return (command_file_text, hero_combo). Hero is IP, villain OOP."""
    facing_bet = int(node.get("to_call", 0)) > 0
    pot_total = int(node["pot_before"])
    to_call = int(node.get("to_call", 0))
    eff_stack = int(node["eff_stack"])
    board = ",".join(node.get("board") or [])
    hero = _hero_combo(node)
    # TexasSolver ranges accept hand classes (66 / AKs / AKo), NOT raw 4-char
    # combos. Solve the class; the exact combo's line is extracted from the dump.
    hero_class = _range_class(hero)
    villain = _expand_range(
        VILLAIN_RANGES.get(node.get("villain_range_key") or DEFAULT_RANGE_KEY,
                           VILLAIN_RANGES[DEFAULT_RANGE_KEY])
    )

    # set_pot = pot at the start of this street's action (before any bet this round).
    # When facing a bet, villain's bet (to_call) is added on top of pot_total - to_call.
    if facing_bet:
        start_pot = max(1, pot_total - to_call)
        pre_bet_pot = start_pot
        villain_bet_pct = _clamp_pct(round(to_call / pre_bet_pot * 100))
        oop_bet_line = f"set_bet_sizes oop,{_street(node)},bet,{villain_bet_pct}"
    else:
        start_pot = pot_total
        oop_bet_line = f"set_bet_sizes oop,{_street(node)},bet,50"

    threads = os.getenv("PHR_SOLVER_THREADS", "8")
    accuracy = os.getenv("PHR_SOLVER_ACCURACY", "0.5")
    max_iter = os.getenv("PHR_SOLVER_MAX_ITER", "150")
    street = _street(node)

    lines = [
        f"set_pot {start_pot}",
        f"set_effective_stack {eff_stack}",
        f"set_board {board}",
        f"set_range_ip {hero_class}",
        f"set_range_oop {villain}",
        oop_bet_line,
        f"set_bet_sizes oop,{street},allin",
        f"set_bet_sizes ip,{street},bet,50",
        f"set_bet_sizes ip,{street},raise,60",
        f"set_bet_sizes ip,{street},allin",
        "set_allin_threshold 0.67",
        "build_tree",
        f"set_thread_num {threads}",
        f"set_accuracy {accuracy}",
        f"set_max_iteration {max_iter}",
        "set_print_interval 50",
        "set_use_isomorphism 1",
        "start_solve",
        "set_dump_rounds 2",
        f"dump_result {dump_path}",
    ]
    return "\n".join(lines) + "\n", hero


_RANKS_ASC = "23456789TJQKA"


def _expand_range(range_str: str) -> str:
    """Expand '+' notation into explicit hands (TexasSolver v0.2.0 rejects '+').

    '22+' -> 22,33,...,AA ; 'A2s+' -> A2s,...,AKs ; 'ATo+' -> ATo,AJo,AQo,AKo.
    Tokens without '+' pass through unchanged.
    """
    out: list[str] = []
    for token in range_str.split(","):
        token = token.strip()
        if not token.endswith("+"):
            out.append(token)
            continue
        body = token[:-1]
        if len(body) == 2 and body[0] == body[1]:  # pair, e.g. 22+
            start = _RANKS_ASC.index(body[0])
            out.extend(r + r for r in _RANKS_ASC[start:])
        elif len(body) == 3:                        # XYs+ / XYo+
            hi, lo, suit = body[0], body[1], body[2]
            hi_i, lo_i = _RANKS_ASC.index(hi), _RANKS_ASC.index(lo)
            out.extend(f"{hi}{_RANKS_ASC[i]}{suit}" for i in range(lo_i, hi_i))
        else:
            out.append(body)
    unique: list[str] = []
    seen: set[str] = set()
    for token in out:
        if token in seen:
            continue
        unique.append(token)
        seen.add(token)
    return ",".join(unique)


_RANK_ORDER = "AKQJT98765432"


def _range_class(combo: str) -> str:
    """'6s6d' -> '66', 'AhKh' -> 'AKs', 'AhKs' -> 'AKo' (TexasSolver range token)."""
    r1, s1, r2, s2 = combo[0], combo[1], combo[2], combo[3]
    if r1 == r2:
        return r1 + r2
    hi, lo = sorted((r1, r2), key=_RANK_ORDER.index)
    return f"{hi}{lo}{'s' if s1 == s2 else 'o'}"


def _street(node: dict[str, Any]) -> str:
    n = len(node.get("board") or [])
    return {3: "flop", 4: "turn", 5: "river"}.get(n, node.get("street", "flop"))


def _clamp_pct(pct: int) -> int:
    return max(10, min(300, pct))


# --- running the solver ----------------------------------------------------

def _run_solver(node: dict[str, Any]) -> dict[str, Any]:
    console = os.getenv("TEXAS_SOLVER_CONSOLE")
    if not console:
        _fail("set TEXAS_SOLVER_CONSOLE to your console_solver(.exe) path")
    console_path = Path(console)
    if not console_path.exists():
        _fail(f"console_solver not found: {console_path}")

    workdir = Path(tempfile.mkdtemp(prefix="n8solver_"))
    dump_path = workdir / "output_result.json"
    cmd_text, _ = _build_input(node, dump_path=str(dump_path).replace("\\", "/"))
    cmd_file = workdir / "input.txt"
    cmd_file.write_text(cmd_text, encoding="utf-8")

    try:
        proc = subprocess.run(
            [str(console_path), "-i", str(cmd_file)],
            cwd=str(console_path.parent),  # TexasSolver loads ./resources relative to binary
            capture_output=True,
            encoding="utf-8",
            timeout=int(os.getenv("PHR_SOLVER_TIMEOUT", "300")),
            check=False,
        )
    except subprocess.TimeoutExpired:
        _fail("TexasSolver timed out")

    if proc.returncode != 0:
        _fail(f"TexasSolver exit={proc.returncode}: {(proc.stderr or '').strip()[:300]}")
    if not dump_path.exists():
        _fail(f"TexasSolver produced no dump at {dump_path}. stdout tail: "
              f"{(proc.stdout or '')[-300:]}")
    return json.loads(dump_path.read_text(encoding="utf-8"))


# --- parsing the dumped tree ----------------------------------------------

def _strategy_from_dump(dump: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """Navigate root (villain OOP) -> Hero's node, read Hero's combo strategy."""
    facing_bet = int(node.get("to_call", 0)) > 0
    hero = _hero_combo(node)

    if facing_bet:
        # Villain may have several bet/all-in children; pick the one whose amount
        # is closest to the actual to_call.
        hero_node = _bet_child_closest(dump, int(node.get("to_call", 0)))
    else:
        hero_node = _child_by_prefix(dump, "CHECK")
    if hero_node is None:
        action = "BET" if facing_bet else "CHECK"
        _fail(f"could not find villain '{action}' child. "
              f"root keys: {sorted(dump.keys())}; children: "
              f"{[lbl for lbl, _ in _node_children(dump)]}")

    actions, freqs = _hero_strategy(hero_node, hero)
    agg = AGG_FACING_BET if facing_bet else AGG_NO_BET
    out: dict[str, float] = {}
    for label, freq in zip(actions, freqs):
        bucket = agg.get(_label_kind(label))
        if bucket is None:
            continue
        bucket = "bet" if bucket == "raise_as_bet" else bucket
        out[bucket] = out.get(bucket, 0.0) + float(freq)
    if not out:
        _fail(f"no Hero strategy parsed at node (actions={actions})")

    best = max(out, key=lambda k: out[k])
    return {"actions": out, "best_action": best, "source_detail": "texassolver"}


def _node_actions(node: dict[str, Any]) -> list[str]:
    return node.get("actions") or node.get("valid_actions") or []


def _node_children(node: dict[str, Any]) -> list[tuple[str, Any]]:
    children = node.get("childrens") or node.get("children") or {}
    if isinstance(children, dict):
        return list(children.items())
    if isinstance(children, list):
        return list(zip(_node_actions(node), children))
    return []


def _child_by_prefix(node: dict[str, Any], prefix: str) -> Any | None:
    for label, child in _node_children(node):
        if _label_kind(label) == prefix.upper():
            return child
    return None


def _bet_child_closest(node: dict[str, Any], to_call: int) -> Any | None:
    """Among BET/ALLIN children, return the one whose amount is closest to to_call."""
    best_child = None
    best_gap = None
    for label, child in _node_children(node):
        if _label_kind(label) not in {"BET", "ALLIN", "RAISE"}:
            continue
        gap = abs(_label_amount(label) - to_call)
        if best_gap is None or gap < best_gap:
            best_gap, best_child = gap, child
    return best_child


def _label_amount(label: str) -> float:
    for tok in str(label).replace(",", " ").split():
        try:
            return float(tok)
        except ValueError:
            continue
    return 0.0


def _label_kind(label: str) -> str:
    """'BET 50' -> 'BET', 'All-In' -> 'ALLIN', 'Raise 60' -> 'RAISE'."""
    token = str(label).strip().upper().replace("-", "").replace(" ", "")
    for kind in ("CHECK", "CALL", "FOLD", "ALLIN", "BET", "RAISE"):
        if token.startswith(kind):
            return kind
    return token


def _hero_strategy(node: dict[str, Any], hero: str) -> tuple[list[str], list[float]]:
    strat = node.get("strategy")
    # Form A (C++/Java console): {"actions": [...], "strategy": {combo: [freqs]}}
    if isinstance(strat, dict) and "strategy" in strat and "actions" in strat:
        actions = strat["actions"]
        table = strat["strategy"]
    else:
        actions = _node_actions(node)
        table = strat
    if not isinstance(table, dict):
        _fail(f"unrecognized strategy shape at Hero node: keys={sorted(node.keys())}")

    freqs = _match_combo(table, hero)
    if freqs is None:
        _fail(f"Hero combo {hero} not in solved strategy "
              f"(have {list(table)[:6]}{'...' if len(table) > 6 else ''})")
    if len(freqs) != len(actions):
        _fail(f"strategy length {len(freqs)} != actions {len(actions)}")
    return list(actions), [float(x) for x in freqs]


def _match_combo(table: dict[str, Any], hero: str) -> Any | None:
    """Find Hero's combo in the strategy map regardless of card order.

    TexasSolver may key a combo as '6s6d' or '6d6s'; match on the unordered
    pair of 2-char cards.
    """
    want = frozenset((hero[:2], hero[2:]))
    for key, freqs in table.items():
        k = str(key)
        if len(k) == 4 and frozenset((k[:2], k[2:])) == want:
            return freqs
    return None


# --- output ---------------------------------------------------------------

def _emit(strategy: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(strategy, ensure_ascii=False))
    sys.stdout.write("\n")


def _fail(message: str) -> "None":
    sys.stderr.write(f"texassolver_adapter: {message}\n")
    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
