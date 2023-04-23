import datetime
import re
import time

import discord
from discord.ext import commands


class Remind(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def remind(self, context, _time, *, phrase):
        pattern = r'(\d+\w)'
        matches = re.findall(pattern, _time)
        seconds = 0  # Make Pycharm stop complaining
        for match in matches:
            temp = int(match[:-1])
            unit = match[-1]
            if unit == "d":
                seconds += temp * 86400  # Converts days into seconds
            elif unit == "h":
                seconds += temp * 3600
            elif unit == "m":
                seconds += temp * 60
            else:
                seconds += temp
        old_time = time.time()
        new_time = datetime.datetime.fromtimestamp(old_time + seconds, datetime.timezone.utc)
        await context.send("Reminder " + phrase + " created for " + _time + "!")
        await discord.utils.sleep_until(new_time)
        await context.send(f"{context.author.mention}: {phrase}\nMessage: {context.message.jump_url}")


async def setup(bot):
    await bot.add_cog(Remind(bot))
