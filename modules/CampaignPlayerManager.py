import asyncio
import datetime
import string
import traceback
from typing import Union, TYPE_CHECKING

import discord
from discord.ext import commands

from modules import CampaignInfo
from .FakeMember import FakeMember

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..DNDBot import DNDBot


class CampaignPlayerManager(commands.Cog):
    def __init__(self, bot: 'DNDBot'):
        self.bot = bot
        self.bot.CampaignPlayerManager = self

    @commands.has_any_role(1050188024287338567, 873734392458145912, 809567701735440469)  # dev, admin, officer
    @commands.command(aliases=["add_player"])
    async def add_player_command(self, context: commands.Context, member: discord.Member, campaign_id: Union[int, str]):
        await self.add_player(context.channel, member, campaign_id)

    async def add_player(self, channel: discord.TextChannel, member: discord.Member, campaign_id: Union[int, str],
                         waitlisted=False) -> bool:
        campaign: CampaignInfo = self.bot.CampaignSQLHelper.select_campaign(campaign_id)
        if member.id == campaign.dm:
            await channel.send("You cannot join your own campaign.")
            return False
        guest_role = channel.guild.get_role(self.bot.config["guest_role"])
        member_role = channel.guild.get_role(self.bot.config["member_role"])
        campaign_role = channel.guild.get_role(campaign.role)
        player_role = channel.guild.get_role(self.bot.config["player_role"])

        if campaign.current_players >= campaign.max_players:
            commit = self.bot.CampaignSQLHelper.waitlist_player(campaign, member)
            if commit:
                await channel.send(f"{member.display_name} has been added to the waitlist for {campaign.name}.")
                await self.update_status(campaign)
                self.bot.connection.commit()
                return True
        if waitlisted:
            commit = self.bot.CampaignSQLHelper.unwaitlist(campaign, member)
        else:
            commit = self.bot.CampaignSQLHelper.add_player(campaign, member)
        if commit:
            try:
                await member.send(f"{member.display_name}: This is a notification that you have been approved and "
                                  f"added to a campaign. If you ever wish to leave the campaign, please use the Leave "
                                  f"a Campaign form found in #how-to-join. Campaign: {campaign.name}.")
            except (discord.Forbidden, discord.HTTPException):
                pass

            await member.remove_roles(guest_role)
            await member.add_roles(member_role, campaign_role, player_role)

            if campaign.current_players + 1 == campaign.min_players:
                category: discord.CategoryChannel = channel.guild.get_channel(campaign.category)
                for i in category.channels:
                    if i.name == "lobby":
                        await i.send("This campaign now meets its minimum player goal!")
            self.bot.connection.commit()
            await self.update_status(campaign)
            return True
        else:
            await channel.send("An unknown error occurred.")
            return False

    @commands.has_any_role(1050188024287338567, 873734392458145912, 809567701735440469)  # dev, admin, officer
    @commands.command()
    async def remove_player(self, context: commands.Context, member: Union[discord.Member, FakeMember],
                            campaign_id: Union[int, str]):
        async def unwaitlist_apply(member_: discord.Member):
            name = member_.nick if member_.nick else member_.display_name
            channel = context.guild.get_channel(self.bot.config["applications_channel"])

            dm = await context.guild.fetch_member(campaign.dm)
            embed = discord.Embed(
                title=f"New Application for {campaign.name} -- from waitlist",
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Campaign", value=campaign.name, inline=False)
            embed.add_field(name="DM", value=str(dm), inline=False)
            embed.add_field(name="Name", value=name)
            embed.add_field(name="Discord", value=str(member_))
            embed.add_field(name="Discord ID", value=str(member_.id))
            embed.set_footer(text="React with a green checkmark to approve or a red X to deny.")

            to_react = await channel.send(dm.mention, embed=embed)

            await to_react.add_reaction("✅")
            await to_react.add_reaction("❌")
            await self.update_status(campaign)

        campaign: CampaignInfo = self.bot.CampaignSQLHelper.select_campaign(campaign_id)
        guest_role = context.guild.get_role(self.bot.config["guest_role"])
        member_role = context.guild.get_role(self.bot.config["member_role"])
        campaign_role = context.guild.get_role(campaign.role)
        player_role = context.guild.get_role(self.bot.config["player_role"])

        commit = self.bot.CampaignSQLHelper.remove_player(campaign, member)
        if commit:
            await member.remove_roles(campaign_role)
            campaign_roles = self.bot.CampaignSQLHelper.select_field("role")
            guest = True
            for campaign_ in campaign_roles:
                if any(role.id == campaign_["role"] for role in member.roles):
                    guest = False

            if guest:
                await member.remove_roles(member_role, player_role)
                await member.add_roles(guest_role)
            await context.send(f"{member.mention} has been removed from the campaign!")
            try:
                await member.send(f"{member.display_name}: This is a notification that you have been removed from the "
                                  f"campaign {campaign.name}. Please contact the President or the Campaign Master if "
                                  f"you think this was a mistake.")
            except (discord.Forbidden, discord.HTTPException):
                await context.send("Unable to send removal message to player.")

            try:
                dm = await context.guild.fetch_member(campaign.dm)
                await dm.send(f"{dm.mention}: This is a notification that {member.mention} has been removed from the "
                              f"campaign {campaign.name}. Please contact the President or the Campaign Master if you think "
                              f"this was a mistake.")
            except (discord.Forbidden, discord.HTTPException):
                await context.send("Unable to send removal message to DM.")

            self.bot.connection.commit()
            if campaign.current_players - 1 < campaign.max_players:
                waitlisted_players = self.bot.CampaignSQLHelper.get_waitlist(campaign)
                if len(waitlisted_players) > 0:
                    waitlisted_players.sort(key=lambda x: x["pid"])
                    # await self.bot.CampaignPlayerManager.add_player(context.channel, context.guild.get_member(
                    # waitlisted_players[0]["id"]), campaign.name, True)
                    await unwaitlist_apply(context.guild.get_member(waitlisted_players[0]["id"]))
        else:
            await context.send("An unknown error occurred.")
        await self.update_status(campaign)

    @commands.has_any_role(1050188024287338567, 873734392458145912, 809567701735440469)  # dev, admin, officer
    @commands.command()
    async def remove_missing_player(self, context, member: int, campaign_id: Union[int, str]):
        await self.remove_player(context, FakeMember(member), campaign_id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.apply(message)

    async def apply(self, message):
        if not message.channel.id == self.bot.config["receipt_channel"]:
            return
        if not message.embeds:
            return
        found_embed = message.embeds[0]
        if found_embed is None:
            return
        if "Website" in found_embed.title:
            return
            # text_check = "campaign"
        else:
            text_check = "which of the following"
        campaigns = []
        name = found_embed.fields[0].value + " " + found_embed.fields[1].value
        member = await message.guild.fetch_member(int(found_embed.fields[2].value))
        channel = message.guild.get_channel(self.bot.config["applications_channel"])
        for i in found_embed.fields:
            if text_check not in i.name.lower():
                continue
            campaign_name = i.value
            try:
                campaigns.append(self.bot.CampaignSQLHelper.select_campaign(campaign_name))
            except AttributeError:
                await message.guild.get_channel(self.bot.config["staff_botspam"]).send("Error in application for player: {}\nCampaign {} not found.".format(name, campaign_name))
        for i in campaigns:
            dm = await message.guild.fetch_member(i.dm)
            embed = discord.Embed(
                title=f"New Application for {i.name}",
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Campaign", value=i.name, inline=False)
            embed.add_field(name="DM", value=str(dm), inline=False)
            embed.add_field(name="Name", value=name)
            embed.add_field(name="Discord", value=str(member))
            embed.add_field(name="Discord ID", value=str(member.id))
            embed.set_footer(text="React with a green checkmark to approve or a red X to deny.")

            to_react = await channel.send(dm.mention, embed=embed)

            await to_react.add_reaction("✅")
            await to_react.add_reaction("❌")
            await self.update_status(i)

    @commands.command()
    async def update_campaign_players(self, context: commands.Context, campaign_id: Union[int, str]):
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_id)
        campaign_role = context.guild.get_role(campaign.role)

        members = campaign_role.members

        for i in members:
            await self.bot.CampaignPlayerManager.add_player(context.channel, i, campaign_id)

        await context.send("Campaign players updated.")
        await self.update_status(campaign)

    @commands.command()
    async def show_waitlisted_players(self, context: commands.Context, campaign_id: Union[int, str]):
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_id)
        resp = self.bot.CampaignSQLHelper.get_waitlist(campaign)
        # sort resp by pid
        resp.sort(key=lambda x: x["pid"])
        waitlisted_players = [context.guild.get_member(i["id"]) for i in resp]
        embed = discord.Embed(
            title=f"Waitlisted players for {campaign.name}",
            timestamp=datetime.datetime.utcnow()
        )
        for i in waitlisted_players:
            embed.add_field(name=i.name, value=str(i.id), inline=False)
        await context.send(embed=embed)

    async def update_status(self, campaign: CampaignInfo):
        if campaign.status_message == 0 or campaign.information_channel == 0:
            return
        message_text = f"Status: {campaign.current_players} out of {campaign.max_players} seats filled.\nLocked: {'Yes' if campaign.locked else 'No'}"
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign.name)
        info_channel: discord.TextChannel = self.bot.get_channel(campaign.information_channel)
        messages = [i async for i in info_channel.history(limit=1)]
        if len(messages) == 0:
            await self.bot.wait_for('message', check=lambda message: message.channel == info_channel)
            await info_channel.send(
                content=message_text)
            return
        last_message = messages[0]
        if last_message.author == self.bot.user:
            try:
                await last_message.edit(content=message_text)
            except discord.HTTPException:
                await info_channel.send(
                    content=message_text)
                await last_message.delete()
        else:
            await info_channel.send(content=message_text)
        await self.update_status_embed(campaign)

    @commands.command()
    async def update_campaign_status(self, context: commands.Context, campaign: Union[int, str]):

        await self.bot.CampaignPlayerManager.update_status(self.bot.CampaignSQLHelper.select_campaign(campaign))
        await context.send("status updated")

    @commands.command()
    async def mass_update(self, context):
        campaigns = [i["id"] for i in self.bot.db.execute("SELECT id FROM campaigns").fetchall()]
        for i in campaigns:
            await self.bot.CampaignPlayerManager.update_status(self.bot.CampaignSQLHelper.select_campaign(i))
            await asyncio.sleep(1)
        await context.send("done")

    async def create_status_message(self, campaign: CampaignInfo) -> discord.Embed:
        embed = discord.Embed(
            title=f"{campaign.name}",
            color=0x00ff00
        )
        embed.add_field(name="DM", value=(await self.bot.fetch_user(campaign.dm)).mention)
        embed.add_field(name="Channel: ", value=f"<#{campaign.information_channel}>", inline=False)
        embed.add_field(name="Status: ",
                        value="✅ Open" if (campaign.current_players < campaign.max_players and not campaign.locked) else "❌ Closed",
                        inline=False)
        embed.add_field(name="Players: ", value=f"{campaign.current_players}/{campaign.max_players}")
        embed.add_field(name="Locked", value=f"{bool(campaign.locked)}", inline=False)

        return embed

    async def update_status_embed(self, campaign: CampaignInfo):
        if campaign.status_message == 0:
            return
        channel = self.bot.get_channel(self.bot.config["status_channel"])
        message = None
        try:
            message = await channel.fetch_message(campaign.status_message)
            embed: discord.Embed = message.embeds[0]
            embed.title = f"{campaign.name} Status"
            if len(embed.fields) == 4:
                embed.add_field(name="tmp", value="tmp", inline=False)
            embed.set_field_at(0, name="DM", value=(await self.bot.fetch_user(campaign.dm)).mention)
            embed.set_field_at(1, name="Channel: ", value=f"<#{campaign.information_channel}>", inline=False)
            embed.set_field_at(2, name="Status: ", value="✅ Open" if campaign.current_players < campaign.max_players and not campaign.locked
                            else "❌ Closed", inline=False)
            embed.set_field_at(3, name="Players: ", value=f"{campaign.current_players}/{campaign.max_players}",
                            inline=False)
            embed.set_field_at(4, name="Locked", value=f"{bool(campaign.locked)}", inline=False)

        except discord.NotFound:
            embed = await self.create_status_message(campaign)

        try:
            await message.edit(embed=embed)
        except:
            await asyncio.sleep(.25)
            if message is not None:
                await message.delete()
            new_message = await channel.send(embed=embed)
            self.bot.db.execute("UPDATE campaigns SET status_message = ? WHERE id = ?", (new_message.id, campaign.id))
            self.bot.connection.commit()

    @commands.command()
    async def init_status(self, context):
        async def create_status_message(campaign: CampaignInfo) -> discord.Embed:
            embed = discord.Embed(
                title=f"{campaign.name}",
                color=0x00ff00
            )
            embed.add_field(name="DM", value=(await self.bot.fetch_user(campaign.dm)).mention)
            embed.add_field(name="Channel: ", value=f"<#{campaign.information_channel}>", inline=False)
            embed.add_field(name="Status: ",
                            value="✅ Open" if campaign.current_players < campaign.max_players else "❌ Closed",
                            inline=False)
            embed.add_field(name="Players: ", value=f"{campaign.current_players}/{campaign.max_players}")

            return embed

        campaigns = [i["id"] for i in self.bot.db.execute("SELECT id FROM campaigns").fetchall()]
        for i in campaigns:
            message = await context.guild.get_channel(self.bot.config["status_channel"]).send(
                embed=(await create_status_message(self.bot.CampaignSQLHelper.select_campaign(i))))
            self.bot.db.execute("UPDATE campaigns SET status_message = ? WHERE id = ?", (message.id, i))
            self.bot.connection.commit()
        await context.send("done")

    @commands.command()
    async def add_status_channels(self, context):
        # get message status channel
        channel = self.bot.get_channel(self.bot.config["status_channel"])
        # get all campaigns
        campaigns = [i["id"] for i in self.bot.db.execute("SELECT id FROM campaigns").fetchall()]
        # for each campaign
        for i in campaigns:
            # get the campaign
            campaign = self.bot.CampaignSQLHelper.select_campaign(i)
            # get the message
            message = await channel.fetch_message(campaign.status_message)
            # get the embed
            embed: discord.Embed = message.embeds[0]
            # add the field
            embed.remove_field(3)
            embed.insert_field_at(1, name="Channel: ", value=f"<#{campaign.information_channel}>", inline=False)
            # edit the message
            await message.edit(embed=embed)
            await asyncio.sleep(.5)  # rate limit
        await context.send("done")

    @commands.command()
    async def fix_status(self, context: commands.Context, campaign: Union[int, str]):
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign)
        await self.update_status_embed(campaign)
        await context.send("done")

    @commands.has_any_role(1050188024287338567)  # dev
    @commands.command()
    async def create_status(self, context: commands.Context, campaign: Union[int, str]):
        async def create_status_message() -> discord.Embed:
            embed = discord.Embed(
                title=f"{campaign.name}",
                color=0x00ff00
            )
            embed.add_field(name="DM", value=(await self.bot.fetch_user(campaign.dm)).mention)
            embed.add_field(name="Channel: ", value=f"<#{campaign.information_channel}>", inline=False)
            embed.add_field(name="Status: ",
                            value="✅ Open" if campaign.current_players < campaign.max_players else "❌ Closed",
                            inline=False)
            embed.add_field(name="Players: ", value=f"{campaign.current_players}/{campaign.max_players}", inline=False)

            return embed

        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign)
        message = await context.guild.get_channel(self.bot.config["status_channel"]).send(
            embed=(await create_status_message()))
        self.bot.db.execute("UPDATE campaigns SET status_message = ? WHERE id = ?", (message.id, campaign.id))
        self.bot.connection.commit()

    @commands.has_any_role(1050188024287338567, 873734392458145912, 809567701735440469)  # dev, admin, officer
    @commands.command()
    async def set_player_count(self, context: commands.Context, count: int, campaign: Union[int, str]):
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign)
        commit = self.bot.CampaignSQLHelper.set_max_players(campaign, count)
        if commit:
            self.bot.connection.commit()
            await self.update_status(campaign)
            await context.send(f"Set max players for {campaign.name} to {count}.")
        else:
            await context.send("An unknown error occurred.")

    @commands.has_any_role(1050188024287338567)  # dev
    @commands.command()
    async def commit(self, context):
        self.bot.connection.commit()
        await context.send("done")

    @commands.has_any_role(1050188024287338567, 873734392458145912, 809567701735440469)  # dev, admin, officer
    @commands.command()
    async def clear_waitlist(self, context: commands.Context, campaign: Union[int, str]):
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign)
        commit = self.bot.CampaignSQLHelper.clear_waitlist(campaign)
        if commit:
            await context.send(f"Cleared waitlist for {campaign.name}")
            self.bot.connection.commit()
        else:
            await context.send("An unknown error occurred.")

    @commands.command()
    async def handle_waitlist(self, context: commands.Context, campaign: Union[int, str]):
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign)
        if context.author.id != campaign.dm and not context.author.guild_permissions.administrator:
            await context.send("You are not the DM of this campaign.")
            return
        waitlisted_players = self.bot.CampaignSQLHelper.get_waitlist(campaign)
        if len(waitlisted_players) == 0:
            await context.send("No waitlisted players.")
            return
        waitlisted_players.sort(key=lambda x: x["pid"])
        member = context.guild.get_member(waitlisted_players[0]["id"])
        name = member.nick if member.nick else member.display_name
        app_channel = context.guild.get_channel(self.bot.config["applications_channel"])

        dm = await context.guild.fetch_member(campaign.dm)
        embed_ = discord.Embed(
            title=f"New Application for {campaign.name} -- from waitlist",
            timestamp=datetime.datetime.utcnow()
        )
        embed_.add_field(name="Campaign", value=campaign.name, inline=False)
        embed_.add_field(name="DM", value=str(dm), inline=False)
        embed_.add_field(name="Name", value=name)
        embed_.add_field(name="Discord", value=str(member))
        embed_.add_field(name="Discord ID", value=str(member.id))
        embed_.set_footer(text="React with a green checkmark to approve or a red X to deny.")

        to_react = await app_channel.send(dm.mention, embed=embed_)

        await to_react.add_reaction("✅")
        await to_react.add_reaction("❌")
        await context.send(to_react.jump_url)

    @commands.command()
    async def update_player_count(self, context: commands.Context, campaign: Union[int, str]):
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign)
        players = self.bot.CampaignSQLHelper.get_players(campaign)
        try:
            self.bot.db.execute(f"UPDATE campaigns SET current_players = ? WHERE id = ?", (len(players), campaign.id))
        except Exception:
            traceback.print_exc()
            await context.send("An unknown error occurred.")
            return
        self.bot.connection.commit()
        await context.send(f"Campaign {campaign.name} updated to {len(players)} players.")

    @commands.command()
    async def sync_player_count(self, context: commands.Context):
        for i in self.bot.CampaignSQLHelper.get_campaigns():
            await self.update_player_count(context, i['id'])
            await asyncio.sleep(.5)


async def setup(bot):
    await bot.add_cog(CampaignPlayerManager(bot))
