import asyncio
import json
import logging
import sqlite3
import sys

import discord
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from DNDBot import DNDBot
from modules.api import api
from modules.errorhandler import TracebackHandler
from fastapi import status
from fastapi import Request


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


app = FastAPI()
app.include_router(api.router)
with open('config.json') as config_file:
    config = json.load(config_file)
with open('token.txt', 'r') as token:
    TOKEN = token.read().rstrip()


async def get_prefix(bot_, message):
    return config["prefix"]


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logging.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


GUILD_ID = config["server"]

connection = sqlite3.connect(config["database_file"], check_same_thread=False)
# connection.row_factory = sqlite3.Row

connection.row_factory = dict_factory
db = connection.cursor()
db.execute("CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY, name TEXT, dm INTEGER, role INTEGER, "
           "category INTEGER, information_channel INTEGER, min_players INTEGER, max_players INTEGER, current_players "
           "INTEGER, status_message INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS warns (id INTEGER PRIMARY KEY, member INTEGER, reason TEXT)")
connection.commit()

intents = discord.Intents.all()

bot = DNDBot(db, connection, config, command_prefix=get_prefix, intents=intents)
DNDBot.instance = bot


@bot.event
async def on_ready():
    print("Logged in")
    for i in bot.all_cogs:
        if i in bot.loaded_cogs:
            continue
        await bot.load_extension(i)
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


# todo: do this better, this is a mess
DNDBot.instance.campaign_creation_callback = api.campaign_creation_callback


async def start():
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        await bot.close()


asyncio.create_task(start())
