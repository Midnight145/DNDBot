import datetime
from typing import Union, TYPE_CHECKING

import discord
from discord.ext import commands

from modules import CampaignInfo

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..bot import DNDBot


class CampaignPlayerManager(commands.Cog):
    def __init__(self, bot: 'DNDBot'):
        self.bot = bot
        self.bot.CampaignPlayerManager = self

    @commands.command(aliases=["add_player"])
    async def add_player_command(self, context: commands.Context, member: discord.Member, campaign_id: Union[int, str]):
        await self.add_player(context.channel, member, campaign_id)

    async def add_player(self, channel: discord.TextChannel, member: discord.Member, campaign_id: Union[int, str], waitlisted=False) -> bool:
        campaign_id: CampaignInfo = self.bot.CampaignSQLHelper.select_campaign(campaign_id)
        if member.id == campaign_id.dm:
            await channel.send("You cannot join your own campaign.")
            return False
        guest_role = channel.guild.get_role(self.bot.config["guest_role"])
        member_role = channel.guild.get_role(self.bot.config["member_role"])
        campaign_role = channel.guild.get_role(campaign_id.role)

        if campaign_id.current_players >= campaign_id.max_players:
            self.bot.CampaignSQLHelper.waitlist_player(campaign_id, member)
            await channel.send(f"{member.display_name} has been added to the waitlist.")
            return True
        if waitlisted:
            commit = self.bot.CampaignSQLHelper.unwaitlist(campaign_id, member)
        else:
            commit = self.bot.CampaignSQLHelper.add_player(campaign_id, member)
        if commit:
            try:
                await member.send(f"{member.display_name}: This is a notification that you have been approved and added to a "
                              f"campaign. If you ever wish to leave the campaign, please use the Leave a Campaign "
                              f"form found in #how-to-join. Campaign: {campaign_id.name}.")
            except (discord.Forbidden, discord.HTTPException):
                pass

            await member.remove_roles(guest_role)
            await member.add_roles(member_role, campaign_role)

            if campaign_id.current_players + 1 == campaign_id.min_players:
                category: discord.CategoryChannel = channel.guild.get_channel(campaign_id.category)
                for i in category.channels:
                    if i.name == "lobby":
                        await i.send("This campaign now meets its minimum player goal!")
            await channel.send(f"{member.mention} has been added to the campaign!")
            self.bot.connection.commit()
            return True
        else:
            await channel.send("An unknown error occurred.")
            return False

    @commands.command()
    async def remove_player(self, context: commands.Context, member: discord.Member, campaign_id: Union[int, str]):
        campaign: CampaignInfo = self.bot.CampaignSQLHelper.select_campaign(campaign_id)
        guest_role = context.guild.get_role(self.bot.config["guest_role"])
        member_role = context.guild.get_role(self.bot.config["member_role"])
        campaign_role = context.guild.get_role(campaign.role)

        commit = self.bot.CampaignSQLHelper.remove_player(campaign, member)
        if commit:
            await member.remove_roles(campaign_role)
            campaign_roles = self.bot.CampaignSQLHelper.select_field("role")
            guest = True
            for i in campaign_roles:
                if i in member.roles:
                    guest = False

            if guest:
                await member.remove_roles(member_role)
                await member.add_roles(guest_role)
            await context.send(f"{member.mention} has been removed from the campaign!")
            self.bot.connection.commit()
            if campaign.current_players - 1 < campaign.max_players:
                waitlisted_players = self.bot.CampaignSQLHelper.get_waitlist(campaign)
                if len(waitlisted_players) > 0:
                    await self.bot.CampaignPlayerManager.add_player(context.channel, context.guild.get_member(waitlisted_players[0]["id"]), campaign.name, True)
        else:
            await context.send("An unknown error occurred.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        await self.apply(message)

    async def apply(self, message):
        if not message.channel.id == self.bot.config["receipt_channel"]:
            return
        if not message.embeds:
            return
        found_embed = message.embeds[0]
        if found_embed is None or found_embed == discord.Embed.Empty:
            return
        campaigns = []
        campaign_name = ""
        name = found_embed.fields[0].value + " " + found_embed.fields[1].value
        member = message.guild.get_member(int(found_embed.fields[2].value))
        channel = message.guild.get_channel(self.bot.config["applications_channel"])
        for i in found_embed.fields[10::]:
            if "which of the following" not in i.name.lower():
                continue
            campaign_name = i.value
            if "(waitlist)" in i.value:
                campaign_name = i.value[:-11]
            campaigns.append(self.bot.CampaignSQLHelper.select_campaign(campaign_name))

        for i in campaigns:
            dm = message.guild.get_member(i.dm)
            embed = discord.Embed(
                title=f"New Application for {campaign_name}",
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Campaign", value=campaign_name, inline=False)
            embed.add_field(name="DM", value=str(dm), inline=False)
            embed.add_field(name="Name", value=name)
            embed.add_field(name="Discord", value=str(member))
            embed.add_field(name="Discord ID", value=str(member.id))
            embed.set_footer(text="React with a green checkmark to approve or a red X to deny.")

            to_react = await channel.send(dm.mention, embed=embed)

            await to_react.add_reaction("✅")
            await to_react.add_reaction("❌")

    @commands.command()
    async def update_campaign_players(self, context: commands.Context, campaign_id: Union[int, str]):
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_id)
        campaign_role = context.guild.get_role(campaign.role)

        members = campaign_role.members

        for i in members:
            await self.bot.CampaignPlayerManager.add_player(context.channel, i, campaign_id)

        await context.send("Campaign players updated.")


def setup(bot):
    bot.add_cog(CampaignPlayerManager(bot))
