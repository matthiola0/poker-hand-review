# poker-hand-review

**English** | [繁體中文](docs/i18n/README.zh-TW.md) | [简体中文](docs/i18n/README.zh-CN.md)

<p align="center">
  <a href="https://github.com/matthiola0/poker-hand-review/actions/workflows/ci.yml"><img src="https://github.com/matthiola0/poker-hand-review/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="version 0.1.0">
  <img src="https://img.shields.io/badge/platform-Windows_/_PowerShell-0078D6?logo=windows&logoColor=white" alt="platform">
  <img src="https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black" alt="ruff">
  <img src="https://img.shields.io/badge/types-mypy_strict-2A6DB2" alt="mypy strict">
  <img src="https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white" alt="pytest">
  <img src="https://img.shields.io/badge/status-M1--M7_core_done-success" alt="status">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license MIT">
</p>

> Review your poker hands like a chess engine — hand by hand, decision by decision, with every move graded against GTO.

**poker-hand-review** reads hand histories exported from Natural8 / GGPoker tournaments and, from **your own (Hero) perspective**, grades each decision against GTO and colors it 🟢 fine / 🟡 inaccuracy / 🔴 mistake — with the recommended action and the reasoning behind it. After one session you know exactly which hands you misplayed, where, and how you should have played them.

<p align="center">
  <img src="docs/screenshots/hero.png" alt="poker-hand-review Web UI" width="720">
</p>

---

## Table of contents

