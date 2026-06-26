# GTO 翻前圖表資料

本目錄存放翻前 GTO 範圍表資料檔（JSON），供 `preflop_charts.lookup()` 載入。

## 檔案命名
`<action>_<hero_pos>[_vs_<vs_pos>]_<stack_bucket>.json`
例：`rfi_BTN_25bb.json`、`vs_rfi_BB_vs_BTN_40bb.json`、`push_fold_SB.json`

## 資料格式
```json
{
  "meta": { "source": "...", "version": "...", "format": "8-max MTT ante", "source_type": "mtt_chart" },
  "actions": { "AA": { "raise": 0.21, "call": 0.79 }, "72o": { "fold": 1.0 } },
  "freqs":   { "AA": 1.0, "72o": 0.0 }
}
```
- `actions`：範圍鍵 -> 四動作頻率（`raise` / `allin` / `call` / `fold`）。引擎據此區分
  raise vs call vs allin 來評分；任一頻率 ≥ 0.05 的動作視為 GTO 混合策略的一部分（不扣分）。
- `freqs`：範圍鍵 -> 進入頻率（= 1 − fold），與舊單頻率模型相容；`actions` 缺漏時退回此欄。
- `meta.source_type`：`mtt_chart`（本專案 MTT 圖）/ `solver_chart`（外部 solver）/ 預設視為 solver。

## 來源與版本（預設：MTT）
- 預設翻前範圍為 **8-max MTT** 圖，由 `tools/import_mtt_preflop_charts.py` 從
  `gto-preflop/mtt/8max/charts/` 的範圍資料匯入，含完整四動作頻率。
- stack 深度 → 引擎 5 桶各取一代表檔：`push_fold←10bb`、`15bb←15bb`、`25bb←30bb`、
  `40bb←50bb`、`60bb+←100bb`。
- 桶內位置別名：早位 open（UTG/UTG1/MP）共用 MP 圖；中位（HJ/CO）共用 CO 圖；
  3bettor IP（CO/BTN）共用 BTN 圖；3bettor blind（SB/BB）共用 BB 圖。
- 未涵蓋情境（如短碼 vs 3bet、SB limp、多人 cold）回退 built-in approximate ranges 並於 UI 標示。
- 重新匯入：先刪舊 `*.json`，再跑 `python tools/import_mtt_preflop_charts.py`。

## 涵蓋範圍
- RFI：各位置全 5 桶。
- vs RFI（防守 call/3bet）：CO/BTN/SB/BB 對早/中/後位開牌，全 5 桶。
- vs 3bet：開牌者 MP/CO/BTN/SB 對 IP/blind 3bet，僅 25bb/40bb/60bb+。
