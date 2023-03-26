import datetime
import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .CampaignBuilder import verification_denied

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..bot import DNDBot


class CampaignReactionHandler(commands.Cog):
    def __init__(self, bot: 'DNDBot'):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        :param payload: Payload from reaction add event
        :return: None
        """
        if payload.user_id == self.bot.user.id:
            return
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

            if "waitlist" in message.embeds[0].title.lower():
                await self.handle_waitlist(message, payload)
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
            await self.bot.get_channel(self.bot.config["verification_channel"]).send(f"{member.mention}: I was unable "
                                                                                     f"to DM you. Please open your "
                                                                                     f"DMs to this server, "
                                                                                     f"as I will send campaign "
                                                                                     f"updates via DM in the future. "
                                                                                     f"Once you have done that, "
                                                                                     f"you will need to re-react to "
                                                                                     f"the verification reaction.")
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

        channel = self.bot.get_channel(self.bot.config["player-sign-up"])
        if reactor.id != dm.id:
            return

        if campaign.current_players >= campaign.max_players:
            commit = self.bot.CampaignSQLHelper.waitlist_player(campaign, member)
            if commit:
                await channel.send(f"{member.mention} has been added to the campaign {campaign.name}'s waitlist")
                await message.delete()
                self.bot.connection.commit()
            else:
                await message.channel.send("An unknown error occurred while adding the player to the waitlist.")
        else:
            if await self.bot.CampaignPlayerManager.add_player(message.channel, member, campaign_name):
                await channel.send(f"{member.mention} has been added to the campaign {campaign_name}!")
                await message.delete()
            else:
                await message.channel.send("An unknown error occurred.")
                return
        await self.bot.CampaignPlayerManager.update_status(campaign)

    async def deny_player(self, message: discord.Message, member: discord.Member, reactor: discord.Member) -> None:
        """
        :param message: Message retrieved from reaction payload
        :param member: Member to deny
        :param reactor: Member who reacted, probably the DM
        :return: None
        """

        channel = self.bot.get_channel(self.bot.config["player-sign-up"])
        message_embed = message.embeds[0]
        campaign_name = message_embed.fields[0].value
        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_name)
        dm = await message.guild.fetch_member(campaign.dm)

        if reactor.id != dm.id:
            return

        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_name)
        await member.send(f"You have been denied from {campaign_name}. This is an automated message. If you believe "
                          f"this to be a mistake, please contact the Campaign Master.")
        await message.delete()
        await channel.send(f"{member.mention} application for the campaign {campaign.name} has been denied by the DM.")

    async def handle_waitlist(self, message, payload: discord.RawReactionActionEvent):
        """
        :param message: Message retrieved from reaction payload
        :param payload: Reaction payload
        :return: None
        """
        async def unwaitlist_apply():
            name = member.nick if member.nick else member.display_name
            app_channel = channel.guild.get_channel(self.bot.config["applications_channel"])

            dm = await channel.guild.fetch_member(campaign.dm)
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
            await self.bot.CampaignPlayerManager.update_status(campaign)

        channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)  # queuing bot for text channel
        embed = message.embeds[0]
        discord_id = int(embed.fields[4].value)
        member = await message.guild.fetch_member(discord_id)
        if message.author.id != self.bot.user.id:  # if message author is not the bot
            return
        if payload.emoji.name == "✅":
            await self.approve_waitlisted_player(message, member, payload.member)

        elif payload.emoji.name == "❌":
            await self.deny_waitlisted_player(message, member, payload.member)
            campaign_name = embed.fields[0].value
            campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_name)
            await unwaitlist_apply()

    async def approve_waitlisted_player(self, message: discord.Message, member: discord.Member, reactor: discord.Member):
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

        channel = self.bot.get_channel(self.bot.config["player-sign-up"])

        if reactor.id != dm.id:
            return

        if await self.bot.CampaignPlayerManager.add_player(message.channel, member, campaign_name, waitlisted=True):
            await channel.send(f"{member.mention} has been added to the campaign {campaign.name}'s waitlist")
            await message.delete()
        else:
            await message.channel.send("An unknown error occurred.")
            return
        #await message.clear_reaction("✅")
        #await message.clear_reaction("❌")
        await self.bot.CampaignPlayerManager.update_status(campaign)

    async def deny_waitlisted_player(self, message: discord.Message, member: discord.Member, reactor: discord.Member):
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
        channel = self.bot.get_channel(self.bot.config["player-sign-up"])

        if reactor.id != dm.id:
            return

        campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_name)
        try:
            await member.send(f"You have been denied from {campaign_name}, which you were on the waitlist for. This "
                              f"is an automated message. If you believe this to be a mistake, please contact the "
                              f"Campaign Master.")
            if self.bot.CampaignSQLHelper.remove_player(campaign, member):
                self.bot.connection.commit()
                await message.delete()
                await channel.send(f"{member.mention} waitlisted application for the campaign {campaign.name} has "
                                   f"been denied by the DM.")
            else:
                await channel.send(f"An unknown error occurred while removing the {member.mention} "
                                   f"from the waitlist for {campaign.name}.")
        except discord.errors.Forbidden:
            pass


def setup(bot):
    bot.add_cog(CampaignReactionHandler(bot))
