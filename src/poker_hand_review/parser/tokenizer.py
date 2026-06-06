"""把一個 .txt 檔切成多個「原始手牌區塊」。"""

from __future__ import annotations

from pathlib import Path


def split_hands(text: str) -> list[str]:
    """以 'Poker Hand #' 為界，把整檔切成多手；每手保留其原始行。"""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("Poker Hand #"):
            if current:
                blocks.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
    if current:
        blocks.append(current)
    return ["\n".join(b).strip() for b in blocks]


def read_file(path: str | Path) -> list[str]:
    """讀檔並切手；自動處理 BOM。"""
    text = Path(path).read_text(encoding="utf-8-sig")
    return split_hands(text)
