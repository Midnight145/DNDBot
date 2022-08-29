import datetime
import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

#from modules import Strings
import bot
from .CampaignBuilder import verification_denied

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..bot import DNDBot


class CampaignReactionHandler(commands.Cog):
    def __init__(self, bot: 'DNDBot'):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        :param payload: The reaction payload
        :return: None
        """
        channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)  # queuing bot for text channel

        if isinstance(channel, discord.VoiceChannel):
            return

        message: discord.Message = await channel.fetch_message(payload.message_id)  # fetching message from text channel

        if channel.id == self.bot.config["verification_channel"]:
            success = await self.verify(payload.member)
            if not success:
                # remove reaction if verification failed
                await message.remove_reaction(payload.emoji, payload.member)
            return

        if channel.id == self.bot.config["applications_channel"]:
            if not message.embeds:
                return
            embed = message.embeds[0]
            discord_id = int(embed.fields[4].value)
            member = await message.guild.fetch_member(discord_id)
            if message.author.id != self.bot.user.id:  # if message author is not the bot
                return
            if payload.emoji.name == "✅":
                await self.approve_player(message, member, payload.member)

            elif payload.emoji.name == "❌":
                await self.deny_player(message, member, payload.member)

    async def verify(self, member: discord.Member) -> bool:
        """
        :param member: Member to be verified
        :return: Whether verification was successful or not
        """
        pattern = re.compile(self.bot.config["verified_regex"])
        match = pattern.fullmatch(member.display_name)
        if match:
            await member.add_roles(member.guild.get_role(self.bot.config["verified_role"]))
            return True

        embed = discord.Embed(
            title="Verification Denied",
            description=verification_denied(self.bot.config['verification_channel']),
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            await self.bot.get_channel(self.bot.config["verification_channel"]).send(f"{member.mention}: I was unable to DM you. Please open your DMs to this server, as I will send campaign updates via DM in the future. Once you have done that, you will need to re-react to the verification reaction.")
        return False

    async def approve_player(self, message: discord.Message, member: discord.Member, reactor: discord.Member):
        """
        :param message: Message retrieved from reaction payload
        :param member: Member to approve
        :param reactor: Member who reacted, probably the DM
        :return: None
        """
        message_embed = message.embeds[0]
        campaign_name = message_embed.fields[0].value
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_name)
        dm = await message.guild.fetch_member(campaign.dm)
        player_name = message_embed.fields[2].value
        discord_tag = message_embed.fields[3].value
        player_discord = message_embed.fields[4].value

        player = await message.guild.fetch_member(int(player_discord))

        if reactor.id != dm.id:
            return

        if campaign.current_players >= campaign.max_players:
            commit = self.bot.CampaignSQLHelper.waitlist_player(campaign, member)
            if commit:
                await message.add_reaction("⏸️")
                self.bot.connection.commit()
            else:
                await message.channel.send("An unknown error occured while adding the player to the waitlist.")
        else:
            if await self.bot.CampaignPlayerManager.add_player(message.channel, member, campaign_name):
                await message.add_reaction("☑️")
            else:
                await message.channel.send("An unknown error occured.")
                return
        await message.clear_reaction("✅")
        await message.clear_reaction("❌")
        await self.bot.CampaignPlayerManager.update_status(campaign)

    async def deny_player(self, message: discord.Message, member: discord.Member, reactor: discord.Member) -> None:
        """
        :param message: Message retrieved from reaction payload
        :param member: Member to deny
        :param reactor: Member who reacted, probably the DM
        :return: None
        """
        message_embed = message.embeds[0]
        campaign_name = message_embed.fields[0].value
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_name)
        dm = await message.guild.fetch_member(campaign.dm)
        player_name = message_embed.fields[2].value
        player_discord = int(message_embed.fields[4].value)

        player = await message.guild.fetch_member(int(player_discord))

        if reactor.id != dm.id:
            return

        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_name)
        await player.send(f"You have been denied from {campaign_name}. This is an automated message. If you believe this to be a mistake, please contact the Campaign Master.")
        await message.add_reaction("🇽")
        await message.clear_reaction("✅")
        await message.clear_reaction("❌")


def setup(bot):
    bot.add_cog(CampaignReactionHandler(bot))
