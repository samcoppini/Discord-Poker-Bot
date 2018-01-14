import asyncio
from enum import Enum
from typing import Dict
import os

import discord

from poker import *

DEFAULT_STARTING_BALANCE = 500
DEFAULT_STARTING_BLIND = 5

POKER_BOT_TOKEN = os.getenv("POKER_BOT_TOKEN")
GAME_OPTIONS = {
    "blind":  "The current price of the little blind",
    "buy-in": "The amount of money all players start out with",
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

    def pay_blind(self, amount: int) -> int:
        self.cur_bet = min(self.balance, amount)
        self.balance -= self.cur_bet
        return self.cur_bet

    def call(self, amount: int) -> int:
        new_bet = amount - self.cur_bet
        new_bet = min(new_bet, self.balance)
        self.balance -= new_bet
        self.cur_bet += new_bet
        return new_bet

# A class that keeps track of all the information having to do with a game
class Game:
    def __init__(self) -> None:
        self.new_game()

    def new_game(self) -> None:
        self.state = GameState.NO_GAME
        # The players participating in the game
        self.players: List[Player] = []
        # The players participating in the current hand
        self.in_hand: List[Player] = []
        # The players that are all in
        self.all_in: List[Player] = []
        # The index of the current dealer
        self.dealer_index = 0
        # The index of the first person to bet this round
        self.first_bettor = 0
        # The deck that we're dealing from
        self.cur_deck: Deck = None
        # The five cards shared by all players
        self.shared_cards: List[Card] = []
        # The current amount that needs to be bet to go to the next round
        self.cur_bet = 0
        # The amount of money in the pot
        self.pot = 0
        # The index of the player whose turn it is
        self.turn_index = -1
        # Options that can be set by the players
        self.options = {
            "blind":  DEFAULT_STARTING_BLIND,
            "buy-in": DEFAULT_STARTING_BALANCE
        }

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

    # Returns whether a user is involved in the current hand
    def is_playing(self, user: discord.User) -> bool:
        for player in self.in_hand:
            if player.user == user:
                return True
        return False

    # Returns some messages to update the players on the state of the game
    def status_between_rounds(self) -> List[str]:
        messages = []
        for player in self.players:
            messages.append(f'{player.user.name} has ${player.balance} left.')
        messages.append(f"{self.dealer.user.name} is the current dealer. Message !deal to deal when you're ready.")
        return messages

    # Moves on to the next dealer
    def next_dealer(self) -> None:
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    # Returns the current dealer
    @property
    def dealer(self) -> Player:
        return self.players[self.dealer_index]

    # Returns the player who is paying the big blind
    @property
    def big_blind(self) -> Player:
        return self.players[self.dealer_index - 1]

    # Returns the player who is paying the little blind
    @property
    def little_blind(self) -> Player:
        return self.players[self.dealer_index - 2]

    # Returns player who is next to move
    @property
    def current_player(self) -> Player:
        return self.in_hand[self.turn_index]

    # Starts a new game, returning the messages to tell the channel
    def start(self) -> List[str]:
        self.state = GameState.NO_HANDS
        self.dealer_index = 0
        for player in self.players:
            player.balance = self.options["buy-in"]
        return ["The game has begun!"] + self.status_between_rounds()

    # Starts a new round of Hold'em, dealing two cards to each player, and return
    # the messages to tell the channel
    def deal_hands(self) -> List[str]:
        # Shuffles a new deck of cards
        self.cur_deck = Deck()

        # Start out the list of players that are all-in as empty
        self.all_in = []

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

        # Set the pot to be currently empty
        self.pot = 0

        # Take care of the blinds, if the blinds are higher than zero
        blind = self.options["blind"]
        self.cur_bet = blind * 2
        if blind > 0:
            self.pot += self.little_blind.pay_blind(blind)
            self.pot += self.big_blind.pay_blind(blind * 2)

            self.first_bettor = self.dealer_index
            self.turn_index = self.first_bettor
            messages.append(f"{self.little_blind.user.name} has paid the little blind of ${blind}.")
            messages.append(f"{self.big_blind.user.name} has paid the big blind of ${blind * 2}.")

        return messages + self.cur_options()

    # Returns messages telling the current player of the options available to them
    def cur_options(self) -> List[str]:
        messages = [f"It is {self.current_player.user.name}'s turn. {self.current_player.user.name} currently has ${self.current_player.balance}. The pot is currently ${self.pot}."]
        if self.cur_bet > 0:
            messages.append(f"The current bet to meet is ${self.cur_bet}, and {self.current_player.user.name} has bet ${self.current_player.cur_bet}.")
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
        for player in self.players:
            player.placed_bet = False
            player.cur_bet = 0
        self.cur_bet = 0
        self.turn_index = self.first_bettor
        return messages + self.cur_options()

    # Finish a player's turn, advancing to either the next player who needs to
    # bet, the next round of betting, or to the showdown
    def next_turn(self) -> List[str]:
        # If everyone is all in, instead of having a next turn, we have a showdown
        do_showdown = (len(self.in_hand) == 0)

        if not do_showdown:
            self.turn_index = (self.turn_index + 1) % len(self.in_hand)
            # If the current player has already bet, and that bet matches the
            # current bet, we can go on to the next round
            if self.cur_bet == self.current_player.cur_bet and self.current_player.placed_bet:
                if len(self.in_hand) == 1:
                    # If everyone but one person is all in, and that person
                    # matched the previous bets, we have the showdown
                    do_showdown = True
                else:
                    # Otherwise, we go to the next round
                    return self.next_round()

        if do_showdown:
            # If there's less than five shared cards currently dealt, we deal
            # the rest of them now
            while len(self.shared_cards) < 5:
                self.shared_cards.append(self.cur_deck.draw())
            self.in_hand += self.all_in
            return self.showdown()

        return self.cur_options()

    # Reveals the players' hands, and rewards the pot to the winner(s)
    def showdown(self) -> List[str]:
        messages = ["We have reached the end of betting. All cards will be revealed."]
        messages.append("  ".join(str(card) for card in self.shared_cards))

        # Go through the player's hands to determine the winner(s)
        winners: List[Player] = []
        best_hand: Hand = None
        for player in self.in_hand:
            # Let everyone know what the player had
            messages.append(f"{player.user.name}'s hand: {player.cards[0]}  {player.cards[1]}")

            # Get the best possible hand that can be made from the player's cards
            best_poss_hand = best_possible_hand(self.shared_cards, player.cards)
            if best_hand is None or best_poss_hand > best_hand:
                # If their hand beats the current winner, make them the sole
                # winner (so far)
                winners = [player]
                best_hand = best_poss_hand
            elif best_hand == best_poss_hand:
                # If their hand tied with the current winner, add them to
                # the winners list
                winners.append(player)

        if len(winners) == 1:
            messages.append(f"{winners[0].user.name} wins ${self.pot}!")
        else:
            messages.append(f"{' and '.join(winner.user.name for winner in winners)} each win ${self.pot // len(winners)}!")
        for winner in winners:
            winner.balance += self.pot // len(winners)

        # Go through the list of players, and knock out the ones that went all
        # in and lost
        i = 0
        while i < len(self.players):
            player = self.players[i]
            if player.balance == 0:
                messages.append(f"{player.user.name} has been knocked out of the game!")
                self.players.pop(i)
                if len(self.players) == 1:
                    # There's only one player, so they win
                    messages.append(f"{self.players[0].user.name} wins the game! Congratulations!")
                    self.state = GameState.NO_GAME
                    return messages
                if i < self.dealer_index:
                    self.dealer_index -= 1
            else:
                i += 1

        # Go on to the next round
        self.state = GameState.NO_HANDS
        self.next_dealer()
        messages += self.status_between_rounds()
        return messages

    # Make the current player check, betting no additional money
    def check(self) -> List[str]:
        self.current_player.placed_bet = True
        return [f"{self.current_player.user.name} checks."] + self.next_turn()

    # Has the current player raise a certain amount
    def raise_bet(self, amount: int) -> List[str]:
        self.current_player.placed_bet = True
        self.cur_bet = amount
        return self.call()

    # Has the current player call the current bet
    def call(self) -> List[str]:
        messages: List[str] = []
        self.current_player.placed_bet = True
        self.pot += self.current_player.call(self.cur_bet)
        if self.current_player.balance == 0:
            messages.append(f"{self.current_player.user.name} is all in!")
            self.all_in.append(self.current_player)
            self.in_hand.pop(self.turn_index)
            self.turn_index -= 1
        return messages + self.next_turn()

    # Has the current player fold their hand
    def fold(self) -> List[str]:
        messages = [f"{self.current_player.user.name} has folded."]
        self.in_hand.pop(self.turn_index)

        # Adjust the index of the first person to bet and the index of the
        # current player, depending on the index of the player who just folded
        if self.turn_index < self.first_bettor:
            self.first_bettor -= 1
        if self.first_bettor >= len(self.in_hand):
            self.first_bettor = 0
        if self.turn_index >= len(self.in_hand):
            self.turn_index = 0

        if len(self.in_hand) <= 1:
            # If everyone's folded except one person, give them the pot instantly
            if len(self.all_in) == 0 or (len(self.all_in) == 1 and len(self.in_hand) == 0):
                winner = self.in_hand[0] if self.in_hand else self.all_in[0]
                messages.append(f"{winner.user.name} wins ${self.pot}!")
                winner.balance += self.pot
                self.state = GameState.NO_HANDS
                self.next_dealer()
                return messages + self.status_between_rounds()
            # If we've reached a point where no one can bet more, we have the
            # showdown instantly
            elif self.current_player.cur_bet == self.cur_bet:
                while len(self.shared_cards) < 5:
                    self.shared_cards.append(self.cur_deck.draw())
                self.in_hand += self.all_in
                return self.showdown()

        # If we've reached this point, we're still playing the game, so go on
        # to the next player
        self.turn_index -= 1
        return messages + self.next_turn()

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
    elif not game.is_playing(message.author):
        return [f"You can't call {message.author.name}, because you've folded already."]
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
    elif not game.is_playing(message.author):
        return [f"You can't check {message.author.name}, because you've folded already."]
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
    elif not game.is_playing(message.author):
        return [f"You can't raise {message.author.name}, because you've folded already."]
    elif game.current_player.user != message.author:
        return [f"You can't raise, {message.author.name}, because it's {game.current_player.user.name}'s turn."]
    tokens = message.content.split()
    if len(tokens) < 2:
        return [f"Please follow !raise with the amount that you'd like to raise it to."]
    try:
        amount = int(tokens[1])
        if amount <= game.cur_bet:
            return [f"You can't raise to ${amount} because it is not larger than the current bet, ${game.cur_bet}"]
        elif amount > game.current_player.balance + game.current_player.cur_bet:
            return [f"You don't have enough money to raise to ${amount}.",
                    f"The most you can raise it to is ${game.current_player.cur_bet + game.current_player.balance}."]
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
    elif not game.is_playing(message.author):
        return [f"You've already folded, {message.author.name}. You can't fold twice."]
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
        option_lines.append(option + name_spaces + str(game.options[option]) + val_spaces + GAME_OPTIONS[option])
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
        game.options[tokens[1]] = val
        return [f"The {tokens[1]} is now set to {tokens[2]}."]
    except ValueError:
        return [f"{tokens[1]} must be set to an integer, and '{tokens[2]}' is not a valid integer."]

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
}

@client.event
async def on_ready():
    print("Poker bot ready!")

@client.event
async def on_message(message):
    if message.author == client.user or len(message.content.split()) == 0:
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
