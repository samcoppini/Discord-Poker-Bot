import asyncio
from enum import Enum
import os

import discord

from poker import *

STARTING_BALANCE = 500

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

class Player:
    def __init__(self, user: discord.User) -> None:
        self.balance = STARTING_BALANCE
        self.user = user
        self.cards: Tuple[Card, Card] = None
        self.cur_bet = 0

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

class Game:
    def __init__(self) -> None:
        self.state = GameState.NO_GAME
        # The players participating in the game
        self.players: List[Player] = []
        # The players participating in the current hand
        self.in_hand: List[Player] = []
        # The index of the current dealer
        self.dealer_index = 0
        # The index of the first person to bet this round
        self.first_bettor = 0
        # The deck that we're dealing from
        self.cur_deck: Deck = None
        # The five cards shared by all players
        self.shared_cards: List[Card] = []
        # The current price of the little blind
        self.min_blind = 5
        # The current amount that needs to be bet to go to the next round
        self.cur_bet = 0
        # The amount of money in the pot
        self.pot = 0
        # The index of the player whose turn it is
        self.turn_index = -1
        # Whether it's the first go-around of betting
        self.first_betting_round = False

    def add_player(self, user: discord.User) -> bool:
        if self.is_player(user):
            return False
        self.players.append(Player(user))
        return True

    def is_player(self, user: discord.User) -> bool:
        for player in self.players:
            if player.user == user:
                return True
        return False

    def is_playing(self, user: discord.User) -> bool:
        for player in self.in_hand:
            if player.user == user:
                return True
        return False

    def status_between_rounds(self) -> List[str]:
        messages = []
        for player in self.players:
            messages.append(f'{player.user.name} has ${player.balance} left.')
        messages.append(f"{self.dealer.user.name} is the current dealer. Message !deal to deal when you're ready.")
        return messages

    def next_dealer(self) -> None:
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    @property
    def dealer(self) -> Player:
        return self.players[self.dealer_index]

    @property
    def big_blind(self) -> Player:
        return self.players[self.dealer_index - 1]

    @property
    def little_blind(self) -> Player:
        return self.players[self.dealer_index - 2]

    @property
    def current_player(self) -> Player:
        return self.in_hand[self.turn_index]

    def start(self) -> List[str]:
        self.state = GameState.NO_HANDS
        self.dealer_index = 0
        return ["The game has begun!"] + self.status_between_rounds()

    def deal_hands(self) -> List[str]:
        self.cur_deck = Deck()
        self.in_hand = []
        self.shared_cards = []
        for player in self.players:
            player.cards = (self.cur_deck.draw(), self.cur_deck.draw())
            player.cur_bet = 0
            self.in_hand.append(player)
        self.state = GameState.HANDS_DEALT
        self.cur_bet = self.min_blind * 2
        self.pot = 0
        self.pot += self.little_blind.pay_blind(self.min_blind)
        self.pot += self.big_blind.pay_blind(self.min_blind * 2)
        self.first_bettor = self.dealer_index
        self.turn_index = self.first_bettor
        self.first_betting_round = True
        return ['The hands have been dealt!',
                f'{self.little_blind.user.name} has paid the little blind of ${self.min_blind}.',
                f'{self.big_blind.user.name} has paid the big blind of ${self.min_blind * 2}.'] + self.cur_options()

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
            player.cur_bet = 0
        self.cur_bet = 0
        self.turn_index = self.first_bettor
        self.first_betting_round = True
        return messages + self.cur_options()

    def next_turn(self) -> List[str]:
        self.turn_index = (self.turn_index + 1) % len(self.in_hand)
        if self.turn_index == self.first_bettor:
            self.first_betting_round = False
        if self.cur_bet == self.current_player.cur_bet and not self.first_betting_round:
                return self.next_round()
        if self.current_player.balance == 0:
            return self.next_turn()
        return self.cur_options()

    def showdown(self) -> List[str]:
        messages = ["We have reached the end of betting. All cards will be revealed."]
        messages.append("  ".join(str(card) for card in self.shared_cards))

        winners: List[Player] = []
        best_hand: Hand = None
        for player in self.in_hand:
            messages.append(f"{player.user.name}'s hand: {player.cards[0]}  {player.cards[1]}")
            best_poss_hand = best_possible_hand(self.shared_cards, player.cards)
            if best_hand is None or best_poss_hand > best_hand:
                winners = [player]
                best_hand = best_poss_hand
            elif best_hand == best_poss_hand:
                winners.append(player)
        if len(winners) == 1:
            messages.append(f"{winners[0].user.name} wins ${self.pot}!")
        else:
            messages.append(f"{' and '.join(winner.user.name for winner in winners)} each win ${self.pot // len(winners)}!")
        for winner in winners:
            winner.balance += self.pot // len(winners)
        self.state = GameState.NO_HANDS
        self.next_dealer()
        messages += self.status_between_rounds()
        return messages

    def check(self) -> List[str]:
        return [f"{self.current_player.user.name} checks."] + self.next_turn()

    def raise_bet(self, amount: int) -> List[str]:
        self.cur_bet = amount
        return self.call()

    def call(self) -> List[str]:
        messages: List[str] = []
        self.pot += self.current_player.call(self.cur_bet)
        if self.current_player.balance == 0:
            messages.append(f"{self.current_player.user.name} is all in!")
        return messages + self.next_turn()

    def fold(self) -> List[str]:
        messages = [f"{self.current_player.user.name} has folded."]
        self.in_hand.pop(self.turn_index)
        if len(self.in_hand) >= self.turn_index:
            self.turn_index = 0
        if len(self.in_hand) == 1:
            messages.append(f"{self.current_player.user.name} wins ${self.pot}!")
            self.current_player.balance += self.pot
            self.state = GameState.NO_HANDS
            self.next_dealer()
            messages += self.status_between_rounds()
        else:
            if self.turn_index < self.first_bettor:
                self.first_bettor -= 1
            messages += self.cur_options()
        return messages

    async def tell_hands(self):
        for player in self.players:
            await client.send_message(player.user, '  '.join(str(card) for card in player.cards))

