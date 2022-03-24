import sys
import discord
import json
import sqlite3

from bot import DNDBot
from modules.errorhandler import TracebackHandler

with open('config.json') as config_file:
    config = json.load(config_file)
with open('token.txt', 'r') as token:
    TOKEN = token.read().rstrip()


async def get_prefix(bot_, message):
    return config["prefix"]

GUILD_ID = config["server"]

connection = sqlite3.connect(config["database_file"])
connection.row_factory = sqlite3.Row
db = connection.cursor()
db.execute("CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY, name TEXT, dm INTEGER, role INTEGER, "
           "category INTEGER, information INTEGER, min_players INTEGER, max_players INTEGER, current_players INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS warns (id INTEGER PRIMARY KEY, member INTEGER, reason TEXT)")
connection.commit()

intents = discord.Intents.default()
intents.members = True

bot = DNDBot(db, connection, config, command_prefix=get_prefix, intents=intents)


@bot.event
async def on_ready():
    print("Logged in")
    for i in bot.all_cogs:
        if i in bot.loaded_cogs: continue
        bot.load_extension(i)
        bot.loaded_cogs.append(i)
    print("All cogs loaded successfully!")


@bot.event
async def on_error(event, *args, **kwargs):
    exc_type, exc_name, exc_traceback = sys.exc_info()
    channel = bot.get_channel(config["staff_botspam"])
    err_code = 255
    for i in range(len(bot.traceback) + 1):
        if i in bot.traceback:
            continue
        err_code = i
    original = getattr(exc_traceback, '__cause__', exc_traceback)
    handler = TracebackHandler(err_code, f"{exc_type.__name__}: {str(exc_name)}", original)
    bot.traceback[err_code] = handler
    await channel.send(f"An error occurred in {event}. Error code: {str(err_code)}")

bot.run(TOKEN)
