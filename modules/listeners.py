import discord
from discord.ext import commands


class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        campaigns = []
            # get all campaign roles
        resp = self.bot.CampaignSQLHelper.select_field("role")
        for role_ in resp:
            # check if member is in campaign
            role = member.guild.get_role(role_[0])
            if role is None:
                continue
            if member in role.members:
                campaigns.append(role.name)
        if len(campaigns) > 0:
            await (member.guild.get_channel(self.bot.config["player_logs"])).send(
                f"Member {member.mention} ({member.display_name}) left the server while in a campaign.\nNickname: {member.nick if member.nick is not None else member.display_name}\nUser ID: {member.id}\nCampaigns: {', '.join(campaigns)}")

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

#    @commands.Cog.listener()
#    async def on_message(self, message):
#        if "bee" in message.content.lower() and not message.author.bot and message.channel.id == 809567702062333967:
#            await message.channel.send("bees are insects AND animals")
 
def setup(bot):
    bot.add_cog(Listeners(bot))
