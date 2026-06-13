"""集中所有 GG/n8 文字格式的正規表示式。"""

from __future__ import annotations

import re

# 標頭：Poker Hand #<id>: Tournament #<tid>, <name> - Level<n>(sb/bb(ante)) - <ts>
HEADER = re.compile(
    r"^Poker Hand #(?P<hand_id>\w+): Tournament #(?P<tid>\d+), "
    r"(?P<name>.+?) - Level(?P<level>\d+)\("
    r"(?P<sb>[\d,]+)/(?P<bb>[\d,]+)(?:\((?P<ante>[\d,]+)\))?\) - "
    r"(?P<ts>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"
)

# Table '105' 8-max Seat #8 is the button
TABLE = re.compile(
    r"^Table '(?P<table>[^']+)' (?P<max>\d+)-max Seat #(?P<button>\d+) is the button"
)

# Seat 1: 4b49ee9d (14,135 in chips)
SEAT = re.compile(r"^Seat (?P<seat>\d+): (?P<player>.+?) \((?P<stack>[\d,]+) in chips\)")

# 街段標記
STREET_MARKER = re.compile(r"^\*\*\* (?P<name>[A-Z ]+) \*\*\*(?: (?P<cards>\[.+\]))?")

# Dealt to Hero [6s 6d]
DEALT = re.compile(r"^Dealt to (?P<player>.+?)(?: \[(?P<cards>[^\]]+)\])?$")

# 動作行（玩家: 動詞 ...）
A_ANTE = re.compile(r"^(?P<player>.+?): posts the ante (?P<amt>[\d,]+)")
A_SB = re.compile(r"^(?P<player>.+?): posts small blind (?P<amt>[\d,]+)")
A_BB = re.compile(r"^(?P<player>.+?): posts big blind (?P<amt>[\d,]+)")
A_FOLD = re.compile(r"^(?P<player>.+?): folds")
A_CHECK = re.compile(r"^(?P<player>.+?): checks")
A_CALL = re.compile(r"^(?P<player>.+?): calls (?P<amt>[\d,]+)(?P<allin> and is all-in)?")
A_BET = re.compile(r"^(?P<player>.+?): bets (?P<amt>[\d,]+)(?P<allin> and is all-in)?")
A_RAISE = re.compile(
    r"^(?P<player>.+?): raises (?P<amt>[\d,]+) to (?P<to>[\d,]+)(?P<allin> and is all-in)?"
)
A_SHOW = re.compile(r"^(?P<player>.+?): shows \[(?P<cards>[^\]]+)\]")

# 收池 / 退注
COLLECT = re.compile(r"^(?P<player>.+?) collected (?P<amt>[\d,]+) from pot")
UNCALLED = re.compile(r"^Uncalled bet \((?P<amt>[\d,]+)\) returned to (?P<player>.+)$")

# SUMMARY
TOTAL_POT = re.compile(r"^Total pot (?P<amt>[\d,]+)")
SUMMARY_BOARD = re.compile(r"^Board \[(?P<cards>[^\]]+)\]")
_SUMMARY_POSITION = r"(?: \((?:button|small blind|big blind)\))?"
SUMMARY_SHOWED = re.compile(
    r"^Seat (?P<seat>\d+): (?P<player>.+?)"
    + _SUMMARY_POSITION
    + r" showed \[(?P<cards>[^\]]+)\] and "
    r"(?:(?:won \((?P<won>[\d,]+)\))|lost)(?: with (?P<rank>.+))?$"
)
SUMMARY_MUCKED = re.compile(
    r"^Seat (?P<seat>\d+): (?P<player>.+?)"
    + _SUMMARY_POSITION
    + r" mucked(?: \[(?P<cards>[^\]]+)\])?$"
)
SUMMARY_FOLDED = re.compile(
    r"^Seat (?P<seat>\d+): (?P<player>.+?)"
    + _SUMMARY_POSITION
    + r" folded (?:before Flop|on the (?:Flop|Turn|River))$"
)
SUMMARY_COLLECTED = re.compile(
    r"^Seat (?P<seat>\d+): (?P<player>.+?)"
    + _SUMMARY_POSITION
    + r" collected \((?P<amt>[\d,]+)\)$"
)


def to_int(s: str) -> int:
    """'1,440' -> 1440。"""
    return int(s.replace(",", ""))
