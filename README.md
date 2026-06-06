# n8-review

[English](README.en.md) | **繁體中文**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="version 0.1.0">
  <img src="https://img.shields.io/badge/platform-Windows_/_PowerShell-0078D6?logo=windows&logoColor=white" alt="platform">
  <img src="https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black" alt="ruff">
  <img src="https://img.shields.io/badge/types-mypy_strict-2A6DB2" alt="mypy strict">
  <img src="https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white" alt="pytest">
  <img src="https://img.shields.io/badge/status-M1--M7_core_done-success" alt="status">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license MIT">
</p>

> 像西洋棋引擎一樣檢討你的撲克手牌 —— 逐手、逐決策，用 GTO 為你的每一步上色。

**n8-review** 讀取 Natural8 / GGPoker 錦標賽匯出的手牌歷史，從 **你本人（Hero）** 的視角，把每個決策標成 🟢 可接受 / 🟡 不準 / 🔴 失誤，並附上 GTO 建議與理由。看完一場，你會清楚知道「我哪幾手打錯、錯在哪、該怎麼打」。

<p align="center">
  <img src="artifacts-solver-chart-ui.png" alt="n8-review Web UI" width="720">
</p>

---

## ✅ 支援範圍

| 來源 / 類型 | 支援 |
|---|---|
| **Natural8 / GGPoker 錦標賽（MTT）** | ✅ 支援 |
| 其他 GG 網路 skin 的錦標賽 | ✅ 多半可用（同一套手牌歷史格式） |
| 其他撲克室（PokerStars、888、partypoker…） | ❌ 尚未支援（手牌歷史格式不同） |
| 現金局（cash game） | ❌ 尚未支援（目前只解析錦標賽標頭） |

> 簡單說:**目前只吃 Natural8 / GGPoker 的錦標賽手牌歷史**。丟其他撲克室或現金局的檔案會解析不到。

---

## ✨ 特色

- **🎯 逐決策 GTO 評分** — 每手列出 Hero 的每個決策點，依偏離 GTO 的 EV 損失上色。
- **📊 統計報表** — GTO 準確率、每百手 EV 損失、VPIP / PFR / 3Bet / C-bet、各位置盈虧。
- **👥 對手群像** — 聚合重複對手的傾向、產生剝削建議，並回饋給翻後 equity 計算。
- **🖥️ Web UI** — 互動式逐手回放，零後端、零建置，開檔即用。
- **🔌 可插拔 solver** — 預設用輕量 equity/EV 估計；關鍵手可接外部 CFR solver 深解。

---

## 🚀 快速開始

### 1. 安裝

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

### 2. 分析你的手牌

把 n8 匯出的 `.txt` 放進一個資料夾（範例見 `data/`），然後：

```powershell
n8-review analyze ".\data" --json report.json
```

終端機會立刻印出彩色的逐手檢討與統計，同時產生一份 `report.json`。

### 3. 用 Web UI 互動檢視

```powershell
n8-review web --report report.json
```

打開終端機印出的網址（預設 http://127.0.0.1:8765/），就能逐手回放、按位置/街段/結果篩選，並查看漏洞與對手群像。

> 不想開 server？也可以直接用瀏覽器打開 `web/index.html`，再手動載入 `report.json`。

---

## 📖 指令一覽

| 指令 | 用途 |
|---|---|
| `n8-review analyze <路徑>` | 逐手彩色檢討 + 統計 + 漏洞；加 `--json report.json` 匯出給 Web UI |
| `n8-review hand <檔> --id <手牌ID>` | 單手逐街深度檢討 |
| `n8-review stats <路徑>` | 只看統計指標 |
| `n8-review profile <路徑>` | 對手群像（VPIP / PFR / 3Bet / 標籤） |
| `n8-review web --report report.json` | 啟動 Web UI 本機 server |

**常用選項**

```powershell
n8-review analyze ".\data" --hero "Hero"          # 指定 Hero 名稱（預設 "Hero"）
n8-review analyze ".\data" --min-tier inaccuracy  # 只顯示不準以上的手
n8-review hand ".\data\xxx.txt" --id TM6030071921 --postflop solver --solver-path C:\path\solver.exe
```

`<路徑>` 可以是單一 `.txt` 檔，也可以是裝滿手牌檔的資料夾。

---

## 🧠 運作原理

