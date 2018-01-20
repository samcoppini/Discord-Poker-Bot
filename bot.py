import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Set, Tuple
import os

import discord

from poker import Card, Deck, Hand, best_possible_hand

POKER_BOT_TOKEN = os.getenv("POKER_BOT_TOKEN")

class Option:
    def __init__(self, desc, default):
        self.description = desc
        self.default = default

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

# A class for representing one pot or side pot
class Pot:
    def __init__(self, players: Set[Player]) -> None:
        # The players that have contributed to this pot and can win it
        self.players = players
        # The bet that needs to be made to join this pot (in addition to the
        # bets of the lower pots)
        self.cur_bet = 0
        # The amount of money accumulated in this pot
        self.amount = 0
        if len(players) > 0:
            # The maximum bet that can be held by this pot before it needs a side pot
            self.max_bet = min(player.max_bet for player in players)
        else:
            # It might be possible to raise the bet beyond what any players can
            # pay if the blinds raise high enough. If so, this pot should never
            # be reached by any players, so we set the max bet extremely high
            # to hopefully prevent accidental creation of another side pot
            self.max_bet = 10000000000000000000000000000

    # Returns which players win this pot, based on the given community cards
    def get_winners(self, shared_cards: List[Card]) -> List[Player]:
        winners: List[Player] = []
        best_hand: Hand = None
        for player in self.players:
            hand = best_possible_hand(shared_cards, player.cards)
            if best_hand is None or hand > best_hand:
                winners = [player]
                best_hand = hand
            elif hand == best_hand:
                winners.append(player)
        return winners

    # Returns a new side pot, for when the bet overflows what can be contained
    # in this pot
    def make_side_pot(self):
        excluded = {player for player in self.players
                    if player.max_bet == self.max_bet}
        return Pot(self.players - excluded)

# A class to manage pots and side pots and who is in each pot and how much
# each player has bet so far
class PotManager:
    def __init__(self):
        # List of side pots in the game
        # If nobody's all-in, there should only be one pot
        # Higher-priced pots are towards the end of the list
        self.pots: List[Pot] = []

    # Resets the list of pots for a new hand
    def new_hand(self, players: List[Player]) -> None:
        self.pots = [Pot(set(players))]

    # Returns the current bet to be matched
    @property
    def cur_bet(self) -> int:
        return sum(pot.cur_bet for pot in self.pots)

    # Returns the amount of money that's in all the pots and side pots
    @property
    def value(self) -> int:
        return sum(pot.amount for pot in self.pots)

    # Increases the current bet to a new given amount
    def increase_bet(self, new_amount: int) -> None:
        accumulated_bet = 0
        while self.pots[-1].max_bet < new_amount:
            self.pots[-1].cur_bet = self.pots[-1].max_bet - accumulated_bet
            accumulated_bet += self.pots[-1].cur_bet
            self.pots.append(self.pots[-1].make_side_pot())
        self.pots[-1].cur_bet = min(self.pots[-1].max_bet, new_amount) - accumulated_bet

    # Returns all the players that are in the pot
    def in_pot(self) -> Set[Player]:
        return self.pots[0].players

    def debug_print(self):
        for i, pot in enumerate(self.pots):
            print(f"Pot #{i}. Bet: ${pot.cur_bet} (Max: {pot.max_bet}). Amount: ${pot.amount}.")
            for player in pot.players:
                print(f"{player.name}: {player.balance}")
            print("-----")

    # Handles a player folding, removing them from every pot that they're
    # eligible for
    def handle_fold(self, player: Player) -> None:
        for pot in self.pots:
            if player in pot.players:
                pot.players.remove(player)

    # Handles a player calling the current bet
    def handle_call(self, player: Player) -> None:
        new_amount = player.bet(min(player.max_bet, self.cur_bet))
        old_bet = player.cur_bet - new_amount
        pot_index = 0
        while new_amount > 0:
            cur_pot = self.pots[pot_index]
            old_bet -= cur_pot.cur_bet
            if old_bet < 0:
                cur_pot.amount -= old_bet
                new_amount += old_bet
                old_bet = 0
            pot_index += 1
        player.placed_bet = True

    # Handles a player raising the current bet to a given amount
    def handle_raise(self, player: Player, new_amount: int) -> None:
        self.increase_bet(self.cur_bet + new_amount)
        self.handle_call(player)

    # Pays the initial blinds for the player, returning whether they were forced
    # all-in by the blind
    def pay_blind(self, player: Player, blind: int) -> bool:
        self.increase_bet(blind)
        self.handle_call(player)
        player.placed_bet = False
        return player.balance == 0

    # Returns whether the betting round is over, which is where every player
    # who can bet has made a bet and have matched the same bet
    def round_over(self) -> bool:
        if self.betting_over():
            return True
        for player in self.pots[0].players:
            if player.balance == 0:
                continue
            elif not player.placed_bet or player.cur_bet < self.cur_bet:
                return False
        return True

    # Returns whether all betting is over, if all but one player has folded or
    # has gone all-in
    def betting_over(self) -> bool:
        players_left_betting = False
        for player in self.pots[0].players:
            if player.balance > 0:
                if players_left_betting or not player.placed_bet:
                    return False
                if player.cur_bet < self.cur_bet:
                    return False
                players_left_betting = True
        return True

    # Returns the winners of the pot, and the amounts that they won
    def get_winners(self, shared_cards: List[Card]) -> Dict[Player, int]:
        winners: Dict[Player, int] = {}
        for pot in self.pots:
            pot_winners = pot.get_winners(shared_cards)
            if len(pot_winners) == 0:
                continue
            pot_won = pot.amount // len(pot_winners)
            if pot_won > 0:
                for winner in pot_winners:
                    winners.setdefault(winner, 0)
                    winners[winner] += pot_won
        return winners

    # Advances to the next round of betting
    def next_round(self) -> None:
        for pot in self.pots:
            pot.cur_bet = 0
            pot.max_bet = 0
        for player in self.pots[-1].players:
            player.placed_bet = False
            player.cur_bet = 0
        self.pots[-1].max_bet = min(player.max_bet for player in self.pots[-1].players)

