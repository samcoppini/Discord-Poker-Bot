# Discord Poker Bot
This is a bot written in python 3 using the [discord.py](https://github.com/Rapptz/discord.py) library. It allows you to play Texas Hold'em over discord.

## Running this for yourself
To run this bot for yourself, first make you are using python 3.6+ and have the discord.py library installed.

```
pip install discord.py
```

Next, head to the [discord applications page](https://discordapp.com/developers/applications/me) and click on the *New App* button.

Add whatever name, description and icon you want for your new app, and click on the *Create App* button.

Scroll down, and click on the *Create a Bot User* button.

Click on the *click to reveal* button to get your bot's token. Next, either set your `POKER_BOT_TOKEN` environment variable to be that token, or replace `os.getenv("POKER_BOT_TOKEN")` on line 9 of `bot.py` with your bot's token.

Now, go to [this page](https://finitereality.github.io/permissions-calculator/?v=0), select all the Non-Administrative permissions, enter the client id from the bot's application page, and then select one of the servers you own to add it that server.

Finally, when you have done all that, run `bot.py`, and message `!newgame` in the server to start a new game of Texas Hold'em.
