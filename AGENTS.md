# CLAUDE.md

Guidance for Claude Code when working in this repository.

Part A 是通用工作守則（取自 [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)，用來降低 LLM 常見的編碼失誤）。
Part B 是 **n8-review** 這個專案的具體脈絡。兩者一起讀。

**取捨：** 這些守則偏向謹慎而非速度。瑣碎任務請自行判斷。

---

# Part A — 工作守則

## 1. Think Before Coding（先想再寫）

**不要臆測。不要藏住困惑。把取捨攤開。**

實作前：
- 明確說出你的假設。不確定就問。
- 有多種解讀時，全部列出——不要默默選一個。
- 有更簡單的做法就講。該反駁時就反駁。
- 有不清楚的地方就停下來，指出哪裡不清楚，然後問。

## 2. Simplicity First（先求簡單）

**用最少的程式碼解決問題。不做沒被要求的事。**

- 不加沒被要求的功能。
- 不為一次性程式碼造抽象層。
- 不加沒被要求的「彈性」或「可設定性」。
- 不為不可能發生的情況寫錯誤處理。
- 如果寫了 200 行但其實 50 行就夠，重寫。

自問：「資深工程師會不會覺得這過度複雜？」會的話，就簡化。

## 3. Surgical Changes（外科手術式修改）

**只動你必須動的。只清理你自己製造的東西。**

- 不要「順手改善」相鄰的程式碼、註解或排版。
- 不要重構沒壞的東西。
- 配合既有風格，即使你會用別的寫法。
- 看到不相關的死碼，提一句——不要刪。
- 你的改動讓某些 import/變數/函式變成孤兒，才由你移除；既有死碼除非被要求，否則別動。

測試：每一行被改的程式碼，都要能直接對應到使用者的要求。

## 4. Goal-Driven Execution（目標導向執行）

**先定義成功標準，然後迴圈直到驗證通過。**

把任務轉成可驗證的目標：
- 「加驗證」→「先為非法輸入寫測試，再讓它通過」
- 「修 bug」→「先寫一個重現它的測試，再讓它通過」
- 「重構 X」→「確保重構前後測試都通過」

多步驟任務先列簡短計畫：
```
1. [步驟] → 驗證：[檢查]
2. [步驟] → 驗證：[檢查]
```

---

# Part B — 專案脈絡：n8-review

Natural8 / GGPoker 錦標賽手牌歷史分析與檢討工具。從 **Hero（使用者本人）** 視角，逐手、逐決策地以 GTO 為基準評分上色（綠=可接受、黃=不準、紅=失誤），像西洋棋引擎標出每一步好壞。

本檔與 [`README.md`](README.md) 是上手的主要入口；架構與模組職責見下方。

## 技術棧

- Python `>=3.11`，套件原始碼在 `src/`（setuptools `src` layout）。
- CLI 用 `typer` + `rich`；翻後 equity 用 `treys`。
- 工具鏈：`pytest`、`ruff`（line-length 100）、`mypy --strict`。
- 平台：Windows / PowerShell。命令請用 PowerShell 語法。

## 開發指令（PowerShell）

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

pytest                 # 測試
ruff check src tests   # lint
mypy src               # 嚴格型別檢查
```

## CLI 用法

```powershell
n8-review analyze ".\data" --json report.json     # 逐手檢討 + 統計，並輸出 Web UI JSON
n8-review stats ".\data"                           # 只看統計
n8-review hand ".\data\<檔名>.txt" --id TM...      # 單手詳細檢討
n8-review web --report report.json --solver-path C:\path\solver-adapter.exe  # 啟 local server
```

## 架構管線

```
.txt → Tokenizer → HandParser → [Hand] → Enrichment（Hero 視角：位置/有效籌碼/M/決策節點）
                                              │
        ┌─────────────────────┬──────────────┴───────────────┐
   Opponent Profiler     Decision Evaluator              Stats / Leaks
   對手傾向 ─assumed range→  逐決策 GTO 評分 ──DecisionEval[]──→  準確率/EV損失/VPIP...
                          ├ 翻前：GTO 範圍表（查表）
                          └ 翻後：可插拔後端
                             ├ Equity/EV（預設）
                             └ CFR solver（選用，外部 adapter）
                                              │
                              CLI（彩色） / JSON export / Web UI
```

## 模組地圖（`src/n8_review/`）

| 目錄 | 職責 |
|---|---|
| `models/` | 純資料模型：`hand`、`action`、`cards`、`enums`、`tournament`、`quality` |
| `parser/` | `tokenizer` + `hand_parser`（+ `patterns`）。未知行入 `raw_unparsed` 警告但**不中斷** |
| `enrich/` | `hero_context`：從 Hand 衍生位置、有效籌碼(BB)、M、Decision[] |
| `gto/` | 翻前 GTO：`preflop_charts`、`ranges`；範圍表 JSON 在 `gto/charts/` |
| `evaluate/` | `evaluator` 逐決策評分；`postflop/` 可插拔後端（`equity_backend` 預設、`solver_backend` 選用）；`quality` 門檻 |
| `analysis/` | `equity`（treys MC）、`stats`、`leaks` |
| `profile/` | `opponent` 對手群像與 assumed range |
| `report/` | `cli_report`（rich 彩色）、`json_export`（Web UI 契約） |
| `web_server.py` | 提供 `web/` SPA + `/api/solve` 端點 |
| `config.py` | 全域組態：Hero、MC 樣本數、翻後後端、品質門檻 |

`web/` 是讀取 JSON report 的靜態 SPA。`tools/` 含 TexasSolver adapter 與圖表匯入腳本。

## 專案特定須知

- **Solver adapter 是外部程序，透過 JSON 契約溝通**——契約見 [`docs/SOLVER_ADAPTER.md`](docs/SOLVER_ADAPTER.md)。路徑可用 `--solver-path` 或環境變數 `N8_REVIEW_SOLVER_PATH` / `TEXAS_SOLVER_PATH`。
- **`ev_loss_bb` 在未使用 solver 時是引擎估計值**，當作嚴重度指引、不是精確 solver EV。改動評分邏輯時別把估計值講成精確值。
- **解析器的容忍原則不可破壞**：已知 token 嚴格解析，未知行進 `raw_unparsed`。新增格式支援時，沿用此策略，別讓未知行造成中斷。
- 註解**中英文皆可**（既有程式碼多為繁中）；配合周圍既有風格即可（見守則 3）。
- 改動評分、解析或匯出邏輯時，對照 `tests/`（`test_hand_parser`、`test_equity`、`test_sdd_pipeline`、`test_texassolver_adapter`）並讓測試通過（見守則 4）。
- `report.json` / `report.*.json` 與 `artifacts-*.png` 是產生物，不是手寫來源。

<!-- AGENTS.md 由 .claude/settings.json 的 PostToolUse hook 自動從本檔同步，請只編輯 CLAUDE.md。 -->