# A class that keeps track of all the information having to do with a game
class Game:
    def __init__(self) -> None:
        self.new_game()
        # Set the game options to the defaults
        self.options = {key: value.default for key, value in GAME_OPTIONS.items()}

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

    # Adds a new player to the game, and returns if they weren't already playing
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
        messages.append(f"{self.dealer.user.name} is the current dealer. Message !deal to deal when you're ready.")
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

    # Starts a new round of Hold'em, dealing two cards to each player, and return
    # the messages to tell the channel
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
            messages.append("Blinds are being doubled this round!")
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
            self.first_bettor = self.dealer_index + 1
        else:
            # In heads-up games, who plays the blinds is different, with the
            # dealer playing the small blind and the other player paying the big
            small_player = self.players[self.dealer_index]
            big_player = self.players[self.dealer_index - 1]
            # Dealer goes first pre-flop, the other player goes first afterwards
            self.turn_index = self.dealer_index
            self.first_bettor = self.dealer_index - 1

        messages.append(f"{small_player.name} has paid the small blind of ${blind}.")
        if self.pot.pay_blind(small_player, blind):
            messages.append(f"{small_player.name} is all in!")
            self.leave_hand(small_player)

        messages.append(f"{big_player.name} has paid the big blind of ${blind * 2}.")
        if self.pot.pay_blind(big_player, blind * 2):
            messages.append(f"{big_player.name} is all in!")
            self.leave_hand(big_player)

        return messages

    # Returns messages telling the current player of the options available to them
    def cur_options(self) -> List[str]:
        messages = [f"It is {self.current_player.name}'s turn. {self.current_player.user.name} currently has ${self.current_player.balance}. The pot is currently ${self.pot.value}."]
        if self.pot.cur_bet > 0:
            messages.append(f"The current bet to meet is ${self.cur_bet}, and {self.current_player.name} has bet ${self.current_player.cur_bet}.")
        else:
            messages.append(f"The current bet to meet is ${self.cur_bet}.")
        if self.current_player.cur_bet == self.cur_bet:
            messages.append("Message !check, !raise or !fold.")
        else:
            messages.append("Message !call, !raise or !fold.")
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

        messages = ["We have reached the end of betting. All cards will be revealed."]

        messages.append("  ".join(str(card) for card in self.shared_cards))

        for player in self.pot.in_pot():
            messages.append(f"{player.name}'s hand: {player.cards[0]}  {player.cards[1]}")

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
                    messages.append(f"{self.players[0].user.name} wins the game! Congratulations!")
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
    async def tell_hands(self):
        for player in self.players:
            await client.send_message(player.user, '  '.join(str(card) for card in player.cards))