- [What it does](#what-it-does)
- [Supported formats](#supported-formats)
- [Quick start](#quick-start)
  - [Install](#install)
  - [Run it](#run-it)
- [Commands and options](#commands-and-options)
- [Screenshot tour](#screenshot-tour)
- [How it works](#how-it-works)
- [Advanced: attach a real solver](#advanced-attach-a-real-solver)
- [Project layout](#project-layout)
- [Development](#development)
- [Contributing](#contributing)
- [Status and roadmap](#status-and-roadmap)
- [License](#license)

---

## What it does

poker-hand-review turns a folder of raw hand-history `.txt` files into a graded, navigable review — the way a chess engine annotates a game move by move.

- **Per-decision GTO grading.** Every Hero decision point is isolated and colored by how much EV it loses versus GTO, so mistakes stand out at a glance.
- **Statistics.** GTO accuracy, EV loss per 100 hands, VPIP / PFR / 3Bet / C-bet, and net result by position.
- **Opponent profiling.** Aggregates recurring opponents' tendencies, suggests exploits, and feeds the assumed ranges back into postflop equity.
- **Interactive Web UI.** Replay any hand street by street, filter by position / street / result, and drill into leaks and opponent profiles.
- **Pluggable postflop engine.** A fast equity/EV estimate by default; attach an external CFR solver for a true deep-solve on the hands that matter.

> [!NOTE]
> The perspective is always **Hero (you)**. The tool grades *your* decisions, not the table's. Set who Hero is with `--hero` (default `Hero`).

---

## Supported formats

| Source / type | Supported |
|---|---|
| Natural8 / GGPoker tournaments (MTT) | Yes |
| Other GG Network skins' tournaments | Usually — same hand-history format |
| Other poker sites (PokerStars, 888, partypoker…) | Not yet — different hand-history format |
| Cash games | Not yet — only tournament headers are parsed |

> [!IMPORTANT]
> Only **Natural8 / GGPoker tournament** hand histories are supported right now. Files from other sites or cash games will not parse.

The parser is deliberately tolerant: known tokens are parsed strictly, but any unrecognized line is recorded as a warning (`raw_unparsed`) instead of aborting the whole file.

---

## Quick start

### Install

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Requires Python 3.11 or newer. Commands below use PowerShell syntax (Windows).

### Run it

poker-hand-review can be driven entirely from the browser or from the command line. Both paths run the same engine and produce the same review; choose by how much you are analyzing at once — they are alternatives, not sequential steps.

| | Browser | Command line |
|---|---|---|
| Best for | reviewing a single file | batch-analyzing a folder |
| Input per run | one `.txt` | an entire folder of `.txt` |
| Terminal review | — | yes |
| Writes `report.json` | no | yes (reloadable later) |

**Browser** — analyze on upload, no separate `analyze` step:

```powershell
poker-hand-review web
```

Open the printed URL (default <http://127.0.0.1:8765/>), click **Load txt / json**, and select a `.txt`. The local server parses and grades it on the spot, then renders the review; nothing is written to disk. The backend dropdown (**Equity** / **Solver**) and solver-path field control how postflop spots are graded.

**Command line** — analyze a folder up front, then open the report:

```powershell
poker-hand-review analyze ".\data" --json report.json
poker-hand-review web --report report.json
```

`analyze` prints a colored, hand-by-hand review in the terminal and writes `report.json`; `web --report` opens that report in the browser. This path processes a whole folder in one run and leaves a reusable `report.json`.

> [!TIP]
> No hand histories of your own yet? A synthetic `data/sample.txt` ships with the repo:
> ```powershell
> poker-hand-review analyze data/sample.txt
> ```

Either way, once a report is open you can replay hands street by street, filter by position / street / result, and drill into leaks and opponent profiles.

> [!NOTE]
> A `.json` report can also be opened without the server — open `web/index.html` and load the file manually. Analyzing a `.txt` always requires the server, because parsing and grading run in Python.

---

## Commands and options

| Command | What it does |
|---|---|
| `poker-hand-review analyze <path>` | Hand-by-hand colored review + stats + leaks |
| `poker-hand-review hand <file> --id <hand-id>` | Deep, street-by-street review of a single hand |
| `poker-hand-review stats <path>` | Statistics only |
| `poker-hand-review profile <path>` | Opponent profiles (VPIP / PFR / 3Bet / tags) |
| `poker-hand-review web` | Start the local Web UI server |

`<path>` may be a single `.txt` file or a folder of hand-history files.

**`analyze` options**

| Option | What it does | Example |
|---|---|---|
| `--json <file>` | Also export a Web UI JSON report | `--json report.json` |
| `--hero <name>` | Set the Hero (you) name; default `Hero` | `--hero "YourName"` |
| `--min-tier <tier>` | Show only this tier or worse: `good` / `inaccuracy` / `mistake` | `--min-tier inaccuracy` |
| `--postflop <backend>` | Postflop engine: `equity` (default) or `solver` | `--postflop solver` |
| `--solver-path <path>` | External solver adapter path (with `--postflop solver`) | `--solver-path .\validation\texassolver.cmd` |
| `--no-color` | Disable ANSI colors in the terminal output | `--no-color` |

**`web` options**

| Option | What it does | Default |
|---|---|---|
| `--report <file>` | Preload a JSON report on startup | none |
| `--solver-path <path>` | Enable the in-UI solver backend | none (equity only) |
| `--host` / `--port` | Bind address | `127.0.0.1` / `8765` |

```powershell
# A few common invocations
poker-hand-review analyze ".\data" --hero "Hero"
poker-hand-review analyze ".\data" --min-tier inaccuracy
poker-hand-review hand ".\data\xxx.txt" --id TM6030071921 --postflop solver --solver-path C:\path\solver.exe
```

---

## Screenshot tour

A quick visual tour of the Web UI. The hero image at the top shows the full interface; click any shot to enlarge.

<table>
<tr>
<td width="50%" align="center"><b>1. Hand list</b><br><sub>Per hand: ID / cards / position / net, color-coded by worst mistake</sub><br><img src="docs/screenshots/hand-list.png" alt="Hand list" width="210"></td>
<td width="50%" align="center"><b>2. Hand replay</b><br><sub>Table + action timeline + decision card (GTO / solver advice)</sub><br><img src="docs/screenshots/hand-replay.png" alt="Hand replay" width="360"></td>
</tr>
<tr>
<td width="50%" align="center"><b>3. Leaks</b><br><sub>Recurring mistakes: count, cumulative EV loss, hands involved</sub><br><img src="docs/screenshots/leaks.png" alt="Leaks" width="270"></td>
<td width="50%" align="center"><b>4. Net by position</b><br><sub>Win / loss per position — which seat is leaking</sub><br><img src="docs/screenshots/positions.png" alt="Net by position" width="300"></td>
</tr>
</table>

---

## How it works

```
.txt ─▶ parse ─▶ Hero-view enrichment ─▶ per-decision GTO grading ─▶ report / Web UI
                 (position/stack/M)      ├ preflop: GTO range-chart lookup
                                         └ postflop: equity estimate (default) or CFR solver (optional)
```

- **Preflop** matches precomputed GTO range charts (per-position open / 3bet / call, plus short-stack push/fold) — true GTO, offline, and fast.
- **Postflop** computes equity versus the opponent's assumed range and applies EV heuristics to reliably flag obvious mistakes. Attach an external adapter to replace those heuristics with a real solver on the hands you care about.

The solver adapter is an external process that speaks a documented JSON contract — see [`docs/SOLVER_ADAPTER.md`](docs/SOLVER_ADAPTER.md).

> [!WARNING]
> Without a solver, `ev_loss_bb` is an engine **estimate** from chart / equity heuristics. Treat it as **severity guidance**, not exact solver EV. For precise numbers, re-run the hand with `--postflop solver` and a solver adapter.

---

## Advanced: attach a real solver

**You do not need a solver for normal use** — the default equity backend already flags obvious mistakes. Attach a solver only when you want a true CFR deep-solve on specific hands.

<details>
<summary><b>Set up TexasSolver (Windows, no build required)</b></summary>

<br>

poker-hand-review ships with an adapter for [TexasSolver](https://github.com/bupticybee/TexasSolver):

1. Download TexasSolver's `console_solver` (bundled in the Windows release — no build needed).
2. Point the adapter at it:
   ```powershell
   $env:TEXAS_SOLVER_CONSOLE = "C:\TexasSolver\console_solver.exe"
   ```
3. Run a hand through the bundled launcher:
   ```powershell
   poker-hand-review hand ".\data\xxx.txt" --id TM123 --postflop solver --solver-path .\validation\texassolver.cmd
   ```

To enable the solver inside the Web UI instead, start the server with `--solver-path`, or pick **Solver** and fill in the path field when loading a `.txt`.

</details>

<details>
<summary><b>Solver environment variables</b></summary>

<br>

| Variable | Purpose | Default |
|---|---|---|
| `TEXAS_SOLVER_CONSOLE` | Path to TexasSolver `console_solver(.exe)` | required |
| `PHR_SOLVER_PATH` / `TEXAS_SOLVER_PATH` | Default adapter path, used instead of `--solver-path` | unset |
| `PHR_SOLVER_THREADS` | CFR thread count | `8` |
| `PHR_SOLVER_ACCURACY` | Exploitability target (% of pot) | `0.5` |
| `PHR_SOLVER_MAX_ITER` | Maximum CFR iterations | `150` |
| `PHR_SOLVER_TIMEOUT` | Per-solve timeout (seconds) | `300` |

</details>

Full setup, tuning knobs, and the modeling assumptions are documented in [`docs/SOLVER_ADAPTER.md`](docs/SOLVER_ADAPTER.md).

---

## Project layout

```
poker-hand-review/
├── src/poker_hand_review/      core engine
│   ├── parser/         hand-history text parsing
│   ├── enrich/         Hero-view derivation (position, effective stack, decision nodes)
│   ├── gto/            preflop GTO range charts
│   ├── evaluate/       per-decision grading + pluggable postflop backends
│   ├── analysis/       equity / stats / leak aggregation
│   ├── profile/        opponent profiling
│   └── report/         CLI colored output + JSON export
├── web/                static Web UI (SPA) + local server endpoints
├── docs/               solver adapter contract + translations
├── data/               example hand histories
├── tools/              TexasSolver adapter and chart import scripts
└── tests/              tests
```

---

## Development

```powershell
pip install -e ".[dev]"   # install dev deps (pytest / ruff / mypy)
pytest                    # tests
ruff check src tests      # lint (line length 100)
mypy src                  # type check (strict)
```

Requires Python 3.11+.

---

## Contributing

Issues and PRs are welcome. A few notes to keep reviews smooth:

**Before you start**

- For larger changes, open an issue first to align on direction before implementing.

**While coding** (see [`CLAUDE.md`](CLAUDE.md))

- **Keep it simple** — the minimum code that solves the problem; no abstractions or configurability that were not asked for.
- **Make surgical changes** — touch only what you must; do not refactor or reformat adjacent code; match the existing style.
- **Respect the parser's tolerance rule** — known tokens are parsed strictly; unknown lines go to `raw_unparsed` as a warning without aborting.
- Comments may be in English or Chinese — match the surrounding style.

**Before you submit**

```powershell
pytest                 # tests must be green
ruff check src tests   # lint must pass
mypy src               # type check (strict) must pass
```

- When changing grading, parsing, or export logic, add a test that reproduces or verifies the change.
- Keep each PR focused on one thing, and write commit messages that explain *what* changed and *why*.

> [!NOTE]
> Edit `CLAUDE.md` only — `AGENTS.md` is auto-synced from it by a hook.

---

## Status and roadmap

The core path (M1–M7) is implemented: parsing, Hero-view enrichment, the equity backend, preflop grading, stats / leaks / profiling, JSON export, the Web UI, and the optional external solver adapter.

Not yet supported: poker sites other than the GG Network, and cash-game formats.

---

## License

MIT License — see [`LICENSE`](LICENSE).