```
.txt ─▶ 解析 ─▶ Hero 視角衍生 ─▶ 逐決策 GTO 評分 ─▶ 報表 / Web UI
                （位置/籌碼/M）   ├ 翻前：GTO 範圍表查表
                                 └ 翻後：equity 估計（預設）或 CFR solver（選用）
```

- **翻前** 比對預存的 GTO 範圍表（各位置 open / 3bet / call、短籌碼 push/fold），是真正的 GTO、離線又快。
- **翻後** 用 equity vs 對手範圍 + EV 啟發法可靠標出「明顯失誤」；想對關鍵手做真 solver 深解，再接上外部 adapter。

Solver adapter 的 JSON 契約見 [`docs/SOLVER_ADAPTER.md`](docs/SOLVER_ADAPTER.md)。

---

## 📁 專案結構

```
n8 analyze/
├── src/n8_review/      核心引擎
│   ├── parser/         手牌歷史文字解析
│   ├── enrich/         Hero 視角衍生（位置、有效籌碼、決策節點）
│   ├── gto/            翻前 GTO 範圍表
│   ├── evaluate/       逐決策評分 + 可插拔翻後後端
│   ├── analysis/       equity / 統計 / 漏洞聚合
│   ├── profile/        對手群像
│   └── report/         CLI 彩色輸出 + JSON 匯出
├── web/                靜態 Web UI（SPA）
├── docs/               solver adapter 契約文件
├── data/               範例手牌歷史
└── tests/              測試
```

---

## 🔬 進階（選用）：接真 solver

**一般使用不需要安裝任何 solver** —— 預設的 equity 後端就能標出明顯失誤。

若你想對關鍵手做真正的 CFR 深解，可以接上 [TexasSolver](https://github.com/bupticybee/TexasSolver)：

1. 下載 TexasSolver 的 `console_solver`（Windows 釋出包已內含，免自行編譯）。
2. 設定它的路徑：`$env:TEXAS_SOLVER_CONSOLE = "C:\TexasSolver\console_solver.exe"`
3. 用內建啟動器跑：
   ```powershell
   n8-review hand ".\data\xxx.txt" --id TM123 --postflop solver --solver-path .\validation\texassolver.cmd
   ```

完整設定、調校參數與模型假設見 [`docs/SOLVER_ADAPTER.md`](docs/SOLVER_ADAPTER.md)。

---

## ⚠️ 關於 EV 估計

未使用 solver 時，`ev_loss_bb` 是引擎的**估計值**（來自圖表 / equity 啟發法），請當作**嚴重度指引**，不是精確的 solver EV。要精確數字，請對該手用 `--postflop solver` 接上 solver adapter。

---

## 🛠️ 開發

```powershell
pip install -e ".[dev]"   # 安裝開發相依（pytest / ruff / mypy）
pytest                    # 測試
ruff check src tests      # lint
mypy src                  # 型別檢查
```

需求：Python 3.11+。

---

## 🤝 貢獻

歡迎 issue 與 PR！送出前請先讀過這幾點，能讓 review 更順：

**動手前**

- 較大的改動建議**先開 issue 對齊方向**，再動手實作。

**寫程式時**（詳見 [`CLAUDE.md`](CLAUDE.md)）

- **保持簡單** —— 用最少的程式碼解決問題，不做沒被要求的抽象或設定彈性。
- **外科手術式修改** —— 只動你必須動的，不順手重構或重排相鄰程式碼；配合既有風格。
- **解析器的容忍原則不可破壞** —— 已知 token 嚴格解析，未知行進 `raw_unparsed` 警告但不中斷。
- 註解**中英文皆可**，配合周圍既有風格即可。

**送出前**

```powershell
pytest                 # 測試要綠
ruff check src tests   # lint 要過
mypy src               # 型別檢查（strict）要過
```

- 改到評分、解析或匯出邏輯時，順手補一個能重現/驗證的測試。
- 一個 PR 專注一件事；commit 訊息寫清楚「改了什麼、為什麼」。

> 提醒：請只編輯 `CLAUDE.md`，`AGENTS.md` 會由 hook 自動同步。

---

## 📌 狀態

核心流程（M1–M7）已完成：解析、Hero 視角衍生、equity 後端、翻前評分、統計 / 漏洞 / 群像、JSON 匯出、Web UI，以及選用的外部 solver adapter。

---

## 📄 授權

MIT License — 詳見 [`LICENSE`](LICENSE)。
