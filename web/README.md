# Web UI

M6 static SPA for poker-hand-review reports. It reads the JSON contract emitted by
`poker-hand-review analyze --json` and needs no backend or build step.

## Generate a report

```powershell
$env:PYTHONPATH='src'
python -m poker_hand_review.cli analyze data --json report.json
```

## Open the UI

Open `web/index.html` in a browser, then load `report.json`.

For a same-origin static server, the UI can also auto-load a report:

```text
http://localhost:8000/web/index.html?report=report.json
```

## Run solver from the UI

Directly opening `index.html` cannot execute a local solver process. Use the
local poker-hand-review server:

```powershell
poker-hand-review web --report report.json --solver-path C:\path\solver-adapter.exe
```

Postflop Hero decisions will show a `Run solver` button. The button calls the
local `/api/solve` endpoint, runs the configured adapter, and updates that
decision's source to `solver` in the browser.

Implemented views:
- Dashboard metrics and position net bars.
- Filterable hand list by tier, position, street, result, and search.
- Per-hand street replay with table seats, board cards, action timeline, and Hero decision cards.
- Leaks and opponent profile panels.

Note: `ev_loss_bb` is an engine estimate from charts/equity heuristics unless a solver backend is later enabled. Treat it as decision severity guidance, not exact solver EV.
