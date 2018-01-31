from typing import List, Tuple

from poker import Card, Hand, best_possible_hand

HoleCards = Tuple[Card, Card]

SPADE = '♠'
HEART = '♥'
DIAMOND = '♦'
CLUB = '♣'

# Tests that two pairs of hole cards with given community cards are ranked correctly
# expected is the expected result. 1 means hand1 should win, 2 means hand2 should win
# 0 means the two hands should tie
def test_ranking(public: List[Card], hand1: HoleCards, hand2: HoleCards, expected: int) -> bool:
    best_hand1 = best_possible_hand(public, hand1)
    best_hand2 = best_possible_hand(public, hand2)
    if best_hand1 == best_hand2:
        winner = 0
    elif best_hand1 > best_hand2:
        winner = 1
    else:
        winner = 2
    if winner == expected:
        return True
    expected_strs = ["a tie", "hand 1 to win", "hand 2 to win"]
    actualstrs = ["the two hands tied", "hand 1 won", "hand 2 won"]
    print("Test failed! Expected", expected_strs[expected], "but", actualstrs[winner])
    print("Shared cards:",  " ".join(str(card) for card in public))
    print("Hole cards 1: ", " ".join(str(card) for card in hand1))
    print("Hole cards 2: ", " ".join(str(card) for card in hand2))
    print("Hand 1: ", " ".join(str(card) for card in best_hand1.cards))
    print("Hand 2: ", " ".join(str(card) for card in best_hand2.cards))
    print("")
    return False

# Tests a list of test cases to see that the hands will be ranked appropriately
def test_rankings(hands: List[Tuple[List[Card], HoleCards, HoleCards, int]]):
    print("Testing hand rankings:")
    tests_passed = 0
    for hand in hands:
        if test_ranking(*hand):
            tests_passed += 1
    print(f"{tests_passed} out of {len(hands)} tests passed!")
    print("")

# Tests that the description for the hands are correct
def test_hand_descriptions(test_cases: List[Tuple[Hand, str]]):
    print("Testing hand descriptions:")
    tests_passed = 0
    for hand, description in test_cases:
        if str(hand) == description:
            tests_passed += 1
        else:
            print(f"Test failed! Expected '{description}', but got {str(hand)}!")
            print("Hand: ", " ".join(str(card) for card in hand.cards))
            print("")
    print(f"{tests_passed} out of {len(test_cases)} tests passed!")
    print("")

