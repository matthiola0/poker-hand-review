"""把 gto-preflop/mtt/8max/charts/ 的 MTT 範圍轉成引擎格式，寫入 src/.../gto/charts/。

來源：gto-preflop/mtt/8max/charts/<stack>bb/{rfi,vs-open}/<name>.json（版控）
目標（套件內，版控）：src/poker_hand_review/gto/charts/<chart_id>.json

引擎 chart_id 命名見 charts/CHARTS.md：
    rfi_<hero>_<bucket>.json
    vs_rfi_<hero>_vs_<opener>_<bucket>.json
    vs_3bet_<hero>_vs_<3bettor>_<bucket>.json

輸出同時帶：
- actions：無損四動作頻率（raise/allin/call/fold）—— 引擎據此評分 raise vs call vs allin
- freqs  ：1 - fold（進入頻率）—— 與既有單頻率模型相容

對接決策（與使用者確認）：
- stack 深度 -> 引擎 5 桶各取一代表檔：push_fold←10、15bb←15、25bb←30、40bb←50、60bb+←100
- 位置 LJ -> 引擎 MP（引擎 8-max 第三位叫 MP，無 LJ）
- 桶內別名：早位 open(UTG/UTG1/MP) 共用 MP 圖；中位(HJ/CO) 共用 CO 圖；
  3bettor IP(CO/BTN) 共用 BTN 圖；3bettor blind(SB/BB) 共用 BB 圖
- 跳過 SB limp 與 cold（引擎無對應 facing）
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_CHARTS = ROOT / "gto-preflop" / "mtt" / "8max" / "charts"
DST = ROOT / "src" / "poker_hand_review" / "gto" / "charts"

# 引擎桶 -> 來源 stack 深度
BUCKET_STACK = {
    "push_fold": 10,
    "15bb": 15,
    "25bb": 30,
    "40bb": 50,
    "60bb+": 100,
}

# RFI：來源位置 -> 引擎位置（LJ->MP）
RFI_POS = {"UTG": "UTG", "UTG1": "UTG1", "LJ": "MP", "HJ": "HJ", "CO": "CO", "BTN": "BTN", "SB": "SB"}

# vs-open 單一加注（防守）檔名 -> (opener 引擎位置, hero 引擎位置)
# 檔名語意為 <開牌桶>-vs-<hero座位>，依 MD 描述對應實際位置。
VS_RFI = {
    "EP-vs-MP": ("MP", "CO"),    # 早位(LJ)open -> 你在中位(CO)
    "EP-vs-BTN": ("MP", "BTN"),
    "EP-vs-SB": ("MP", "SB"),
    "EP-vs-BB": ("MP", "BB"),
    "MP-vs-BTN": ("CO", "BTN"),  # 中位(CO)open -> 你在BTN
    "MP-vs-SB": ("CO", "SB"),
    "MP-vs-BB": ("CO", "BB"),
    "BTN-vs-SB": ("BTN", "SB"),
    "BTN-vs-BB": ("BTN", "BB"),
    "SB-vs-BB": ("SB", "BB"),
}

# vs-3bet 檔名 -> (hero=原開牌者 引擎位置, 3bettor 引擎位置)
VS_3BET = {
    "EPopen-vs-IP3bet": ("MP", "BTN"),
    "EPopen-vs-blind3bet": ("MP", "BB"),
    "MPopen-vs-IP3bet": ("CO", "BTN"),
    "MPopen-vs-blind3bet": ("CO", "BB"),
    "BTNopen-vs-blind3bet": ("BTN", "BB"),
    "SBopen-vs-BB3bet": ("SB", "BB"),
}

# 桶內別名：把同桶的其他引擎位置指向代表位置
OPENER_ALIAS = {"MP": ["UTG", "UTG1"], "CO": ["HJ"]}          # 早位 / 中位 open
TBETTOR_ALIAS = {"BTN": ["CO"], "BB": ["SB"]}                 # IP / blind 3bettor

SKIP = {"BB-vs-SBlimp", "cold-BB", "cold-BTN"}


def load(stack: int, scenario: str, name: str) -> dict | None:
    p = SRC_CHARTS / f"{stack}bb" / scenario / f"{name}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def meta_for(bucket: str, stack: int, scenario: str, name: str, chart_id: str) -> dict:
    return {
        "source": "MTT 8-max preflop GTO ranges",
        "version": "1.0",
        "format": "8-max MTT ante",
        "source_type": "mtt_chart",
        "source_stack_bb": stack,
        "source_scenario": scenario,
        "source_name": name,
        "stack_bucket": bucket,
        "chart_id": chart_id,
        "notes": "actions=four-action frequencies (raise/allin/call/fold); freqs=1-fold.",
    }


def write_chart(chart_id: str, src: dict, bucket: str, stack: int, scenario: str, name: str) -> None:
    out = {
        "meta": meta_for(bucket, stack, scenario, name, chart_id),
        "actions": src["actions"],
        "freqs": src["freqs"],
    }
    (DST / f"{chart_id}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[str] = []

    for bucket, stack in BUCKET_STACK.items():
        # ---- RFI ----
        for shot_pos, eng_pos in RFI_POS.items():
            src = load(stack, "rfi", shot_pos)
            if src is None:
                skipped.append(f"rfi {stack}bb {shot_pos} (來源缺)")
                continue
            cid = f"rfi_{eng_pos}_{bucket}"
            write_chart(cid, src, bucket, stack, "rfi", shot_pos)
            written.append(cid)

        # ---- vs_rfi（防守單一加注）----
        for name, (opener, hero) in VS_RFI.items():
            src = load(stack, "vs-open", name)
            if src is None:
                skipped.append(f"vs_rfi {stack}bb {name} (來源缺)")
                continue
            targets = [opener] + OPENER_ALIAS.get(opener, [])
            for op in targets:
                if op == hero:
                    continue  # 開牌者不可能與 Hero 同位
                cid = f"vs_rfi_{hero}_vs_{op}_{bucket}"
                write_chart(cid, src, bucket, stack, "vs-open", name)
                written.append(cid)

        # ---- vs_3bet ----
        for name, (hero, tbettor) in VS_3BET.items():
            src = load(stack, "vs-open", name)
            if src is None:
                skipped.append(f"vs_3bet {stack}bb {name} (來源缺，短碼不另做)")
                continue
            hero_targets = [hero] + OPENER_ALIAS.get(hero, [])
            tb_targets = [tbettor] + TBETTOR_ALIAS.get(tbettor, [])
            for h in hero_targets:
                for tb in tb_targets:
                    if h == tb:
                        continue  # 3bettor 不可能與開牌者同位
                    cid = f"vs_3bet_{h}_vs_{tb}_{bucket}"
                    write_chart(cid, src, bucket, stack, "vs-open", name)
                    written.append(cid)

    print(f"寫入 {len(written)} 個引擎 chart -> {DST.relative_to(ROOT)}")
    print(f"略過 {len(skipped)} 項（短碼無 vs-open / limp / cold）：")
    for s in skipped[:12]:
        print("  -", s)
    if len(skipped) > 12:
        print(f"  ... 其餘 {len(skipped) - 12} 項")
    print(f"\n跳過情境（引擎無對應 facing）：{', '.join(sorted(SKIP))}")


if __name__ == "__main__":
    main()
