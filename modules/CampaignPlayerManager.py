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

    @commands.command()
    async def add_player(self, context: commands.Context, member: discord.Member, campaign_id: Union[int, str]):
        campaign: CampaignInfo = self.bot.CampaignSQLHelper.select_campaign(campaign_id)
        guest_role = context.guild.get_role(self.bot.config["guest_role"])
        member_role = context.guild.get_role(self.bot.config["member_role"])
        campaign_role = context.guild.get_role(campaign.role)
        await member.remove_roles(guest_role)
        await member.add_roles(member_role, campaign_role)
        self.bot.CampaignSQLHelper.add_player(campaign, member)

        if campaign.current_players + 1 == campaign.min_players:
            category: discord.CategoryChannel = context.guild.get_channel(campaign.category)
            for i in category.channels:
                if i.name == "lobby":
                    await i.send("This campaign now meets its minimum player goal!")

    @commands.command()
    async def remove_player(self, context: commands.Context, member: discord.Member, campaign_id: Union[int, str]):
        campaign: CampaignInfo = self.bot.CampaignSQLHelper.select_campaign(campaign_id)
        guest_role = context.guild.get_role(self.bot.config["guest_role"])
        member_role = context.guild.get_role(self.bot.config["member_role"])
        campaign_role = context.guild.get_role(campaign.role)

        await member.remove_roles(campaign_role)
        campaign_roles = self.bot.CampaignSQLHelper.select_field("role")
        guest = True
        for i in campaign_roles:
            if i in member.roles:
                guest = False

        if guest:
            await member.remove_roles(member_role)
            await member.add_roles(guest_role)

        self.bot.CampaignSQLHelper.remove_player(campaign, member)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.apply(message)

    async def apply(self, message):
        if not message.channel.id == 887340491333591100:
            return
        if not message.embeds: return
        found_embed = message.embeds[0]
        if found_embed is None or found_embed == discord.Embed.Empty:
            return
        campaigns = []
        campaign_name = ""
        name = found_embed.fields[0].value + " " + found_embed.fields[1].value
        member = message.guild.get_member_named(found_embed.fielsd[2].value)
        for i in found_embed.fields[9::]:
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
            embed.set_footer(text="React with a green checkmark to approve or a red X to deny.")

            await message.channel.send(dm.mention, embed=embed)

        await message.add_reaction("✅")


def setup(bot):
    bot.add_cog(CampaignPlayerManager(bot))