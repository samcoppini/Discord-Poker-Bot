from collections import namedtuple
import os
from typing import Dict, List

import discord

from game import Game, GAME_OPTIONS, GameState

POKER_BOT_TOKEN = os.getenv("POKER_BOT_TOKEN")

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
        messages = ["There is already a game in progress, "
                    "you can't start a new game."]
        if game.state == GameState.WAITING:
            messages.append("It still hasn't started yet, so you can still "
                            "message !join to join that game.")
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
                "Message !join to join the game, "
                "or !start to start the game."]
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
        return ["The game must have at least two players before "
                "it can be started."]
    else:
        return game.start()

def deal_hand(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started for you to deal. "
                "Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't deal because the game hasn't started yet."]
    elif game.state != GameState.NO_HANDS:
        return ["The cards have already been dealt."]
    elif game.dealer.user != message.author:
        return [f"You aren't the dealer, {message.author.name}.",
                f"Please wait for {game.dealer.user.name} to !deal."]
    else:
        return game.deal_hands()

def call_bet(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet. Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't call any bets because the game hasn't started yet."]
    elif not game.is_player(message.author):
        return ["You can't call, because you're not playing, "
                f"{message.author.name}."]
    elif game.state == GameState.NO_HANDS:
        return ["You can't call any bets because the hands haven't been "
                "dealt yet."]
    elif game.current_player.user != message.author:
        return [f"You can't call {message.author.name}, because it's "
                f"{game.current_player.user.name}'s turn."]
    else:
        return game.call()

def check(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet. Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't check because the game hasn't started yet."]
    elif not game.is_player(message.author):
        return ["You can't check, because you're not playing, "
                f"{message.author.name}."]
    elif game.state == GameState.NO_HANDS:
        return ["You can't check because the hands haven't been dealt yet."]
    elif game.current_player.user != message.author:
        return [f"You can't check, {message.author.name}, because it's "
                f"{game.current_player.user.name}'s turn."]
    elif game.current_player.cur_bet != game.cur_bet:
        return [f"You can't check, {message.author.name} because you need to "
                f"put in ${game.cur_bet - game.current_player.cur_bet} to "
                "call."]
    else:
        return game.check()

def raise_bet(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet. Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't raise because the game hasn't started yet."]
    elif not game.is_player(message.author):
        return ["You can't raise, because you're not playing, "
                f"{message.author.name}."]
    elif game.state == GameState.NO_HANDS:
        return ["You can't raise because the hands haven't been dealt yet."]
    elif game.current_player.user != message.author:
        return [f"You can't raise, {message.author.name}, because it's "
                f"{game.current_player.name}'s turn."]

    tokens = message.content.split()
    if len(tokens) < 2:
        return [f"Please follow !raise with the amount that you would "
                "like to raise it by."]
    try:
        amount = int(tokens[1])
        if game.cur_bet >= game.current_player.max_bet:
            return ["You don't have enough money to raise the current bet "
                    f"of ${game.cur_bet}."]
        elif game.cur_bet + amount > game.current_player.max_bet:
            return [f"You don't have enough money to raise by ${amount}.",
                    "The most you can raise it by is "
                    f"${game.current_player.max_bet - game.cur_bet}."]
        return game.raise_bet(amount)
    except ValueError:
        return ["Please follow !raise with an integer. "
                f"'{tokens[1]}' is not an integer."]

def fold_hand(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet. "
                "Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't fold yet because the game hasn't started yet."]
    elif not game.is_player(message.author):
        return ["You can't fold, because you're not playing, "
                f"{message.author.name}."]
    elif game.state == GameState.NO_HANDS:
        return ["You can't fold yet because the hands haven't been dealt yet."]
    elif game.current_player.user != message.author:
        return [f"You can't fold {message.author.name}, because it's "
                f"{game.current_player.name}'s turn."]
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
        option_lines.append(option + name_spaces + str(game.options[option])
                            + val_spaces + GAME_OPTIONS[option].description)
    return ['```' + '\n'.join(option_lines) + '```']

def set_option(game: Game, message: discord.Message) -> List[str]:
    tokens = message.content.split()
    if len(tokens) == 2:
        return ["You must specify a new value after the name of an option "
                "when using the !set command."]
    elif len(tokens) == 1:
        return ["You must specify an option and value to set when using "
                "the !set command."]
    elif tokens[1] not in GAME_OPTIONS:
        return [f"'{tokens[1]}' is not an option. Message !options to see "
                "the list of options."]
    try:
        val = int(tokens[2])
        if val < 0:
            return [f"Cannot set {tokens[1]} to a negative value!"]
        game.options[tokens[1]] = val
        return [f"The {tokens[1]} is now set to {tokens[2]}."]
    except ValueError:
        return [f"{tokens[1]} must be set to an integer, and '{tokens[2]}'"
                " is not a valid integer."]

def chip_count(game: Game, message: discord.Message) -> List[str]:
    if game.state in (GameState.NO_GAME, GameState.WAITING):
        return ["You can't request a chip count because the game "
                "hasn't started yet."]
    return [f"{player.user.name} has ${player.balance}."
            for player in game.players]

def all_in(game: Game, message: discord.Message) -> List[str]:
    if game.state == GameState.NO_GAME:
        return ["No game has been started yet. Message !newgame to start one."]
    elif game.state == GameState.WAITING:
        return ["You can't go all in because the game hasn't started yet."]
    elif not game.is_player(message.author):
        return ["You can't go all in, because you're not playing, "
                f"{message.author.name}."]
    elif game.state == GameState.NO_HANDS:
        return ["You can't go all in because the hands haven't "
                "been dealt yet."]
    elif game.current_player.user != message.author:
        return [f"You can't go all in, {message.author.name}, because "
                f"it's {game.current_player.user.name}'s turn."]
    else:
        return game.all_in()

Command = namedtuple("Command", ["description", "action"])

commands: Dict[str, Command] = {
    '!newgame': Command('Starts a new game, allowing players to join.',
                        new_game),
    '!join':    Command('Lets you join a game that is about to begin',
                        join_game),
    '!start':   Command('Begins a game after all players have joined',
                        start_game),
    '!deal':    Command('Deals the hole cards to all the players',
                        deal_hand),
    '!call':    Command('Matches the current bet',
                        call_bet),
    '!raise':   Command('Increase the size of current bet',
                        raise_bet),
    '!check':   Command('Bet no money',
                        check),
    '!fold':    Command('Discard your hand and forfeit the pot',
                        fold_hand),
    '!help':    Command('Show the list of commands',
                        show_help),
    '!options': Command('Show the list of options and their current values',
                        show_options),
    '!set':     Command('Set the value of an option',
                        set_option),
    '!count':   Command('Shows how many chips each player has left',
                        chip_count),
    '!all-in':  Command('Bets the entirety of your remaining chips',
                        all_in),
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
            await client.send_message(
                message.channel, f"{message.content} is not a valid command. "
                                 "Message !help to see the list of commands.")
            return

        game = games.setdefault(message.channel, Game())
        messages = commands[command][1](game, message)
        if command == '!deal' and messages[0] == 'The hands have been dealt!':
            await game.tell_hands(client)
        await client.send_message(message.channel, '\n'.join(messages))

client.run(POKER_BOT_TOKEN)