client = discord.Client()
games: Dict[discord.Channel, Game] = {}

def new_game(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        game.new_game()
        game.add_player(message.author)
        game.state = GameState.WAITING
        return [f"A new game has been started by {message.author.name}!",
                 "Message !join to join the game."]
    else:
        messages = ["There is already a game in progress, you can't start a new game."]
        if game.state == GameState.WAITING:
            messages.append("It still hasn't started yet, so you can still message !join to join that game.")
        return messages

def join_game(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet for you to join.",
                "Message !newgame to start a new game."]
    elif game.state != GameState.WAITING:
        return [f"The game is already in progress, {message.author.name}.",
                 "You're not allowed to join right now."]
    elif game.add_player(message.author):
        return [f"{message.author.name} has joined the game!",
                 "Message !join to join the game, or !start to start the game."]
    else:
        return [f"You've already joined the game {message.author.name}!"]

def start_game(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["Message !newgame if you would like to start a new game."]
    elif game.state != GameState.WAITING:
        return [f"The game has already started, {message.author.name}.",
                 "It can't be started twice."]
    elif not game.is_player(message.author):
        return [f"You are not a part of that game yet, {message.author.name}.",
                 "Please message !join if you are interested in playing."]
    elif len(game.players) < 2:
        return ["The game must have at least two players before it can be started."]
    else:
        return game.start()

def deal_hand(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started for you to deal. Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't deal because the game hasn't started yet."]
    elif game.state != GameState.NO_HANDS:
        return ["The cards have already been dealt."]
    elif game.dealer.user != message.author:
        return [f"You aren't the dealer {message.author.name}, so don't try to deal.",
                f"Please wait for {game.dealer.user.name} to !deal."]
    else:
        return game.deal_hands()

def call_bet(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet. Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't call any bets because the game hasn't started yet."]
    elif not game.is_player(message.author):
        return [f"You can't call, because you're not playing {message.author.name}."]
    elif game.state == GameState.NO_HANDS:
        return ["You can't call any bets because the hands haven't been dealt yet."]
    elif game.current_player.user != message.author:
        return [f"You can't call {message.author.name}, because it's {game.current_player.user.name}'s turn."]
    else:
        return game.call()

def check(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet. Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't check because the game hasn't started yet."]
    elif not game.is_player(message.author):
        return [f"You can't check, because you're not playing {message.author.name}."]
    elif game.state == GameState.NO_HANDS:
        return ["You can't check because the hands haven't been dealt yet."]
    elif game.current_player.user != message.author:
        return [f"You can't check, {message.author.name}, because it's {game.current_player.user.name}'s turn."]
    elif game.current_player.cur_bet != game.cur_bet:
        return [f"You can't check, {message.author.name} because you need to put in ${game.cur_bet - game.current_player.cur_bet} to call."]
    else:
        return game.check()

def raise_bet(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet. Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't raise because the game hasn't started yet."]
    elif not game.is_player(message.author):
        return [f"You can't raise, because you're not playing {message.author.name}."]
    elif game.state == GameState.NO_HANDS:
        return ["You can't raise because the hands haven't been dealt yet."]
    elif game.current_player.user != message.author:
        return [f"You can't raise, {message.author.name}, because it's {game.current_player.user.name}'s turn."]
    tokens = message.content.split()
    if len(tokens) < 2:
        return [f"Please follow !raise with the amount that you'd like to raise it by."]
    try:
        amount = int(tokens[1])
        if game.cur_bet >= game.current_player.max_bet:
            return [f"You don't have enough money to raise the current bet of ${game.cur_bet}."]
        elif game.cur_bet + amount > game.current_player.max_bet:
            return [f"You don't have enough money to raise by ${amount}.",
                    f"The most you can raise it by is ${game.current_player.cur_bet + game.current_player.balance - game.cur_bet}."]
        return game.raise_bet(amount)
    except ValueError:
        return [f"Please follow !raise with an integer. '{tokens[1]}' is not an integer."]

def fold_hand(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet. Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't fold yet because the game hasn't started yet."]
    elif not game.is_player(message.author):
        return [f"You can't fold, because you're not playing {message.author.name}."]
    elif game.state == GameState.NO_HANDS:
        return ["You can't fold yet because the hands haven't been dealt yet."]
    elif game.current_player.user != message.author:
        return [f"You can't fold {message.author.name}, because it's {game.current_player.user.name}'s turn."]
    else:
        return game.fold()

def show_help(game: Game, message: discord.Message) -> List[str]:
    longest_command = len(max(commands, key=len))
    help_lines = []
    for command, info in sorted(commands.items()):
        spacing = ' ' * (longest_command - len(command) + 2)
        help_lines.append(command + spacing + info[0])
    return ['```' + '\n'.join(help_lines) + '```']

def show_options(game: Game, message: discord.Message) -> List[str]:
    longest_option = len(max(game.options, key=len))
    longest_value = max([len(str(val)) for key, val in game.options.items()])
    option_lines = []
    for option in GAME_OPTIONS:
        name_spaces = ' ' * (longest_option - len(option) + 2)
        val_spaces = ' ' * (longest_value - len(str(game.options[option])) + 2)
        option_lines.append(option + name_spaces + str(game.options[option]) + val_spaces + GAME_OPTIONS[option].description)
    return ['```' + '\n'.join(option_lines) + '```']

def set_option(game: Game, message: discord.Message) -> List[str]:
    tokens = message.content.split()
    if len(tokens) == 2:
        return ["You must specify a new value after the name of an option when using the !set command."]
    elif len(tokens) == 1:
        return ["You must specify an option and value to set when using the !set command."]
    elif tokens[1] not in GAME_OPTIONS:
        return [f"'{tokens[1]}' is not an option. Message !options to see the list of options."]
    try:
        val = int(tokens[2])
        if val < 0:
            return [f"Cannot set {tokens[1]} to a negative value!"]
        game.options[tokens[1]] = val
        return [f"The {tokens[1]} is now set to {tokens[2]}."]
    except ValueError:
        return [f"{tokens[1]} must be set to an integer, and '{tokens[2]}' is not a valid integer."]

def chip_count(game: Game, message: discord.Message) -> List[str]:
    if game.state in (GameState.NO_GAME, GameState.WAITING):
        return ["You can't request a chip count because no game has started yet."]
    return [f"{player.user.name} has ${player.balance}." for player in game.players]

commands = {
    '!newgame': ('Starts a new game, allowing players to join.',
                 new_game),
    '!join':    ('Lets you join a game that is about to begin',
                 join_game),
    '!start':   ('Begins a game after all players have joined',
                 start_game),
    '!deal':    ('Deals the hole cards to all the players',
                 deal_hand),
    '!call':    ('Matches the current bet',
                 call_bet),
    '!raise':   ('Increase the size of current bet',
                 raise_bet),
    '!check':   ('Bet no money',
                 check),
    '!fold':    ('Discard your hand and forfeit the pot',
                 fold_hand),
    '!help':    ('Show the list of commands',
                 show_help),
    '!options': ('Show the list of options and their current values',
                 show_options),
    '!set':     ('Set the value of an option',
                 set_option),
    '!count':   ('Shows how many chips each player has left',
                 chip_count),
}

@client.event
async def on_ready():
    print("Poker bot ready!")

@client.event
async def on_message(message):
    # Ignore messages sent by the bot itself
    if message.author == client.user:
        return
    # Ignore empty messages
    if len(message.content.split()) == 0:
        return
    # Ignore private messages
    if message.channel.is_private:
        return

    command = message.content.split()[0]
    if command[0] == '!':
        if command not in commands:
            await client.send_message(message.channel, f"{message.content} is not a valid command. Message !help to see the list of commands.")
            return
        game = games.setdefault(message.channel, Game())
        messages = commands[command][1](game, message)
        if command == '!deal' and messages[0] == 'The hands have been dealt!':
            await game.tell_hands()
        await client.send_message(message.channel, '\n'.join(messages))

client.run(POKER_BOT_TOKEN)
