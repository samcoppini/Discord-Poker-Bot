from collections import namedtuple
import os
from typing import Dict, List

import discord

from game import Game, GAME_OPTIONS, GameState

POKER_BOT_TOKEN = os.getenv("POKER_BOT_TOKEN")

client = discord.Client()
games: Dict[discord.Channel, Game] = {}

# Starts a new game if one hasn't been started yet, returning an error message
# if a game has already been started. Returns the messages the bot should say
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

# Has a user try to join a game about to begin, giving an error if they've
# already joined or the game can't be joined. Returns the list of messages the
# bot should say
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

# Starts a game, so long as one hasn't already started, and there are enough
# players joined to play. Returns the messages the bot should say.
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

# Deals the hands to the players, saying an error message if the hands have
# already been dealt, or the game hasn't started. Returns the messages the bot
# should say
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

# Handles a player calling a bet, giving an appropriate error message if the
# user is not the current player or betting hadn't started. Returns the list of
# messages the bot should say.
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

# Has a player check, giving an error message if the player cannot check.
# Returns the list of messages the bot should say.
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

# Has a player raise a bet, giving an error message if they made an invalid
# raise, or if they cannot raise. Returns the list of messages the bot will say
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

# Has a player fold their hand, giving an error message if they cannot fold
# for some reason. Returns the list of messages the bot should say
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

# Returns a list of messages that the bot should say in order to tell the
# players the list of available commands.
def show_help(game: Game, message: discord.Message) -> List[str]:
    longest_command = len(max(commands, key=len))
    help_lines = []
    for command, info in sorted(commands.items()):
        spacing = ' ' * (longest_command - len(command) + 2)
        help_lines.append(command + spacing + info[0])
    return ['```' + '\n'.join(help_lines) + '```']

# Returns a list of messages that the bot should say in order to tell the
# players the list of settable options.
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

# Sets an option to player-specified value. Says an error message if the player
# tries to set a nonexistent option or if the option is set to an invalid value
# Returns the list of messages the bot should say.
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

# Returns a list of messages that the bot should say to tell the players of
# the current chip standings.
def chip_count(game: Game, message: discord.Message) -> List[str]:
    if game.state in (GameState.NO_GAME, GameState.WAITING):
        return ["You can't request a chip count because the game "
                "hasn't started yet."]
    return [f"{player.user.name} has ${player.balance}."
            for player in game.players]

# Handles a player going all-in, returning an error message if the player
# cannot go all-in for some reason. Returns the list of messages for the bot
# to say.
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

# The commands avaliable to the players
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

        # The messages to send to the channel and the messages to send to the
        # players individually must be done seperately, so we check the messages
        # to the channel to see if hands were just dealt, and if so, we tell the
        # players what their hands are.
        if command == '!deal' and messages[0] == 'The hands have been dealt!':
            await game.tell_hands(client)

        await client.send_message(message.channel, '\n'.join(messages))

client.run(POKER_BOT_TOKEN)
