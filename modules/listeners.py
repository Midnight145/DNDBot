import discord
from discord.ext import commands


class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.get_role(809567701735440467) in member.roles:
            await (member.guild.get_channel(self.bot.config["player_logs"])).send(
                f"Member {member.mention} ({member.display_name}) left the server while in a campaign.\nNickname: {member.nick if member.nick is not None else member.display_name}\nUser ID: {member.id}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Role Logging

        if sorted(before.roles, key=lambda x: x.id) == sorted(after.roles, key=lambda x: x.id):
            return
        diff = [i for i in after.roles + before.roles if i not in after.roles or i not in before.roles]
        new_roles = []
        for i in diff:
            if i in after.roles and i not in before.roles:
                new_roles.append(i)
        for i in new_roles:
            resp = self.bot.db.execute("SELECT * FROM campaigns WHERE role LIKE ?", (i.id,)).fetchone()
            if resp is None:
                continue
            else:

                category = self.bot.get_channel(resp["category"])
                for channel in category.channels:
                    if channel.name == "lobby":
                        await channel.send(f"{after.mention} has joined the campaign!")


def setup(bot):
    bot.add_cog(Listeners(bot))