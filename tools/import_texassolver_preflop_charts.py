"""Import bundled TexasSolver preflop range presets into poker-hand-review charts.

This importer consumes the range text files shipped with TexasSolver's
``qb_ranges/100bb 2.5x 500rake`` pack and writes JSON files under
``src/poker_hand_review/gto/charts``. The result is an offline solver-derived chart
set for 100bb cash/rake spots. It is intentionally bucketed as ``60bb+`` so
short-stack MTT spots continue to use their own charts or the built-in fallback.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SOURCE_NAME = "TexasSolver bundled qb_ranges / 100bb 2.5x 500rake"
SOURCE_VERSION = "TexasSolver v0.2.0 Windows bundle"
SOURCE_FORMAT = "6-max NLHE cash, 100bb, 2.5x opens, 500 rake preset"
STACK_BUCKET = "60bb+"

SOURCE_TO_TARGET_POSITIONS = {
    "UTG": ("MP",),
    "MP": ("HJ",),
    "CO": ("CO",),
    "BTN": ("BTN",),
    "SB": ("SB",),
    "BB": ("BB",),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(r"C:\Users\abc35\TexasSolver\TexasSolver-v0.2.0-Windows\ranges\qb_ranges\100bb 2.5x 500rake"),
        help="TexasSolver qb_ranges source directory",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("src/poker_hand_review/gto/charts"),
        help="poker-hand-review chart output directory",
    )
    args = parser.parse_args()

    count = import_charts(args.source, args.out)
    print(f"imported {count} preflop solver charts into {args.out}")


def import_charts(source: Path, out_dir: Path) -> int:
    if not source.exists():
        raise FileNotFoundError(source)
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    count += _import_rfi(source, out_dir)
    count += _import_vs_rfi(source, out_dir)
    count += _import_vs_3bet(source, out_dir)
    return count


def _import_rfi(source: Path, out_dir: Path) -> int:
    count = 0
    for source_pos, target_positions in SOURCE_TO_TARGET_POSITIONS.items():
        if source_pos == "BB":
            continue
        open_size = "3.0bb" if source_pos == "SB" else "2.5bb"
        path = source / source_pos / f"{source_pos}_{open_size}.txt"
        if not path.exists():
            continue
        freqs = _read_range(path)
        for target_pos in target_positions:
            count += _write_chart(
                out_dir,
                chart_id=f"rfi_{target_pos}_{STACK_BUCKET}",
                freqs=freqs,
                source_file=path,
                source_position=source_pos,
                target_position=target_pos,
                action="rfi",
            )
    return count


def _import_vs_rfi(source: Path, out_dir: Path) -> int:
    count = 0
    for source_hero, target_heroes in SOURCE_TO_TARGET_POSITIONS.items():
        hero_dir = source / source_hero
        if not hero_dir.exists():
            continue
        for source_opener, target_openers in SOURCE_TO_TARGET_POSITIONS.items():
            if source_opener == "BB" or source_opener == source_hero:
                continue
            open_size = "3.0bb" if source_opener == "SB" else "2.5bb"
            files = [
                path
                for path in hero_dir.glob(f"{source_opener}_{open_size}_{source_hero}_*.txt")
                if "FOLD" not in path.stem.upper()
            ]
            if not files:
                continue
            freqs = _merge_ranges(files)
            for target_hero in target_heroes:
                for target_opener in target_openers:
                    count += _write_chart(
                        out_dir,
                        chart_id=f"vs_rfi_{target_hero}_vs_{target_opener}_{STACK_BUCKET}",
                        freqs=freqs,
                        source_file=files[0],
                        source_position=source_hero,
                        target_position=target_hero,
                        action="vs_rfi",
                        vs_position=target_opener,
                        source_vs_position=source_opener,
                    )
    return count


def _import_vs_3bet(source: Path, out_dir: Path) -> int:
    count = 0
    for source_hero, target_heroes in SOURCE_TO_TARGET_POSITIONS.items():
        threebet_dir = source / source_hero / "vs_3bet"
        if not threebet_dir.exists():
            continue
        for source_villain, target_villains in SOURCE_TO_TARGET_POSITIONS.items():
            if source_villain == source_hero:
                continue
            files = [
                path
                for path in threebet_dir.glob(f"{source_hero}_2.5bb_{source_villain}_*_{source_hero}_*.txt")
                if "FOLD" not in path.stem.upper()
            ]
            if not files:
                continue
            freqs = _merge_ranges(files)
            for target_hero in target_heroes:
                for target_villain in target_villains:
                    count += _write_chart(
                        out_dir,
                        chart_id=f"vs_3bet_{target_hero}_vs_{target_villain}_{STACK_BUCKET}",
                        freqs=freqs,
                        source_file=files[0],
                        source_position=source_hero,
                        target_position=target_hero,
                        action="vs_3bet",
                        vs_position=target_villain,
                        source_vs_position=source_villain,
                    )
    return count


def _read_range(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    freqs: dict[str, float] = {}
    if not text:
        return freqs
    for token in text.split(","):
        if ":" not in token:
            continue
        hand, value = token.split(":", 1)
        freqs[hand.strip()] = float(value)
    return freqs


def _merge_ranges(paths: list[Path]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for path in paths:
        for hand, freq in _read_range(path).items():
            merged[hand] = max(merged.get(hand, 0.0), freq)
    return merged


def _write_chart(
    out_dir: Path,
    *,
    chart_id: str,
    freqs: dict[str, float],
    source_file: Path,
    source_position: str,
    target_position: str,
    action: str,
    vs_position: str = "",
    source_vs_position: str = "",
) -> int:
    payload = {
        "meta": {
            "source": SOURCE_NAME,
            "version": SOURCE_VERSION,
            "format": SOURCE_FORMAT,
            "source_file": str(source_file),
            "source_position": source_position,
            "source_vs_position": source_vs_position,
            "target_position": target_position,
            "target_vs_position": vs_position,
            "action": action,
            "stack_bucket": STACK_BUCKET,
            "notes": (
                "Imported from TexasSolver bundled preflop range presets. "
                "Use for 60bb+ cash-like spots; short-stack MTT buckets should use matching charts."
            ),
        },
        "freqs": dict(sorted(freqs.items())),
    }
    (out_dir / f"{chart_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 1


if __name__ == "__main__":
    main()
