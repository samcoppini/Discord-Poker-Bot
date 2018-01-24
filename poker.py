from collections import namedtuple
from enum import Enum
from functools import total_ordering
from itertools import combinations
from typing import List, Tuple
import random

SUITS = ('♠', '♥', '♦', '♣')

RankInfo = namedtuple('RankInfo', ['name', 'plural', 'value'])

RANK_INFO = {
    "2":  RankInfo("deuce", "deuces", 0),
    "3":  RankInfo("three", "threes", 1),
    "4":  RankInfo("four",  "fours",  2),
    "5":  RankInfo("five",  "fives",  3),
    "6":  RankInfo("six",   "sixes",  4),
    "7":  RankInfo("seven", "sevens", 5),
    "8":  RankInfo("eight", "eights", 6),
    "9":  RankInfo("nine",  "nines",  7),
    "10": RankInfo("ten",   "tens",   8),
    "J":  RankInfo("jack",  "jacks",  9),
    "Q":  RankInfo("queen", "queens", 10),
    "K":  RankInfo("king",  "kings",  11),
    "A":  RankInfo("ace",   "aces",   12),
}

# An enumeration for ranking poker hands
@total_ordering
class HandRanking(Enum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_KIND = 8
    STRAIGHT_FLUSH = 9
    # Royal flush is just a special case of the straight flush

    def __lt__(self, other):
        return self.value < other.value

# A simple class representing a card
@total_ordering
class Card:
    def __init__(self, suit: str, rank: str) -> None:
        self.suit = suit
        self.rank = rank

    # When comparing two cards, suit doesn't matter, just the rank of the card
    def __lt__(self, other):
        return RANK_INFO[self.rank].value < RANK_INFO[other.rank].value

    def __eq__(self, other):
        return self.rank == other.rank

    def __str__(self) -> str:
        return self.suit + self.rank

    @property
    def name(self) -> str:
        return RANK_INFO[self.rank].name

    @property
    def plural(self) -> str:
        return RANK_INFO[self.rank].plural

# A class for representing a 5-card hand, and allowing for the easy comparison
# of hands
@total_ordering
class Hand:
    def __init__(self, cards: List[Card]) -> None:
        # Sort the cards first thing to make hands easier to compare
        self.cards = sorted(cards)

        # Gets a list of the duplicated cards (pairs, three-of-a-kinds, etc)
        dups = self.get_dups()

        # At this point, we determine the ranking of the hand
        if self.is_flush():
            if self.is_straight():
                self.rank = HandRanking.STRAIGHT_FLUSH
            else:
                self.rank = HandRanking.FLUSH
        elif self.is_straight():
            self.rank = HandRanking.STRAIGHT
        elif dups:
            if len(dups) == 2:
                if len(dups[1]) == 3:
                    self.rank = HandRanking.FULL_HOUSE
                else:
                    self.rank = HandRanking.TWO_PAIR
            else:
                if len(dups[0]) == 4:
                    self.rank = HandRanking.FOUR_OF_KIND
                elif len(dups[0]) == 3:
                    self.rank = HandRanking.THREE_OF_KIND
                else:
                    self.rank = HandRanking.PAIR
            self.rearrange_dups(dups)
        else:
            self.rank = HandRanking.HIGH_CARD

    def __lt__(self, other):
        if self.rank < other.rank:
            return True
        if self.rank > other.rank:
            return False
        for self_card, other_card in zip(self.cards[::-1], other.cards[::-1]):
            if self_card < other_card:
                return True
            elif self_card > other_card:
                return False
        return False

    def __eq__(self, other):
        if self.rank != other.rank:
            return False
        for self_card, other_card in zip(self.cards, other.cards):
            if self_card != other_card:
                return False
        return True

    def __str__(self):
        if self.rank == HandRanking.HIGH_CARD:
            return self.cards[4].name + " high"
        elif self.rank == HandRanking.PAIR:
            return "pair of " + self.cards[4].plural
        elif self.rank == HandRanking.TWO_PAIR:
            return "two pair, " + self.cards[4].plural + " and " + self.cards[2].plural
        elif self.rank == HandRanking.THREE_OF_KIND:
            return "three of a kind, " + self.cards[4].plural
        elif self.rank == HandRanking.STRAIGHT:
            return self.cards[4].name + "-high straight"
        elif self.rank == HandRanking.FLUSH:
            return self.cards[4].name + "-high flush"
        elif self.rank == HandRanking.FULL_HOUSE:
            return "full house, " + self.cards[4].plural + " over " + self.cards[1].plural
        elif self.rank == HandRanking.FOUR_OF_KIND:
            return "four of a kind, " + self.cards[4].plural
        elif self.rank == HandRanking.STRAIGHT_FLUSH:
            if self.cards[4].rank == 'A':
                return "royal flush"
            else:
                return self.cards[4].name + "-high straight flush"

    # Rearrange the duplicated cards in the hand so that comparing two hands
    # with the same ranking is easier
    # This moves duplicated cards to the end of the hand
    def rearrange_dups(self, dups: List[List[Card]]) -> None:
        flat_dups = [card for cards in dups for card in cards]
        for dup in flat_dups:
            self.cards.pop(self.cards.index(dup))
        self.cards += flat_dups

    # Returns whether the hand is a straight
    def is_straight(self) -> bool:
        ranks = [RANK_INFO[card.rank].value for card in self.cards]
        # Check to see if each card is exactly one better than the previous card
        for i in range(1, 5):
            if ranks[i - 1] != ranks[i] - 1:
                break
        else:
            # If we've reached this point, each card was exactly one rank
            # higher than the previous card.
            return True
        # Check for the special case of an ace-low straight
        if ranks == [0, 1, 2, 3, 12]:
            self.cards = [self.cards[-1]] + self.cards[:-1]
            return True
        return False

    # Returns whether a hand is a flush, meaning all the cards are the same suit
    def is_flush(self) -> bool:
        suit = self.cards[0].suit
        for card in self.cards[1:]:
            if card.suit != suit:
                return False
        return True

    # Returns a list of the pairs, three-of-a-kinds and four-of-a-kinds in the hand
    def get_dups(self) -> List[List[Card]]:
        dups: List[List[Card]] = []
        cur_dup: List[Card] = [self.cards[0]]
        for card in self.cards[1:]:
            if cur_dup[0] != card:
                if len(cur_dup) > 1:
                    dups.append(cur_dup)
                cur_dup = [card]
            else:
                cur_dup.append(card)
        if len(cur_dup) > 1:
            dups.append(cur_dup)
        # For full houses, make it so the three-of-a-kind is always second in
        # the list of duplicates
        if len(dups) == 2 and len(dups[0]) > len(dups[1]):
            dups[0], dups[1] = dups[1], dups[0]
        return dups

# Returns the best possible 5-card hand that can be made from the five
# community cards and a player's two hole cards
def best_possible_hand(public: List[Card], private: Tuple[Card, Card]) -> Hand:
    return max(Hand(list(hand))
               for hand in combinations(tuple(public) + private, 5))

# A class for representing a simple, randomized deck that can be drawn from
class Deck:
    def __init__(self):
        self.cards = [Card(suit, rank) for suit in SUITS
                                       for rank in RANK_INFO]
        random.shuffle(self.cards)

    def draw(self) -> Card:
        return self.cards.pop()
