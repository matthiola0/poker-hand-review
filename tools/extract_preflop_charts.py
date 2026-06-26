"""把 gto-preflop/ 下的範圍表截圖（PNG）轉成程式可讀的 JSON。

每張 13x13 範圍圖 -> 一個 JSON，含每手牌的四動作頻率（lossless）與
引擎相容的單一進入頻率（freqs = 1 - fold）。

用法（需 Pillow + numpy）：
    python tools/extract_preflop_charts.py

來源結構：gto-preflop/<stack>bb/{rfi,vs-open}/<name>.png
輸出結構：gto-preflop/charts/<stack>bb/{rfi,vs-open}/<name>.json + charts/index.json

色塊（從截圖校準）：紅=raise、深紅=allin、綠=call、藍=fold。
圖片尺寸略有差異，故格線一律按比例（W/13, H/13）計算。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "gto-preflop"
OUT = SRC / "charts"

RANKS = "AKQJT98765432"

# 動作 -> 參考 RGB（從截圖校準）
REF = {
    "raise": (237, 65, 66),
    "allin": (122, 37, 37),
    "call": (90, 175, 100),
    "fold": (66, 125, 180),
}
ACTIONS = list(REF)
REF_ARR = np.array([REF[a] for a in ACTIONS], dtype=np.float32)  # 4x3

# 像素到最近參考色超過此距離者視為文字/格線，排除
MAX_DIST = 70.0
# 取樣窗：手牌標籤(白字)固定在格子上半部，分割一律為垂直(左右)色帶，
# 故只取「格子下緣水平帶」統計左右比例，完全避開文字造成的少數色低估。
# 左右多裁邊，避免相鄰格顏色滲入。
SAMPLE_Y = (0.62, 0.94)   # 下緣帶（避開上方文字）
SAMPLE_X = (0.08, 0.92)   # 去除格線與鄰格滲色


def hand_at(i: int, j: int) -> str:
    """格 (列 i, 欄 j) -> 手牌鍵。對角=對子，上三角=同花，下三角=非同花。"""
    hi, lo = RANKS[min(i, j)], RANKS[max(i, j)]
    if i == j:
        return hi + lo
    return f"{hi}{lo}s" if i < j else f"{hi}{lo}o"


def snap(x: float) -> float:
    if x < 0.03:
        return 0.0
    if x > 0.97:
        return 1.0
    return round(x, 2)


def extract(path: Path) -> dict[str, dict[str, float]]:
    """回傳 {手牌: {動作: 頻率}}。"""
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    h, w, _ = arr.shape
    actions: dict[str, dict[str, float]] = {}
    for i in range(13):
        for j in range(13):
            y0 = int((i + SAMPLE_Y[0]) * h / 13)
            y1 = int((i + SAMPLE_Y[1]) * h / 13)
            x0 = int((j + SAMPLE_X[0]) * w / 13)
            x1 = int((j + SAMPLE_X[1]) * w / 13)
            reg = arr[y0:y1, x0:x1].reshape(-1, 3)
            # 每像素到 4 參考色的距離
            d = np.linalg.norm(reg[:, None, :] - REF_ARR[None, :, :], axis=2)  # N x 4
            nearest = d.argmin(1)
            mindist = d.min(1)
            keep = mindist <= MAX_DIST
            total = int(keep.sum())
            hand = hand_at(i, j)
            if total == 0:
                actions[hand] = {"fold": 1.0}  # 退化情形：當作 fold
                continue
            counts = np.bincount(nearest[keep], minlength=4)
            cell = {}
            for k, name in enumerate(ACTIONS):
                f = snap(counts[k] / total)
                if f > 0:
                    cell[name] = f
            actions[hand] = cell or {"fold": 1.0}
    return actions


def enter_freq(cell: dict[str, float]) -> float:
    return round(min(1.0, sum(v for a, v in cell.items() if a != "fold")), 2)


def parse_name(stem: str) -> str:
    """去掉檔名前面的排序編號，如 '1-UTG' -> 'UTG'、'10-SB-vs-BB' -> 'SB-vs-BB'。"""
    return re.sub(r"^\d+-", "", stem)


def main() -> None:
    index = []
    n = 0
    for stack_dir in sorted(SRC.glob("*bb"), key=lambda p: int(p.name[:-2]), reverse=True):
        stack_bb = int(stack_dir.name[:-2])
        for scenario in ("rfi", "vs-open"):
            sdir = stack_dir / scenario
            if not sdir.is_dir():
                continue
            for img in sorted(sdir.glob("*.png")):
                name = parse_name(img.stem)
                actions = extract(img)
                freqs = {h: enter_freq(c) for h, c in actions.items()}
                meta = {
                    "stack_bb": stack_bb,
                    "scenario": scenario,
                    "name": name,
                    "source_image": str(img.relative_to(SRC)).replace("\\", "/"),
                    "colors": {"raise": "red", "allin": "darkred", "call": "green", "fold": "blue"},
                    "grid": "13x13",
                    "note": "actions=完整四動作頻率(lossless)；freqs=1-fold(引擎相容進入頻率)",
                }
                out_path = OUT / stack_dir.name / scenario / f"{name}.json"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(
                    json.dumps({"meta": meta, "actions": actions, "freqs": freqs}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                index.append(
                    {
                        "stack_bb": stack_bb,
                        "scenario": scenario,
                        "name": name,
                        "path": str(out_path.relative_to(OUT)).replace("\\", "/"),
                    }
                )
                n += 1
    (OUT).mkdir(parents=True, exist_ok=True)
    (OUT / "index.json").write_text(
        json.dumps({"count": n, "charts": index}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完成：{n} 張圖 -> JSON，索引 charts/index.json")


if __name__ == "__main__":
    main()
