import time

from discord.ext import commands
import discord
import datetime


class Remind(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def remind(self, context, _time, *, phrase):
        temp = int(''.join([i for i in _time if i.isdigit()]))
        seconds = 0  # Make Pycharm stop complaining
        for i in str(_time):
            if i == "d":
                seconds = temp * 86400  # Converts days into seconds
            elif i == "h":
                seconds = temp * 3600
            elif i == "m":
                seconds = temp * 60
            else:
                seconds = temp

        old_time = time.time()
        new_time = datetime.datetime.utcfromtimestamp(old_time + seconds)
        await context.send("Reminder " + phrase + " created for " + _time + "!")
        await discord.utils.sleep_until(new_time)
        await context.send(context.author.mention + ": " + phrase)


def setup(bot):
    bot.add_cog(Remind(bot))
