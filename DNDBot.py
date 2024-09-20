import asyncio
import datetime
import os
import sqlite3
import traceback
import zipfile

import discord.abc
from discord.ext import commands, tasks

from modules import CampaignBuilder, CampaignSQLHelper, CampaignPlayerManager, CampaignManager, Strings


class DNDBot(commands.Bot):
    instance: 'DNDBot' = None

    # noinspection PyTypeChecker
    def __init__(self, db: sqlite3.Cursor, connection: sqlite3.Connection, config: dict, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.connection = connection
        self.config = config
        self.all_cogs, self.loaded_cogs, self.unloaded_cogs = [], [], []
        self.COG_FILE = "COGS.txt"
        self.traceback = {}

        with open(self.COG_FILE, "r") as cogs:
            self.all_cogs = [i.rstrip() for i in cogs.readlines()]

        self.CampaignBuilder = CampaignBuilder(self)
        self.CampaignSQLHelper = CampaignSQLHelper(self)
        self.CampaignPlayerManager: CampaignPlayerManager = None
        self.CampaignManager: CampaignManager = None
        self.campaign_creation_callback: callable = None
        self.backup_task.start()
        self.mutex = asyncio.Lock()

    @tasks.loop(hours=24)
    async def backup_task(self):
        await self.wait_until_ready()
        await self.mutex.acquire()
        self.connection.close()
        try:
            # if backups/ directory doesn't exist, create it
            if not os.path.exists("backups"):
                os.makedirs("backups")
                # zip the database file
            filename = ("backups/" + self.config["database_file"] + '-' +
                        datetime.date.today().strftime("%Y-%m-%d") + ".zip")
            with zipfile.ZipFile(filename, "w") as backup:
                backup.write(self.config["database_file"], os.path.basename(self.config["database_file"]))
        except Exception as e:
            traceback.print_exc()
        finally:
            def dict_factory(cursor, row):
                d = {}
                for idx, col in enumerate(cursor.description):
                    d[col[0]] = row[idx]
                return d
            self.connection = sqlite3.connect(self.config["database_file"], check_same_thread=False)
            self.connection.row_factory = dict_factory
            self.db = self.connection.cursor()
            self.mutex.release()

    async def try_send_message(self, member: discord.Member, channel: discord.abc.Messageable, message):
        try:
            await member.send(message)
        except discord.Forbidden:
            await channel.send(Strings.Error.ERROR_CLOSED_DMS.format(member=member))
        except Exception:
            await channel.send(Strings.Error.ERROR_UNKNOWN_DMS.format(member=member))
