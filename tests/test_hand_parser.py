"""Parser 單元測試（M1）。"""

from __future__ import annotations

from poker_hand_review.models import ActionType, Street
from poker_hand_review.parser import parse_hand, split_hands

SAMPLE = """Poker Hand #TM6030071921: Tournament #287580360, Bounty Hunters Special $10.80 Hold'em No Limit - Level6(150/300(45)) - 2026/06/02 18:50:00
Table '105' 8-max Seat #8 is the button
Seat 1: 4b49ee9d (14,135 in chips)
Seat 5: Hero (8,683 in chips)
Seat 8: 300a78cd (15,140 in chips)
Hero: posts the ante 45
4b49ee9d: posts small blind 150
dcb4b332: posts big blind 300
*** HOLE CARDS ***
Dealt to Hero [6s 6d]
e49622c3: raises 300 to 600
Hero: calls 600
*** FLOP *** [Ah 6h Qs]
Hero: raises 1,860 to 3,300
*** TURN *** [Ah 6h Qs] [7d]
Hero: bets 4,738 and is all-in
e49622c3: calls 4,738
Hero: shows [6s 6d] (three of a kind, Sixes)
*** RIVER *** [Ah 6h Qs 7d] [Tc]
*** SHOWDOWN ***
e49622c3 collected 22,076 from pot
*** SUMMARY ***
Total pot 22,076 | Rake 0 | Jackpot 0
Board [Ah 6h Qs 7d Tc]
Seat 3: e49622c3 showed [As Ac] and won (22,076) with three of a kind, Aces
Seat 5: Hero showed [6s 6d] and lost with three of a kind, Sixes
"""


def test_header_and_tournament():
    hand = parse_hand(SAMPLE)
    assert hand.hand_id == "TM6030071921"
    assert hand.tournament.tid == "287580360"
    assert hand.tournament.level == 6
    assert (hand.tournament.sb, hand.tournament.bb, hand.tournament.ante) == (150, 300, 45)
    assert hand.max_seats == 8
    assert hand.button_seat == 8


def test_hero_hole_and_seats():
    hand = parse_hand(SAMPLE)
    assert [str(c) for c in hand.hero_hole] == ["6s", "6d"]
    assert hand.hero_seat.stack == 8683
    assert hand.hero_seat.is_hero


def test_streets_and_allin():
    hand = parse_hand(SAMPLE)
    streets = {s.street: s for s in hand.streets}
    assert Street.FLOP in streets
    turn = streets[Street.TURN]
    allin = [a for a in turn.actions if a.all_in]
    assert allin and allin[0].player == "Hero" and allin[0].type == ActionType.BET


def test_total_pot_and_showdown():
    hand = parse_hand(SAMPLE)
    assert hand.total_pot == 22076
    villain = [s for s in hand.showdowns if s.player == "e49622c3"]
    assert villain and villain[0].won == 22076


def test_amount_comma_stripped():
    hand = parse_hand(SAMPLE)
    flop = next(s for s in hand.streets if s.street == Street.FLOP)
    raise_action = next(a for a in flop.actions if a.type == ActionType.RAISE)
    assert raise_action.to_amount == 3300


def test_split_hands_counts_blocks():
    doubled = SAMPLE + "\n\n" + SAMPLE.replace("TM6030071921", "TM6030071922")
    assert len(split_hands(doubled)) == 2
