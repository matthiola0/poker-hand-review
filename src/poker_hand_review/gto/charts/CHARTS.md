# GTO 翻前圖表資料

本目錄存放翻前 GTO 範圍表資料檔（JSON），供 `preflop_charts.lookup()` 載入。

## 檔案命名
`<action>_<hero_pos>[_vs_<vs_pos>]_<stack_bucket>.json`
例：`rfi_BTN_25bb.json`、`vs_rfi_BB_vs_BTN_40bb.json`、`push_fold_SB.json`

## 資料格式（草案，M4 凍結）
```json
{
  "meta": { "source": "<圖表來源>", "version": "...", "format": "8-max MTT ante" },
  "freqs": { "AA": 1.0, "AKs": 1.0, "A5s": 0.5, "72o": 0.0 }
}
```
`freqs`：範圍鍵（`ranges.hand_key` 格式）-> 進入頻率 0..1。

## 來源與版本
- `*_60bb+.json`：由 `tools/import_texassolver_preflop_charts.py` 從
  `TexasSolver-v0.2.0-Windows/ranges/qb_ranges/100bb 2.5x 500rake` 匯入。
  這是 TexasSolver bundle 內附的 6-max NLHE cash 100bb / 2.5x open / rake preset
  preflop ranges，作為 `60bb+` cash-like spot 的離線 solver-derived chart。
- 這些 `60bb+` chart 不應硬套到 15bb/25bb/40bb MTT ante spot；短籌碼 MTT bucket
  若沒有對應 JSON，系統會回退到 built-in approximate ranges 並在 UI 標示。
- 圖表可替換；更動請更新 `meta.version` 並於此記錄。

## 涵蓋範圍（規劃）
- 深籌碼（≥40bb）：各位置 RFI、vs RFI（call/3bet）、vs 3bet。
- 中淺（15–32bb）：簡化 RFI 與防守。
- ≤~12bb：Nash 推/棄。