test_rankings([
    # Testing that a high card beats a less-high card
    ([Card(SPADE, '9'), Card(CLUB, '4'), Card(HEART, '5'), Card(SPADE, '6'), Card(HEART, '7')],
     (Card(CLUB, 'K'), Card(CLUB, 'Q')),
     (Card(CLUB, 'A'), Card(CLUB, '2')),
     2),

    # The next highest card decides it if the first highest cards tie
    ([Card(SPADE, 'J'), Card(CLUB, '2'), Card(HEART, '5'), Card(SPADE, '9'), Card(HEART, '10')],
     (Card(CLUB, 'A'), Card(CLUB, '8')),
     (Card(DIAMOND, 'A'), Card(CLUB, '7')),
     1),

    # If the board beats all the hole cards, the two players should tie
    ([Card(SPADE, 'J'), Card(CLUB, '10'), Card(HEART, '9'), Card(SPADE, '8'), Card(HEART, '6')],
     (Card(CLUB, '5'), Card(CLUB, '4')),
     (Card(CLUB, '3'), Card(CLUB, '2')),
     0),

    # A pair beats a high card
    ([Card(SPADE, '2'), Card(CLUB, '4'), Card(HEART, '5'), Card(DIAMOND, '6'), Card(CLUB, '7')],
     (Card(CLUB, '2'), Card(CLUB, '3')),
     (Card(CLUB, 'A'), Card(CLUB, 'K')),
     1),

    # A high pair beats a low pair
    ([Card(SPADE, '2'), Card(DIAMOND, '3'), Card(HEART, '5'), Card(DIAMOND, '6'), Card(CLUB, '7')],
     (Card(CLUB, '2'), Card(CLUB, 'A')),
     (Card(CLUB, '3'), Card(CLUB, '4')),
     2),

    # The pair with a higher kicker beats the same pair with a worse kicker
    ([Card(SPADE, '2'), Card(CLUB, '4'), Card(HEART, '5'), Card(DIAMOND, '6'), Card(CLUB, '7')],
     (Card(CLUB, '2'), Card(CLUB, 'A')),
     (Card(HEART, '2'), Card(CLUB, 'K')),
     1),

    # The kicker for pairs doesn't matter if they're both too low
    ([Card(SPADE, '2'), Card(CLUB, 'K'), Card(HEART, 'Q'), Card(DIAMOND, 'J'), Card(CLUB, '7')],
     (Card(DIAMOND, 'K'), Card(CLUB, '3')),
     (Card(SPADE, 'K'), Card(CLUB, '6')),
     0),

    # Two pair beats one pair
    ([Card(SPADE, '2'), Card(CLUB, '3'), Card(HEART, '5'), Card(DIAMOND, '6'), Card(CLUB, '7')],
     (Card(DIAMOND, '2'), Card(SPADE, '3')),
     (Card(CLUB, 'A'), Card(DIAMOND, 'A')),
     1),

    # The higher pair for a two pair decides which one wins
    ([Card(SPADE, '2'), Card(CLUB, '4'), Card(HEART, '5'), Card(DIAMOND, '6'), Card(CLUB, '7')],
     (Card(CLUB, '5'), Card(SPADE, '6')),
     (Card(CLUB, '2'), Card(SPADE, '7')),
     2),

    # The second pair can decide for two tied two pairs
    ([Card(CLUB, '2'), Card(SPADE, '4'), Card(DIAMOND, '6'), Card(HEART, '8'), Card(CLUB, '10')],
     (Card(SPADE, '10'), Card(CLUB, '4')),
     (Card(HEART, '10'), Card(SPADE, '2')),
     1),

    # The kicker can decide it who wins if both players have the same two pair
    ([Card(CLUB, 'K'), Card(SPADE, '9'), Card(HEART, '9'), Card(DIAMOND, '3'), Card(SPADE, '2')],
     (Card(SPADE, 'K'), Card(CLUB, '4')),
     (Card(HEART, 'K'), Card(CLUB, '5')),
     2),

    # Two pairs can tie if the two pairs are the same and the kickers are too low
    ([Card(CLUB, 'K'), Card(SPADE, '9'), Card(HEART, '9'), Card(DIAMOND, '5'), Card(SPADE, '2')],
     (Card(SPADE, 'K'), Card(CLUB, '4')),
     (Card(HEART, 'K'), Card(CLUB, '3')),
     0),

    # Three-of-a-kind beats a pair
    ([Card(SPADE, '2'), Card(SPADE, 'A'), Card(CLUB, '10'), Card(HEART, 'J'), Card(DIAMOND, '6')],
     (Card(CLUB, '2'), Card(HEART, '2')),
     (Card(DIAMOND, 'A'), Card(CLUB, 'K')),
     1),

    # Three-of-a-kind beats two pair
    ([Card(SPADE, '2'), Card(SPADE, 'A'), Card(CLUB, '10'), Card(HEART, 'K'), Card(DIAMOND, '6')],
     (Card(DIAMOND, 'A'), Card(CLUB, 'K')),
     (Card(CLUB, '2'), Card(HEART, '2')),
     2),

    # A higher three-of-a-kind beats a lower three-of-a-kind
    ([Card(CLUB, 'K'), Card(SPADE, 'Q'), Card(HEART, '5'), Card(HEART, '4'), Card(HEART, '3')],
     (Card(SPADE, 'K'), Card(HEART, 'K')),
     (Card(CLUB, 'Q'), Card(HEART, 'Q')),
     1),

    # A three-of-a-kind with a higher kicker beats the same three-of-a-kind with a lower
    ([Card(CLUB, '10'), Card(SPADE, '10'), Card(HEART, 'J'), Card(DIAMOND, '6'), Card(CLUB, '2')],
     (Card(DIAMOND, '10'), Card(DIAMOND, 'K')),
     (Card(HEART, '10'), Card(CLUB, 'A')),
     2),

    # Two three-of-a-kinds can tie with different kickers if the kickers are low enough
    ([Card(CLUB, '10'), Card(SPADE, '10'), Card(HEART, 'J'), Card(DIAMOND, '6'), Card(CLUB, 'K')],
     (Card(DIAMOND, '10'), Card(DIAMOND, '3')),
     (Card(HEART, '10'), Card(CLUB, '2')),
     0),

    # Staight beats a pair
    ([Card(CLUB, '10'), Card(SPADE, '9'), Card(DIAMOND, '8'), Card(HEART, '7'), Card(SPADE, 'A')],
     (Card(CLUB, 'A'), Card(SPADE, 'K')),
     (Card(CLUB, '6'), Card(CLUB, '2')),
     2),

    # Straight beats two pair
    ([Card(CLUB, '10'), Card(SPADE, '9'), Card(DIAMOND, '8'), Card(HEART, 'K'), Card(SPADE, 'A')],
     (Card(CLUB, '6'), Card(CLUB, '7')),
     (Card(CLUB, 'A'), Card(SPADE, 'K')),
     1),

    # Straight beats three-of-a-kind
    ([Card(CLUB, '10'), Card(SPADE, '9'), Card(DIAMOND, '8'), Card(HEART, 'A'), Card(SPADE, 'A')],
     (Card(CLUB, 'A'), Card(SPADE, 'K')),
     (Card(CLUB, '6'), Card(CLUB, '7')),
     2),

    # A higher straight beats a lower one
    ([Card(CLUB, '10'), Card(SPADE, '9'), Card(DIAMOND, '8'), Card(HEART, '7'), Card(SPADE, 'A')],
     (Card(CLUB, 'J'), Card(SPADE, '2')),
     (Card(CLUB, '6'), Card(CLUB, 'A')),
     1),

    # Straights can tie
    ([Card(CLUB, '10'), Card(SPADE, '9'), Card(DIAMOND, '8'), Card(HEART, '7'), Card(SPADE, 'A')],
     (Card(CLUB, '6'), Card(SPADE, '2')),
     (Card(SPADE, '6'), Card(CLUB, 'A')),
     0),

    # Flush beats a pair
    ([Card(CLUB, '5'), Card(CLUB, '6'), Card(CLUB, '7'), Card(SPADE, 'A'), Card(SPADE, 'Q')],
     (Card(CLUB, '3'), Card(CLUB, '2')),
     (Card(HEART, 'A'), Card(HEART, 'K')),
     1),

    # Flush beats two pair
    ([Card(CLUB, '5'), Card(CLUB, '6'), Card(CLUB, '7'), Card(SPADE, 'A'), Card(SPADE, 'K')],
     (Card(CLUB, '3'), Card(CLUB, '2')),
     (Card(HEART, 'A'), Card(HEART, 'K')),
     1),

    # Flush beats three-of-a-kind
    ([Card(CLUB, '5'), Card(CLUB, '6'), Card(CLUB, '7'), Card(SPADE, 'A'), Card(CLUB, 'K')],
     (Card(CLUB, '3'), Card(CLUB, '2')),
     (Card(HEART, 'A'), Card(DIAMOND, 'A')),
     1),

    # Flush beats a straight
    ([Card(CLUB, '5'), Card(CLUB, '6'), Card(CLUB, '7'), Card(SPADE, 'A'), Card(SPADE, 'Q')],
     (Card(CLUB, '3'), Card(CLUB, '2')),
     (Card(HEART, '8'), Card(HEART, '9')),
     1),

    # Higher flush beats lower flush
    ([Card(SPADE, '7'), Card(SPADE, '4'), Card(SPADE, '8'), Card(DIAMOND, 'K'), Card(CLUB, 'K')],
     (Card(SPADE, 'K'), Card(SPADE, 'Q')),
     (Card(SPADE, 'A'), Card(SPADE, '2')),
     2),

    # Full house beats a pair
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(HEART, '3'), Card(DIAMOND, 'Q'), Card(DIAMOND, 'J')],
     (Card(HEART, '2'), Card(SPADE, '3')),
     (Card(DIAMOND, 'K'), Card(DIAMOND, 'A')),
     1),

    # Full house beats two pair
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(HEART, '3'), Card(DIAMOND, 'Q'), Card(DIAMOND, 'A')],
     (Card(DIAMOND, 'K'), Card(SPADE, 'A')),
     (Card(HEART, '2'), Card(SPADE, '3')),
     2),

    # Full house beats three-of-a-kind
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(HEART, '3'), Card(DIAMOND, 'Q'), Card(DIAMOND, 'A')],
     (Card(HEART, '2'), Card(SPADE, '3')),
     (Card(DIAMOND, 'K'), Card(DIAMOND, '2')),
     1),

    # Full house beats a straight
    ([Card(SPADE, '2'), Card(HEART, '2'), Card(CLUB, 'J'), Card(DIAMOND, '10'), Card(SPADE, 'Q')],
     (Card(SPADE, 'A'), Card(SPADE, 'K')),
     (Card(CLUB, '2'), Card(CLUB, 'Q')),
     2),

    # Full house beats a flush
    ([Card(SPADE, '2'), Card(HEART, '2'), Card(SPADE, 'J'), Card(DIAMOND, '10'), Card(SPADE, 'Q')],
     (Card(CLUB, '2'), Card(CLUB, 'Q')),
     (Card(SPADE, 'A'), Card(SPADE, 'K')),
     1),

    # Ties between full houses are decided by the three-of-a-kind
    ([Card(SPADE, 'A'), Card(SPADE, 'K'), Card(CLUB, 'J'), Card(HEART, 'J'), Card(DIAMOND, '3')],
     (Card(CLUB, 'A'), Card(DIAMOND, 'J')),
     (Card(CLUB, 'K'), Card(DIAMOND, 'K')),
     2),

    # If the three-of-a-kinds of two full houses tie, then the pairs decide
    ([Card(SPADE, 'A'), Card(CLUB, 'A'), Card(HEART, 'A'), Card(CLUB, 'J'), Card(CLUB, '10')],
     (Card(HEART, 'J'), Card(CLUB, '2')),
     (Card(HEART, '10'), Card(CLUB, 'K')),
     1),

    # Two full houses can tie when everything's the same rank
    ([Card(SPADE, '3'), Card(CLUB, '3'), Card(HEART, '2'), Card(CLUB, '2'), Card(DIAMOND, '4')],
     (Card(DIAMOND, '3'), Card(SPADE, 'A')),
     (Card(HEART, '3'), Card(CLUB, '5')),
     0),

    # Four of a kind beats a pair
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(SPADE, 'A'), Card(HEART, 'J'), Card(DIAMOND, '9')],
     (Card(DIAMOND, '2'), Card(HEART, '2')),
     (Card(SPADE, 'K'), Card(SPADE, 'Q')),
     1),

    # Four of a kind beats two pair
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(SPADE, 'A'), Card(HEART, 'J'), Card(DIAMOND, '9')],
     (Card(DIAMOND, '2'), Card(HEART, '2')),
     (Card(SPADE, 'K'), Card(CLUB, 'A')),
     1),

    # Four of a kind beats three of a kind
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(SPADE, 'Q'), Card(HEART, '2'), Card(DIAMOND, '9')],
     (Card(DIAMOND, '2'), Card(HEART, '3')),
     (Card(SPADE, 'K'), Card(CLUB, 'A')),
     1),

    # Four of a kind beats a straight
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(SPADE, 'Q'), Card(HEART, 'J'), Card(DIAMOND, '10')],
     (Card(DIAMOND, '2'), Card(HEART, '2')),
     (Card(SPADE, 'K'), Card(CLUB, 'A')),
     1),

    # Four of a kind beats a flush
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(SPADE, '7'), Card(HEART, 'J'), Card(SPADE, '10')],
     (Card(DIAMOND, '2'), Card(HEART, '2')),
     (Card(SPADE, 'K'), Card(SPADE, 'A')),
     1),

    # Four of a kind beats a full house
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(SPADE, '7'), Card(HEART, 'J'), Card(DIAMOND, 'A')],
     (Card(DIAMOND, '2'), Card(HEART, '2')),
     (Card(DIAMOND, '7'), Card(CLUB, '7')),
     1),

    # Ties between four of a kinds are decided by the kicker
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(SPADE, '7'), Card(HEART, '2'), Card(DIAMOND, '2')],
     (Card(DIAMOND, 'K'), Card(HEART, 'Q')),
     (Card(SPADE, '3'), Card(SPADE, 'A')),
     2),

    # The kickers of four-of-a-kinds can tie
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(SPADE, '7'), Card(HEART, '2'), Card(DIAMOND, '2')],
     (Card(DIAMOND, 'K'), Card(HEART, 'Q')),
     (Card(SPADE, 'K'), Card(CLUB, 'K')),
     0),

    # The four-of-a-kind kickers might not be high enough to matter
    ([Card(SPADE, '2'), Card(CLUB, '2'), Card(SPADE, 'A'), Card(HEART, '2'), Card(DIAMOND, '2')],
     (Card(DIAMOND, 'K'), Card(HEART, 'Q')),
     (Card(SPADE, '3'), Card(CLUB, '4')),
     0),

    # Straight flush beats a pair
    ([Card(SPADE, '2'), Card(SPADE, '3'), Card(SPADE, '4'), Card(CLUB, 'A'), Card(CLUB, 'K')],
     (Card(SPADE, '5'), Card(SPADE, '6')),
     (Card(HEART, 'A'), Card(HEART, 'Q')),
     1),

    # Straight flush beats two pair
    ([Card(SPADE, '2'), Card(SPADE, '3'), Card(SPADE, '4'), Card(CLUB, 'A'), Card(CLUB, 'K')],
     (Card(SPADE, '5'), Card(SPADE, '6')),
     (Card(HEART, 'A'), Card(HEART, 'K')),
     1),

    # Straight flush beats three-of-a-kind
    ([Card(SPADE, '2'), Card(SPADE, '3'), Card(SPADE, '4'), Card(CLUB, 'A'), Card(CLUB, 'K')],
     (Card(SPADE, '5'), Card(SPADE, '6')),
     (Card(HEART, 'A'), Card(DIAMOND, 'A')),
     1),

    # Straight flush beats straight
    ([Card(SPADE, '2'), Card(SPADE, '3'), Card(SPADE, '4'), Card(CLUB, 'A'), Card(CLUB, 'K')],
     (Card(SPADE, '5'), Card(SPADE, 'A')),
     (Card(HEART, '5'), Card(HEART, '6')),
     1),

    # Straight flush beats flush
    ([Card(SPADE, '2'), Card(SPADE, '3'), Card(SPADE, '4'), Card(CLUB, 'Q'), Card(CLUB, 'J')],
     (Card(SPADE, '5'), Card(SPADE, '6')),
     (Card(SPADE, 'A'), Card(SPADE, 'K')),
     1),

    # Straight flush beats full house
    ([Card(SPADE, '2'), Card(SPADE, '3'), Card(SPADE, '4'), Card(CLUB, '2'), Card(CLUB, 'A')],
     (Card(SPADE, '5'), Card(SPADE, '6')),
     (Card(HEART, 'A'), Card(DIAMOND, 'A')),
     1),

    # Higher straight flush beats a lower straight flush
    ([Card(SPADE, 'Q'), Card(SPADE, 'J'), Card(SPADE, '10'), Card(CLUB, '2'), Card(HEART, '3')],
     (Card(SPADE, 'K'), Card(SPADE, 'A')),
     (Card(SPADE, '9'), Card(SPADE, '8')),
     1),

    # The same straight flush will tie with itself
    ([Card(SPADE, 'A'), Card(SPADE, '2'), Card(SPADE, '3'), Card(SPADE, '4'), Card(SPADE, '5')],
     (Card(CLUB, '6'), Card(CLUB, '7')),
     (Card(HEART, 'A'), Card(CLUB, 'A')),
     0),
])

