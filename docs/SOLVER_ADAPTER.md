# Solver Adapter Contract

M7 enables the optional `solver` postflop backend through an external adapter.
The core engine does not call TexasSolver directly. Instead, it writes a compact
JSON input file and runs:

```powershell
solver-adapter.exe input.json
```

The adapter prints strategy JSON to stdout.

## Input

```json
{
  "contract": "poker_hand_review.solver_node.v1",
  "street": "flop",
  "hero_hole": ["Ah", "Kh"],
  "board": ["As", "7d", "2c"],
  "pot_before": 100,
  "to_call": 40,
  "eff_stack": 1000,
  "villain_range_key": "tight",
  "bb": 20,
  "candidate_actions": ["fold", "call", "raise"]
}
```

When `to_call` is `0`, `candidate_actions` is `["check", "bet"]`.

## Output

Preferred:

```json
{
  "actions": {
    "call": 0.72,
    "fold": 0.28
  },
  "best_action": "call"
}
```

Also accepted:

```json
{
  "strategy": [
    {"action": "call", "frequency": 0.72},
    {"action": "fold", "frequency": 0.28}
  ]
}
```

If `best_action` is omitted, poker-hand-review uses the highest-frequency action.

## CLI

```powershell
$env:PYTHONPATH='src'
python -m poker_hand_review.cli hand data\hands.txt --id TM123 --postflop solver --solver-path C:\path\solver-adapter.exe
```

`--solver-path` can also be provided through `PHR_SOLVER_PATH` or
`TEXAS_SOLVER_PATH`.

---

## TexasSolver adapter (real solver)

`tools/texassolver_adapter.py` implements this contract on top of
[TexasSolver](https://github.com/bupticybee/TexasSolver)'s `console_solver`. It
translates a node into a TexasSolver command file, runs the solver, parses the
dumped game tree, and prints the strategy JSON.

> Verified end-to-end against the prebuilt **TexasSolver v0.2.0 Windows**
> `console_solver.exe` (its Windows release zip bundles the console binary +
> `resources/`, so no build is needed). The dump is Form A:
> `{actions, childrens, strategy:{actions, strategy:{combo:[freqs]}}, node_type, player}`.

### Setup

1. Build / download `console_solver(.exe)` from TexasSolver. Note its path.
2. poker-hand-review invokes the solver path as `<solver-path> <input.json>` with no extra
   args, so point it at a 2-line launcher that calls the adapter:

   **Windows `texassolver.cmd`:**
   ```bat
   @echo off
   python "%~dp0..\tools\texassolver_adapter.py" %*
   ```
   **macOS/Linux `texassolver.sh`:**
   ```bash
   #!/usr/bin/env bash
   exec python3 "$(dirname "$0")/../tools/texassolver_adapter.py" "$@"
   ```
3. Tell the adapter where the solver binary is:
   ```powershell
   $env:TEXAS_SOLVER_CONSOLE = "C:\TexasSolver\console_solver.exe"
   ```
4. Run poker-hand-review pointed at the launcher:
   ```powershell
   poker-hand-review hand .\data\hands.txt --id TM123 --postflop solver --solver-path .\texassolver.cmd
   ```

Tuning via env: `PHR_SOLVER_THREADS` (8), `PHR_SOLVER_ACCURACY` (0.5, % pot),
`PHR_SOLVER_MAX_ITER` (150), `PHR_SOLVER_TIMEOUT` (300s).

### Validate without solving a full tree

```powershell
# 1. See the exact TexasSolver input the adapter would feed (no binary needed):
python tools\texassolver_adapter.py --dry-run node.json

# 2. Run that input through your TexasSolver once, then check the parser reads it:
python tools\texassolver_adapter.py --parse output_result.json node.json
```
`--parse` prints the poker-hand-review strategy. If your TexasSolver build dumps a different
JSON shape, the error message lists the keys it found so the parser is a 1-line fix.

### Modeling assumptions (read this)

The v1 node contract carries Hero's hand, board, pot/to_call/stack, and a coarse
villain range key, but **not** who is in position. The adapter therefore models:

- **Hero in position**, solved as his hand *class* (`6s6d` -> `66`, `AhKh` -> `AKs`)
  because TexasSolver ranges reject raw 4-char combos; the exact combo's strategy
  line is then extracted from the dump. **Villain OOP** with a preset range from
  `villain_range_key` (`tight` / `balanced` / `wide_passive` / `wide_aggressive`).
- A **single villain bet size ≈ `to_call`** so the "facing a bet" node is unambiguous.
- `to_call == 0` → read Hero's node after villain checks; `to_call > 0` → after villain bets.
- TexasSolver's `RAISE`/`ALLIN` frequencies are folded into `raise`; `BET`/`ALLIN` into `bet`.
- Villain range `+` notation (`22+`, `A2s+`) is expanded to explicit hands, since
  TexasSolver v0.2.0 rejects `+`. When facing multiple villain bet/all-in lines, the
  child whose size is closest to `to_call` is used.

This is a genuine GTO solve of Hero's hand vs the assumed range — a strong second
opinion — but an approximation of the true table spot (real positions, multiway,
exact sizing). For position-exact solving, extend the node contract to carry
`hero_in_position` and branch the OOP/IP ranges accordingly (contract v2).
