"""撲克牌表示與解析。"""

from __future__ import annotations

from dataclasses import dataclass

RANKS = "23456789TJQKA"
SUITS = "shdc"


@dataclass(frozen=True)
class Card:
    rank: str  # one of RANKS
    suit: str  # one of SUITS

    def __post_init__(self) -> None:
        if self.rank not in RANKS or self.suit not in SUITS:
            raise ValueError(f"非法撲克牌: {self.rank}{self.suit}")

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


def parse_card(token: str) -> Card:
    """'6s' -> Card('6', 's')。"""
    token = token.strip()
    if len(token) != 2:
        raise ValueError(f"非法牌 token: {token!r}")
    return Card(token[0], token[1])


def parse_cards(text: str) -> tuple[Card, ...]:
    """擷取字串中所有撲克牌，忽略任意數量的中括號分組。

    '[Ah 6h Qs]'、'Ah 6h Qs'、'[Ah 6h Qs] [7d]'（turn/river 多組）皆可。
    """
    text = text.replace("[", " ").replace("]", " ")
    if not text.strip():
        return ()
    return tuple(parse_card(t) for t in text.split())
