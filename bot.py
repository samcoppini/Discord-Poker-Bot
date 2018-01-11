import random
import os

import discord

POKER_BOT_TOKEN = os.getenv('POKER_BOT_TOKEN')

RANKS = ('2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K')
SUITS = (':spades:', ':diamonds:', ':clubs:', ':hearts:')

client = discord.Client()

@client.event
async def on_ready():
    print("Logged in as", client)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    tokens = message.content.split()
    if tokens[0] == '!deal':
        hand = random.choice(SUITS) + random.choice(RANKS)
        await client.send_message(message.author, hand)

client.run(POKER_BOT_TOKEN)
