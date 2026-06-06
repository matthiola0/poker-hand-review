# data/

Put your Natural8 / GGPoker tournament hand-history `.txt` files in this folder, then run:

```powershell
n8-review analyze ".\data" --json report.json
```

## Privacy

Your real hands are **not** version-controlled — `.gitignore` ignores everything in `data/` except one example:

- **`sample.txt`** — a synthetic sample hand history (fake player IDs, fake tournament) that shows the input format and lets anyone try the tool right away.

Want to try it immediately, without preparing your own files?

```powershell
n8-review analyze ".\data\sample.txt"
```