POKER_BOT_TOKEN = os.getenv("POKER_BOT_TOKEN")

client = discord.Client()
game = Game()

def new_game(message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        game.add_player(message.author)
        game.state = GameState.WAITING
        return [f"A new game has been started by {message.author.name}!",
                 "Message !join to join the game."]
    else:
        messages = ["There is already a game in progress, you can't start a new game."]
        if game.state == GameState.WAITING:
            messages.append("It still hasn't started yet, so you can still message !join to join that game.")
        return messages

def join_game(message: discord.Message) -> List[str]:
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

def start_game(message: discord.Message) -> List[str]:
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

def deal_hand(message: discord.Message) -> List[str]:
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

def call_bet(message: discord.Message) -> List[str]:
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

def check(message: discord.Message) -> List[str]:
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

def raise_bet(message: discord.Message) -> List[str]:
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

def fold_hand(message: discord.Message) -> List[str]:
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

@client.event
async def on_ready():
    print("Poker bot ready!")

@client.event
async def on_message(message):
    commands = {
        '!newgame': new_game,
        '!join':    join_game,
        '!start':   start_game,
        '!deal':    deal_hand,
        '!call':    call_bet,
        '!raise':   raise_bet,
        '!check':   check,
        '!fold':    fold_hand,
    }
    command = message.content.split()[0]
    if command[0] == '!' and command in commands:
        messages = commands[command](message)
        if command == '!deal' and messages[0] == 'The hands have been dealt!':
            await game.tell_hands()
        for text in messages:
            await client.send_message(message.channel, text)

client.run(POKER_BOT_TOKEN)
