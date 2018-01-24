from typing import Tuple

import discord

from poker import Card

# A class that contains information on an individual player
class Player:
    def __init__(self, user: discord.User) -> None:
        # How many chips the player has
        self.balance = 0
        # The discord user associated with the player
        self.user = user
        # The player's hole cards
        self.cards: Tuple[Card, Card] = None
        # How many chips the player has bet this round
        self.cur_bet = 0
        # Whether the player has placed a bet yet this round
        self.placed_bet = False

    @property
    def name(self) -> str:
        return self.user.name

    # The maximum bet that the player can match
    @property
    def max_bet(self) -> int:
        return self.cur_bet + self.balance

    # Increases the player's bet to match new_amount
    def bet(self, new_amount: int) -> int:
        money_lost = (new_amount - self.cur_bet)
        self.balance -= money_lost
        self.cur_bet = new_amount
        return money_lost

    def pay_blind(self, blind: int) -> int:
        self.cur_bet = min(self.balance, blind)
        self.balance -= self.cur_bet
        return self.cur_bet
