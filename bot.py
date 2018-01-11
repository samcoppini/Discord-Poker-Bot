from enum import Enum
import random
import os

import discord

POKER_BOT_TOKEN = os.getenv('POKER_BOT_TOKEN')
RANKS = ('2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A')
SUITS = (':spades:', ':diamonds:', ':clubs:', ':hearts:')
STARTING_BALANCE = 500

client = discord.Client()

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
    
class Game:
    def __init__(self):
        self.state = GameState.NO_GAME
        self.players = []
        self.player_hands = []
        self.deck = []
        self.shared_cards = []
        self.dealer_index = 0

    @property
    def dealer(self):
        return self.players[self.dealer_index][0]

    def shuffle(self):
        self.deck = [rank + suit for rank in RANKS
                                 for suit in SUITS]
        random.shuffle(self.deck)

    def add_player(self, player):
        for user, balance in self.players:
            if user == player:
                return False
        self.players.append((player, STARTING_BALANCE))
        return True

    async def deal_hands(self, channel):
        self.player_hands = []
        self.shared_cards = []
        self.shuffle()
        for player, balance in self.players:
            hand = (self.deck.pop(), self.deck.pop())
            self.player_hands.append((player, hand, 0))
            await client.send_message(player, '  '.join(hand))
        await client.send_message(channel, "Hands have been dealt. Start betting.")
        game.state = GameState.HANDS_DEALT

    async def flop(self, channel):
        for i in range(3):
            self.shared_cards.append(self.deck.pop())
        await self.say_shared_cards(channel, 'flop')
        self.state = GameState.FLOP_DEALT

    async def turn(self, channel):
        self.shared_cards.append(self.deck.pop())
        await self.say_shared_cards(channel, 'turn')
        self.state = GameState.TURN_DEALT

    async def river(self, channel):
        self.shared_cards.append(self.deck.pop())
        await self.say_shared_cards(channel, 'river')
        self.state = GameState.RIVER_DEALT

    async def showdown(self, channel):
        message = []
        message.append('Community cards: ')
        message.append('  '.join(self.shared_cards))
        for player, hand, bet_amount in self.player_hands:
            message.append(player.name + "'s hand:")
            message.append('  '.join(hand))
        await client.send_message(channel, '\n'.join(message))
        self.state = GameState.NO_HANDS
        self.dealer_index = (self.dealer_index + 1) % len(self.players)
        await self.say_state(channel)

    async def say_shared_cards(self, channel, name):
        message = f'Dealing the {name}:\n{"  ".join(self.shared_cards)}'
        await client.send_message(channel, message)

    async def say_state(self, channel):
        for player, balance in self.players:
            await client.send_message(channel, f'{player.name} has ${balance}.')
        await client.send_message(channel, f"It is {self.dealer.name}'s turn to deal. Message !deal to deal.")

@client.event
async def on_ready():
    print("Logged in as", client)

@client.event
async def on_message(message):
    channel = message.channel

    async def speak(text):
        await client.send_message(channel, text)

    if message.author == client.user:
        return

    tokens = message.content.split()

    if tokens[0] == '!newgame':
        if game.state == GameState.NO_GAME:
            game.state = GameState.WAITING
            await speak('Starting a new game. Message !join to join the game.')
    elif tokens[0] == '!join':
        if game.state == GameState.WAITING:
            if game.add_player(message.author):
                await speak(message.author.name + " has joined the game.")
                if len(game.players) >= 2:
                    await speak("Message !join to join the game, or !start to start.")
                else:
                    await speak("Message !join to join the game.")
    elif tokens[0] == '!start':
        if message.author not in [player for player, balance in game.players]:
            await speak("You can't start the game if you're not playing, " + message.author.name)
            await speak("Message !join to join.")
            return
        elif len(game.players) < 2:
            await speak("Can't start the game with less than two players.")
            return
        if game.state == GameState.WAITING:
            game.state = GameState.NO_HANDS
            await speak('The game has begun!')
            await game.say_state(message.channel)
    elif tokens[0] == '!deal':
        if message.author != game.dealer:
            await speak(f"You are not the dealer, {message.author.name}, don't try to deal.")
            return
        if game.state == GameState.NO_HANDS:
            await game.deal_hands(channel)
        elif game.state == GameState.HANDS_DEALT:
            await game.flop(channel)
        elif game.state == GameState.FLOP_DEALT:
            await game.turn(channel)
        elif game.state == GameState.TURN_DEALT:
            await game.river(channel)
        elif game.state == GameState.RIVER_DEALT:
            await game.showdown(channel)

game = Game()
client.run(POKER_BOT_TOKEN)
