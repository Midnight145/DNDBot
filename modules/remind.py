import asyncio
import datetime
import re
import time

import discord
from discord.ext import commands


class Remind(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tasks = []

    @commands.command()
    async def remind(self, context: commands.Context, _time, *, phrase):
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
        timestamp = old_time + seconds
        self.bot.db.execute("INSERT INTO reminders (user_id, channel, time, phrase, jump_url) VALUES (?, ?, ?, ?, ?)",
                            (context.author.id, context.channel.id, timestamp, phrase, context.message.jump_url))
        self.bot.connection.commit()
        await context.send("Reminder " + phrase + " created for " + _time + "!")
        await discord.utils.sleep_until(new_time)
        await context.send(f"{context.author.mention}: {phrase}\nMessage: {context.message.jump_url}")
        self.bot.db.execute("DELETE FROM reminders WHERE jump_url = ?", (context.message.jump_url,))
        self.bot.connection.commit()

    @commands.command()
    async def reminders(self, context: commands.Context):
        reminders = self.bot.db.execute("SELECT * FROM reminders WHERE user_id = ?", (context.author.id,)).fetchall()
        if len(reminders) == 0:
            await context.send("You have no reminders!")
            return
        embed = discord.Embed(title="Reminders", color=discord.Color.from_rgb(255, 255, 255))
        for reminder in reminders:
            embed.add_field(name=f"ID: {reminder['id']} -- {reminder['phrase']}",
                            value=f"Time: {datetime.datetime.fromtimestamp(reminder['time'], datetime.timezone.utc).strftime('%m/%d/%Y %H:%M:%S')}",
                            inline=False)
        await context.send(embed=embed)

    @commands.command()
    async def delete_reminder(self, context: commands.Context, reminder_id):
        reminder = self.bot.db.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
        if reminder is None:
            await context.send("Reminder not found!")
            return
        if reminder["user_id"] != context.author.id:
            await context.send("You can only delete your own reminders!")
            return
        self.bot.db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        self.bot.connection.commit()
        await context.send("Reminder deleted!")

    # noinspection PyAsyncCall
    async def cog_load(self):
        reminders = self.bot.db.execute("SELECT * FROM reminders").fetchall()
        for reminder in reminders:
            self.tasks.append(asyncio.create_task(self.remind_task(reminder)))
        print("Done loading reminders!")

    async def cog_unload(self):
        for task in self.tasks:
            task.cancel()
        print("Done unloading reminders!")

    async def remind_task(self, reminder):
        user = self.bot.get_user(reminder["user_id"])
        channel = self.bot.get_channel(reminder["channel"])
        print("Sleeping until " + str(
            datetime.datetime.fromtimestamp(reminder["time"], datetime.timezone.utc)) + " for " + reminder["phrase"])
        await discord.utils.sleep_until(datetime.datetime.fromtimestamp(reminder["time"], datetime.timezone.utc))
        await channel.send(f"{user.mention}: {reminder['phrase']}\nMessage: {reminder['jump_url']}")
        self.bot.db.execute("DELETE FROM reminders WHERE id = ?", (reminder["id"],))
        self.bot.connection.commit()


async def setup(bot):
    await bot.add_cog(Remind(bot))
