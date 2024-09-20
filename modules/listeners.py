import discord
from discord.ext import commands


class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.db.execute("CREATE TABLE IF NOT EXISTS reacts (id INTEGER PRIMARY KEY, phrase TEXT, reaction TEXT, "
                            "channel INTEGER)")
        self.bot.db.execute("CREATE TABLE IF NOT EXISTS responses (id INTEGER PRIMARY KEY, phrase TEXT, response TEXT, "
                            "channel INTEGER)")
        self.bot.connection.commit()
        self.reacts = {}
        self.responses = {}

        self.load_reactions()

    def load_reactions(self):
        react_table = self.bot.db.execute("SELECT * FROM reacts").fetchall()
        response_table = self.bot.db.execute("SELECT * FROM responses").fetchall()
        self.reacts = {i["id"]: (i["phrase"], i["reaction"], i["channel"]) for i in react_table}
        self.responses = {i["id"]: (i["phrase"], i["response"], i["channel"]) for i in response_table}

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        campaigns = []
        # get all campaign roles
        resp = self.bot.CampaignSQLHelper.select_field("role")
        for role_ in resp:
            # check if member is in campaign
            role = member.guild.get_role(role_['role'])
            if role is None:
                continue
            if member in role.members:
                campaigns.append(role.name)
        if len(campaigns) > 0:
            await (member.guild.get_channel(self.bot.config["player_logs"])).send(
                f"Member {member.mention} ({member.display_name}) left the server while in a campaign.\nNickname: "
                f"{member.nick if member.nick is not None else member.display_name}\nUser ID: {member.id}\nCampaigns: "
                f"{', '.join(campaigns)}")

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

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def add_reaction(self, context, phrase, reaction, channel):
        self.bot.db.execute("INSERT INTO reacts (phrase, reaction, channel) VALUES (?, ?, ?)",
                            (phrase, reaction, channel))
        self.bot.connection.commit()
        self.load_reactions()
        await context.send("Added!")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def add_response(self, context, phrase, response, channel):
        self.bot.db.execute("INSERT INTO responses (phrase, response, channel) VALUES (?, ?, ?)",
                            (phrase, response, channel))
        self.bot.connection.commit()
        self.load_reactions()
        await context.send("Added!")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def list_reactions(self, context):
        reacts = self.bot.db.execute("SELECT * FROM reacts").fetchall()
        resps = self.bot.db.execute("SELECT * FROM responses").fetchall()
        resp = "Message Reactions:\n"
        for i in reacts:
            resp += f"{i['id']}: {i['phrase']} -> {i['reaction']} in {context.guild.get_channel(i['channel'])}\n"
        await context.send(resp)
        resp = "Message Responses:\n"
        for i in resps:
            resp += f"{i['id']}: {i['phrase']} -> {i['response']} in {context.guild.get_channel(i['channel'])}\n"
        await context.send(resp)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def remove_reaction(self, context, id_):
        self.bot.db.execute("DELETE FROM reacts WHERE id = ?", (id_,))
        self.bot.connection.commit()
        self.load_reactions()
        await context.send("Removed!")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def remove_response(self, context, id_):
        self.bot.db.execute("DELETE FROM responses WHERE id = ?", (id_,))
        self.bot.connection.commit()
        self.load_reactions()
        await context.send("Removed!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # this just force-caches the member
        if member.guild.get_member(member.id) is None:
            await self.bot.guild.fetch_member(member.id)


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        for i in self.reacts.values():
            if i[0] in message.content.lower() and message.channel.id == int(i[2]):
                await message.add_reaction(i[1])
        for i in self.responses.values():
            if i[0] in message.content.lower() and message.channel.id == int(i[2]):
                await message.channel.send(i[1])

    @commands.command()
    async def reload_reactions(self, context):
        self.load_reactions()
        await context.send("Reloaded!")


async def setup(bot):
    await bot.add_cog(Listeners(bot))
