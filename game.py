from collections import namedtuple
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List

import discord

from player import Player
from poker import best_possible_hand, Card, Deck
from pot import PotManager

Option = namedtuple("Option", ["description", "default"])

GAME_OPTIONS: Dict[str, Option] = {
    "blind":  Option("The current price of the small blind", 5),
    "buy-in": Option("The amount of money all players start out with", 500),
    "raise-delay": Option("The number of minutes before blinds double",  30),
    "starting-blind": Option("The starting price of the small blind", 5)
}

# An enumeration that says what stage of the game we've reached
class GameState(Enum):
    # Game hasn't started yet
    NO_GAME = 1
    # A game has started, and we're waiting for players to join
    WAITING = 2
    # Everyone's joined, we're waiting for the hands to be dealt
    NO_HANDS = 3
    # We've dealt hands to everyone, they're making their bets
    HANDS_DEALT = 4
    # We've just dealt the flop
    FLOP_DEALT = 5
    # We just dealt the turn
    TURN_DEALT = 6
    # We just dealt the river
    RIVER_DEALT = 7

# A class that keeps track of all the information having to do with a game
class Game:
    def __init__(self) -> None:
        self.new_game()
        # Set the game options to the defaults
        self.options = {key: value.default
                        for key, value in GAME_OPTIONS.items()}

    def new_game(self) -> None:
        self.state = GameState.NO_GAME
        # The players participating in the game
        self.players: List[Player] = []
        # The players participating in the current hand
        self.in_hand: List[Player] = []
        # The index of the current dealer
        self.dealer_index = 0
        # The index of the first person to bet in the post-flop rounds
        self.first_bettor = 0
        # The deck that we're dealing from
        self.cur_deck: Deck = None
        # The five cards shared by all players
        self.shared_cards: List[Card] = []
        # Used to keep track of the current value of the pot, and who's in it
        self.pot = PotManager()
        # The index of the player in in_hand whose turn it is
        self.turn_index = -1
        # The last time that the blinds were automatically raised
        self.last_raise: datetime = None

    # Adds a new player to the game, returning if they weren't already playing
    def add_player(self, user: discord.User) -> bool:
        if self.is_player(user):
            return False
        self.players.append(Player(user))
        return True

    # Returns whether a user is playing in the game
    def is_player(self, user: discord.User) -> bool:
        for player in self.players:
            if player.user == user:
                return True
        return False

    # Removes a player from being able to bet, if they folded or went all in
    def leave_hand(self, to_remove: Player) -> None:
        for i, player in enumerate(self.in_hand):
            if player == to_remove:
                index = i
                break
        else:
            # The player who we're removing isn't in the hand, so just
            # return
            return

        self.in_hand.pop(index)

        # Adjust the index of the first person to bet and the index of the
        # current player, depending on the index of the player who just folded
        if index < self.first_bettor:
            self.first_bettor -= 1
        if self.first_bettor >= len(self.in_hand):
            self.first_bettor = 0
        if self.turn_index >= len(self.in_hand):
            self.turn_index = 0

    # Returns some messages to update the players on the state of the game
    def status_between_rounds(self) -> List[str]:
        messages = []
        for player in self.players:
            messages.append(f"{player.user.name} has ${player.balance}.")
        messages.append(f"{self.dealer.user.name} is the current dealer. "
                        "Message !deal to deal when you're ready.")
        return messages

    # Moves on to the next dealer
    def next_dealer(self) -> None:
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    # Returns the current dealer
    @property
    def dealer(self) -> Player:
        return self.players[self.dealer_index]

    @property
    def cur_bet(self) -> int:
        return self.pot.cur_bet

    # Returns the player who is next to move
    @property
    def current_player(self) -> Player:
        return self.in_hand[self.turn_index]

    # Starts a new game, returning the messages to tell the channel
    def start(self) -> List[str]:
        self.state = GameState.NO_HANDS
        self.dealer_index = 0
        for player in self.players:
            player.balance = self.options["buy-in"]
        # Reset the blind to be the starting blind value
        self.options["blind"] = self.options["starting-blind"]
        return ["The game has begun!"] + self.status_between_rounds()

    # Starts a new round of Hold'em, dealing two cards to each player, and
    # return the messages to tell the channel
    def deal_hands(self) -> List[str]:
        # Shuffles a new deck of cards
        self.cur_deck = Deck()

        # Start out the shared cards as being empty
        self.shared_cards = []

        # Deals hands to each player, setting their initial bets to zero and
        # adding them as being in on the hand
        self.in_hand = []
        for player in self.players:
            player.cards = (self.cur_deck.draw(), self.cur_deck.draw())
            player.cur_bet = 0
            player.placed_bet = False
            self.in_hand.append(player)

        self.state = GameState.HANDS_DEALT
        messages = ["The hands have been dealt!"]

        # Reset the pot for the new hand
        self.pot.new_hand(self.players)

        if self.options["blind"] > 0:
            messages += self.pay_blinds()

        self.turn_index -= 1
        return messages + self.next_turn()

    # Makes the blinds players pay up with their initial bets
    def pay_blinds(self) -> List[str]:
        messages: List[str] = []

        # See if we need to raise the blinds or not
        raise_delay = self.options["raise-delay"]
        if raise_delay == 0:
            # If the raise delay is set to zero, consider it as being turned
            # off, and do nothing for blinds raises
            self.last_raise = None
        elif self.last_raise is None:
            # Start the timer, if it hasn't been started yet
            self.last_raise = datetime.now()
        elif datetime.now() - self.last_raise > timedelta(minutes=raise_delay):
            messages.append("**Blinds are being doubled this round!**")
            self.options["blind"] *= 2
            self.last_raise = datetime.now()

        blind = self.options["blind"]

        # Figure out the players that need to pay the blinds
        if len(self.players) > 2:
            small_player = self.players[(self.dealer_index + 1) % len(self.in_hand)]
            big_player = self.players[(self.dealer_index + 2) % len(self.in_hand)]
            # The first player to bet pre-flop is the player to the left of the big blind
            self.turn_index = (self.dealer_index + 3) % len(self.in_hand)
            # The first player to bet post-flop is the first player to the left of the dealer
            self.first_bettor = (self.dealer_index + 1) % len(self.players)
        else:
            # In heads-up games, who plays the blinds is different, with the
            # dealer playing the small blind and the other player paying the big
            small_player = self.players[self.dealer_index]
            big_player = self.players[self.dealer_index - 1]
            # Dealer goes first pre-flop, the other player goes first afterwards
            self.turn_index = self.dealer_index
            self.first_bettor = self.dealer_index - 1

        messages.append(f"{small_player.name} has paid the small blind "
                        f"of ${blind}.")

        if self.pot.pay_blind(small_player, blind):
            messages.append(f"{small_player.name} is all in!")
            self.leave_hand(small_player)

        messages.append(f"{big_player.name} has paid the big blind "
                        f"of ${blind * 2}.")
        if self.pot.pay_blind(big_player, blind * 2):
            messages.append(f"{big_player.name} is all in!")
            self.leave_hand(big_player)

        return messages

    # Returns messages telling the current player their options
    def cur_options(self) -> List[str]:
        messages = [f"It is {self.current_player.name}'s turn. "
                    f"{self.current_player.user.name} currently has "
                    f"${self.current_player.balance}. "
                    f"The pot is currently ${self.pot.value}."]
        if self.pot.cur_bet > 0:
            messages.append(f"The current bet to meet is ${self.cur_bet}, "
                            f"and {self.current_player.name} has bet "
                            f"${self.current_player.cur_bet}.")
        else:
            messages.append(f"The current bet to meet is ${self.cur_bet}.")
        if self.current_player.cur_bet == self.cur_bet:
            messages.append("Message !check, !raise or !fold.")
        elif self.current_player.max_bet > self.cur_bet:
            messages.append("Message !call, !raise or !fold.")
        else:
            messages.append("Message !all-in or !fold.")
        return messages

    # Advances to the next round of betting (or to the showdown), returning a
    # list messages to tell the players
    def next_round(self) -> List[str]:
        messages: List[str] = []
        if self.state == GameState.HANDS_DEALT:
            messages.append("Dealing the flop:")
            self.shared_cards.append(self.cur_deck.draw())
            self.shared_cards.append(self.cur_deck.draw())
            self.shared_cards.append(self.cur_deck.draw())
            self.state = GameState.FLOP_DEALT
        elif self.state == GameState.FLOP_DEALT:
            messages.append("Dealing the turn:")
            self.shared_cards.append(self.cur_deck.draw())
            self.state = GameState.TURN_DEALT
        elif self.state == GameState.TURN_DEALT:
            messages.append("Dealing the river:")
            self.shared_cards.append(self.cur_deck.draw())
            self.state = GameState.RIVER_DEALT
        elif self.state == GameState.RIVER_DEALT:
            return self.showdown()
        messages.append("  ".join(str(card) for card in self.shared_cards))
        self.pot.next_round()
        self.turn_index = self.first_bettor
        return messages + self.cur_options()

    # Finish a player's turn, advancing to either the next player who needs to
    # bet, the next round of betting, or to the showdown
    def next_turn(self) -> List[str]:
        if self.pot.round_over():
            if self.pot.betting_over():
                return self.showdown()
            else:
                return self.next_round()
        else:
            self.turn_index = (self.turn_index + 1) % len(self.in_hand)
            return self.cur_options()

    def showdown(self) -> List[str]:
        while len(self.shared_cards) < 5:
            self.shared_cards.append(self.cur_deck.draw())

        messages = ["We have reached the end of betting. "
                    "All cards will be revealed."]

        messages.append("  ".join(str(card) for card in self.shared_cards))

        for player in self.pot.in_pot():
            messages.append(f"{player.name}'s hand: "
                            f"{player.cards[0]}  {player.cards[1]}")

        winners = self.pot.get_winners(self.shared_cards)
        for winner, winnings in sorted(winners.items(), key=lambda item: item[1]):
            hand_name = str(best_possible_hand(self.shared_cards, winner.cards))
            messages.append(f"{winner.name} wins ${winnings} with a {hand_name}.")
            winner.balance += winnings

        # Remove players that went all in and lost
        i = 0
        while i < len(self.players):
            player = self.players[i]
            if player.balance > 0:
                i += 1
            else:
                messages.append(f"{player.name} has been knocked out of the game!")
                self.players.pop(i)
                if len(self.players) == 1:
                    # There's only one player, so they win
                    messages.append(f"{self.players[0].user.name} wins the game! "
                                    "Congratulations!")
                    self.state = GameState.NO_GAME
                    return messages
                if i <= self.dealer_index:
                    self.dealer_index -= 1

        # Go on to the next round
        self.state = GameState.NO_HANDS
        self.next_dealer()
        messages += self.status_between_rounds()
        return messages

    # Make the current player check, betting no additional money
    def check(self) -> List[str]:
        self.current_player.placed_bet = True
        return [f"{self.current_player.name} checks."] + self.next_turn()

    # Has the current player raise a certain amount
    def raise_bet(self, amount: int) -> List[str]:
        self.pot.handle_raise(self.current_player, amount)
        messages = [f"{self.current_player.name} raises by ${amount}."]
        if self.current_player.balance == 0:
            messages.append(f"{self.current_player.name} is all in!")
            self.leave_hand(self.current_player)
            self.turn_index -= 1
        return messages + self.next_turn()

    # Has the current player match the current bet
    def call(self) -> List[str]:
        self.pot.handle_call(self.current_player)
        messages = [f"{self.current_player.name} calls."]
        if self.current_player.balance == 0:
            messages.append(f"{self.current_player.name} is all in!")
            self.leave_hand(self.current_player)
            self.turn_index -= 1
        return messages + self.next_turn()

    def all_in(self) -> List[str]:
        if self.pot.cur_bet > self.current_player.max_bet:
            return self.call()
        else:
            return self.raise_bet(self.current_player.max_bet - self.cur_bet)

    # Has the current player fold their hand
    def fold(self) -> List[str]:
        messages = [f"{self.current_player.name} has folded."]
        self.pot.handle_fold(self.current_player)
        self.leave_hand(self.current_player)

        # If only one person is left in the pot, give it to them instantly
        if len(self.pot.in_pot()) == 1:
            winner = list(self.pot.in_pot())[0]
            messages += [f"{winner.name} wins ${self.pot.value}!"]
            winner.balance += self.pot.value
            self.state = GameState.NO_HANDS
            self.next_dealer()
            return messages + self.status_between_rounds()

        # If there's still betting to do, go on to the next turn
        if not self.pot.betting_over():
            self.turn_index -= 1
            return messages + self.next_turn()

        # Otherwise, have the showdown immediately
        return self.showdown()

    # Send a message to each player, telling them what their hole cards are
    async def tell_hands(self, client: discord.Client):
        for player in self.players:
            await client.send_message(player.user, str(player.cards[0]) + "  "
                                                   + str(player.cards[1]))
