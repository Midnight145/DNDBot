import importlib

import discord
from discord.ext import commands
import sqlite3
from modules import CampaignBuilder, CampaignSQLHelper, CampaignPlayerManager


class DNDBot(commands.Bot):
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

    @commands.command(name="reload", aliases=["r"], hidden=True)
    async def reload(self, ctx: commands.Context):
        """Reloads all cogs"""
        for cog in self.all_cogs:
            try:
                self.unload_extension(cog)
                self.load_extension(cog)
                self.loaded_cogs.append(cog)
                self.unloaded_cogs.remove(cog)
            except Exception as e:
                self.traceback[cog] = e
                self.unloaded_cogs.append(cog)
                self.loaded_cogs.remove(cog)
        await ctx.send("Reloaded all cogs")
