# CLAUDE.md

Guidance for Claude Code when working in this repository.

Part A is the general working guidelines (from [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills), to reduce common LLM coding mistakes).
Part B is the specific context of the **poker-hand-review** project. Read both.

**Tradeoff:** these guidelines bias toward caution over speed. Use judgment for trivial tasks.

---

# Part A — Working guidelines

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

---

# Part B — Project context: poker-hand-review

A GTO hand-history review tool for Natural8 / GGPoker tournaments. From the **Hero (you, the user)** perspective, it grades and colors every decision against GTO (green = fine, yellow = inaccuracy, red = mistake), like a chess engine marking each move.

This file and [`README.md`](README.md) are the main entry points; architecture and module responsibilities are below.

## Tech stack

- Python `>=3.11`; package source under `src/` (setuptools `src` layout).
- CLI uses `typer` + `rich`; postflop equity uses `treys`.
- Tooling: `pytest`, `ruff` (line-length 100), `mypy --strict`.
- Platform: Windows / PowerShell. Use PowerShell syntax for commands.

## Dev commands (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

pytest                 # tests
ruff check src tests   # lint
mypy src               # strict type check
```

## CLI usage

```powershell
poker-hand-review analyze ".\data" --json report.json     # per-hand review + stats, emit Web UI JSON
poker-hand-review stats ".\data"                           # stats only
poker-hand-review hand ".\data\<file>.txt" --id TM...      # single-hand deep review
poker-hand-review web --report report.json --solver-path C:\path\solver-adapter.exe  # start local server
```

## Architecture pipeline

```
.txt → Tokenizer → HandParser → [Hand] → Enrichment (Hero view: position/effective stack/M/decision nodes)
                                              │
        ┌─────────────────────┬──────────────┴───────────────┐
   Opponent Profiler     Decision Evaluator              Stats / Leaks
   tendencies ─assumed range→  per-decision GTO grading ──DecisionEval[]──→  accuracy/EV loss/VPIP...
                          ├ preflop: GTO range charts (lookup)
                          └ postflop: pluggable backend
                             ├ Equity/EV (default)
                             └ CFR solver (optional, external adapter)
                                              │
                              CLI (colored) / JSON export / Web UI
```

## Module map (`src/poker_hand_review/`)

| Directory | Responsibility |
|---|---|
| `models/` | Pure data models: `hand`, `action`, `cards`, `enums`, `tournament`, `quality` |
| `parser/` | `tokenizer` + `hand_parser` (+ `patterns`). Unknown lines go to `raw_unparsed` as a warning but **never abort** |
| `enrich/` | `hero_context`: derives position, effective stack (BB), M, and Decision[] from a Hand |
| `gto/` | Preflop GTO: `preflop_charts`, `ranges`; range-chart JSON in `gto/charts/` |
| `evaluate/` | `evaluator` per-decision grading; `postflop/` pluggable backends (`equity_backend` default, `solver_backend` optional); `quality` thresholds |
| `analysis/` | `equity` (treys MC), `stats`, `leaks` |
| `profile/` | `opponent` profiling and assumed range |
| `report/` | `cli_report` (rich colored), `json_export` (Web UI contract) |
| `web_server.py` | Serves the `web/` SPA + `/api/solve` endpoint |
| `config.py` | Global config: Hero, MC sample count, postflop backend, quality thresholds |

`web/` is a static SPA that reads a JSON report. `tools/` holds the TexasSolver adapter and chart import scripts.

## Project-specific notes

- **The solver adapter is an external process that communicates via a JSON contract** — see [`docs/SOLVER_ADAPTER.md`](docs/SOLVER_ADAPTER.md). Provide the path via `--solver-path` or the env vars `PHR_SOLVER_PATH` / `TEXAS_SOLVER_PATH`.
- **`ev_loss_bb` is an engine estimate when no solver is used** — treat it as severity guidance, not exact solver EV. When changing grading logic, don't present the estimate as exact.
- **Don't break the parser's tolerance rule**: known tokens are parsed strictly; unknown lines go to `raw_unparsed`. When adding format support, keep this strategy — never let an unknown line abort parsing.
- Comments may be **English or Chinese** (existing code is mostly Traditional Chinese); just match the surrounding style (see guideline 3).
- When changing grading, parsing, or export logic, check against `tests/` (`test_hand_parser`, `test_equity`, `test_sdd_pipeline`, `test_texassolver_adapter`) and keep them green (see guideline 4).
- `report.json` / `report.*.json` are generated outputs, not hand-written sources.

<!-- AGENTS.md is auto-synced from this file by the PostToolUse hook in .claude/settings.json — edit CLAUDE.md only. -->
