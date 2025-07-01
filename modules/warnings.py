import datetime

import discord
from discord.ext import commands


class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_role(809567701735440469)
    @commands.command()
    async def warn(self, context: commands.Context, member: discord.Member, *, reason: str):
        self.bot.db.execute("INSERT INTO warns (member, reason) VALUES (?, ?)", (member.id, reason))
        self.bot.connection.commit()
        embed = discord.Embed(
            title="User warned",
            description=f"User {member.mention} warned.\nReason: {reason}",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        await context.send(embed=embed)

        if context.channel.id != self.bot.config["warnings_channel"]:
            await (context.guild.get_channel(self.bot.config["warnings_channel"])).send(embed=embed)
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            await context.send(f"Error in sending message to {member.mention}: Forbidden")
        await context.message.delete()

    @commands.command(aliases=["warnings", "list_warnings"])
    async def warns(self, context: commands.Context, member: discord.Member = None):
        if member is None:
            member = context.author
        if member != context.author:
            if not any(self.bot.config["officer_role"] == i.id for i in context.author.roles):
                member = context.author
        resp = self.bot.db.execute("SELECT * FROM warns WHERE member = ?", (member.id,)).fetchall()
        counter = 0
        embed = discord.Embed(
            title="Warnings",
            description=f"Warnings for member {member.mention}",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        for i in resp:
            embed.add_field(name=f"Warning {counter}", value=i["reason"], inline=False)
            counter += 1

        await context.send(embed=embed)

    # @commands.has_role("Officer")
    # @commands.command()
    # async def list_warnings(self, context: commands.Context, member: discord.Member = None):
    #     resp = self.bot.db.execute("SELECT * FROM warns").fetchall()
    #     warned_members = [i["member"] for i in resp]
    #     for member_id in warned_members:
    #         member = context.guild.get_member(member_id)
    #         if member is None:
    #             mention = member_id
    #         else:
    #             mention = member.mention
    #         counter = 0
    #         embed = discord.Embed(
    #             title="Warnings",
    #             description=f"Warnings for member {mention}",
    #             color=discord.Color.dark_red(),
    #             timestamp=datetime.datetime.utcnow()
    #         )
    #         for warn in resp:
    #             if warn["member"] == member_id:
    #                 embed.add_field(name=f"Warning {counter}", value=warn["reason"], inline=False)
    #                 counter += 1
    #         await context.send(embed=embed)

    @commands.has_role("Officer")
    @commands.command()
    async def remove_warn(self, context: commands.Context, member: discord.Member, index: int):
        resp = self.bot.db.execute("SELECT * FROM warns WHERE member = ?", (member.id,)).fetchall()
        text = resp[index]["reason"]
        self.bot.db.execute("DELETE FROM warns WHERE reason LIKE ? AND member = ?", (text, member.id))
        self.bot.db.connection.commit()
        embed = discord.Embed(
            title="Warning removed.",
            description=f"Warning {index} removed from {member.mention}",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Warning Reason", value=text)
        await context.send(embed=embed)
        await (context.guild.get_channel(self.bot.config["warnings_channel"])).send(embed=embed)
        await context.message.delete()


async def setup(bot):
    await bot.add_cog(Warnings(bot))