test_hand_descriptions([
    (Hand([Card(SPADE, '2'),
           Card(HEART, '3'),
           Card(HEART, '4'),
           Card(HEART, '5'),
           Card(HEART, '7')]),
     "seven high"
    ),
    (Hand([Card(SPADE, 'J'),
           Card(HEART, 'A'),
           Card(HEART, 'K'),
           Card(HEART, '10'),
           Card(HEART, '9')]),
     "ace high"
    ),
    (Hand([Card(SPADE, '2'),
           Card(HEART, '2'),
           Card(HEART, '4'),
           Card(HEART, '5'),
           Card(HEART, '7')]),
     "pair of deuces"
    ),
    (Hand([Card(SPADE, 'A'),
           Card(HEART, '6'),
           Card(HEART, 'K'),
           Card(HEART, 'Q'),
           Card(SPADE, '6')]),
     "pair of sixes"
    ),
    (Hand([Card(SPADE, '2'),
           Card(HEART, '6'),
           Card(HEART, '2'),
           Card(HEART, 'A'),
           Card(SPADE, '6')]),
     "two pair, sixes and deuces"
    ),
    (Hand([Card(SPADE, 'J'),
           Card(HEART, 'A'),
           Card(HEART, 'J'),
           Card(HEART, 'Q'),
           Card(SPADE, 'A')]),
     "two pair, aces and jacks"
    ),
    (Hand([Card(SPADE, 'A'),
           Card(SPADE, '2'),
           Card(HEART, 'K'),
           Card(HEART, '2'),
           Card(SPADE, 'K')]),
     "two pair, kings and deuces"
    ),
    (Hand([Card(SPADE, 'A'),
           Card(HEART, '3'),
           Card(HEART, 'K'),
           Card(SPADE, '3'),
           Card(CLUB,  '3')]),
     "three of a kind, threes"
    ),
    (Hand([Card(SPADE, '8'),
           Card(HEART, 'K'),
           Card(HEART, '8'),
           Card(CLUB,  '8'),
           Card(HEART, 'A')]),
     "three of a kind, eights"
    ),
    (Hand([Card(SPADE, 'Q'),
           Card(HEART, '6'),
           Card(HEART, 'K'),
           Card(HEART, 'Q'),
           Card(CLUB,  'Q')]),
     "three of a kind, queens"
    ),
    (Hand([Card(SPADE, 'A'),
           Card(HEART, '3'),
           Card(HEART, '5'),
           Card(CLUB,  '4'),
           Card(HEART, '2')]),
     "five-high straight"
    ),
    (Hand([Card(SPADE, '8'),
           Card(HEART, '6'),
           Card(HEART, '9'),
           Card(HEART, '5'),
           Card(CLUB,  '7')]),
     "nine-high straight"
    ),
    (Hand([Card(SPADE, 'Q'),
           Card(HEART, 'K'),
           Card(HEART, '10'),
           Card(HEART, 'J'),
           Card(HEART, 'A')]),
     "ace-high straight"
    ),
    (Hand([Card(HEART, '2'),
           Card(HEART, '3'),
           Card(HEART, '4'),
           Card(HEART, '5'),
           Card(HEART, '7')]),
     "seven-high flush"
    ),
    (Hand([Card(SPADE, '4'),
           Card(SPADE, '7'),
           Card(SPADE, '6'),
           Card(SPADE, '9'),
           Card(SPADE, '2')]),
     "nine-high flush"
    ),
    (Hand([Card(DIAMOND, 'J'),
           Card(DIAMOND, '10'),
           Card(DIAMOND, '4'),
           Card(DIAMOND, '3'),
           Card(DIAMOND, '2')]),
     "jack-high flush"
    ),
    (Hand([Card(CLUB, 'A'),
           Card(CLUB, '2'),
           Card(CLUB, '3'),
           Card(CLUB, '4'),
           Card(CLUB, '6')]),
     "ace-high flush"
    ),
    (Hand([Card(CLUB, 'A'),
           Card(CLUB, '2'),
           Card(CLUB, '3'),
           Card(CLUB, '4'),
           Card(CLUB, '6')]),
     "ace-high flush"
    ),
    (Hand([Card(CLUB,  '10'),
           Card(CLUB,  '2'),
           Card(SPADE, '2'),
           Card(HEART, '2'),
           Card(SPADE, '10')]),
     "full house, deuces over tens"
    ),
    (Hand([Card(CLUB,  '10'),
           Card(CLUB,  '2'),
           Card(SPADE, '2'),
           Card(HEART, '10'),
           Card(SPADE, '10')]),
     "full house, tens over deuces"
    ),
    (Hand([Card(CLUB,    '4'),
           Card(CLUB,    'A'),
           Card(SPADE,   '4'),
           Card(HEART,   '4'),
           Card(DIAMOND, '4')]),
     "four of a kind, fours"
    ),
    (Hand([Card(CLUB, 'A'),
           Card(CLUB, '2'),
           Card(CLUB, '3'),
           Card(CLUB, '4'),
           Card(CLUB, '5')]),
     "five-high straight flush"
    ),
    (Hand([Card(SPADE, '6'),
           Card(SPADE, '2'),
           Card(SPADE, '3'),
           Card(SPADE, '4'),
           Card(SPADE, '5')]),
     "six-high straight flush"
    ),
    (Hand([Card(DIAMOND, '9'),
           Card(DIAMOND, '8'),
           Card(DIAMOND, '10'),
           Card(DIAMOND, '7'),
           Card(DIAMOND, '6')]),
     "ten-high straight flush"
    ),
    (Hand([Card(HEART, 'K'),
           Card(HEART, 'Q'),
           Card(HEART, '10'),
           Card(HEART, 'J'),
           Card(HEART, '9')]),
     "king-high straight flush"
    ),
    (Hand([Card(HEART, 'K'),
           Card(HEART, 'Q'),
           Card(HEART, '10'),
           Card(HEART, 'J'),
           Card(HEART, 'A')]),
     "royal flush"
    ),
])
