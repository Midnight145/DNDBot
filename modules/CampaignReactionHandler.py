import datetime
import re
import typing
from enum import IntEnum
from typing import TYPE_CHECKING, Callable, Awaitable

import discord
from discord.ext import commands

from . import CampaignInfo
from .Strings import Confirmation, Error
from .api.CampaignActionHandler import ActionHandler

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..DNDBot import DNDBot


class CampaignReactionHandler(commands.Cog):
    def __init__(self, bot: 'DNDBot'):
        self.bot = bot
        self.finished_waitlist = []

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        :param payload: Payload from reaction add event
        :return: None
        """

        class FieldValuesWebsite(IntEnum):
            first_name = 0
            last_name = 1
            unt_email = 2
            discord_tag = 3
            discord_id = 4
            dm_experience = 5
            playstyle = 6
            campaign_name = 7
            info_message = 8
            system = 9
            location = 10
            meeting_frequency = 11
            meeting_day = 12
            meeting_time = 13
            session_length = 14
            min_players = 15
            max_players = 16
            new_player_friendly = 17

        class FieldValues(IntEnum):
            first_name = 0
            last_name = 1
            discord_username = 2
            unt_email = 3
            meeting_day = 4
            meeting_time = 5
            location = 6
            meeting_frequency = 7
            system = 8
            campaign_name = 9
            info_message = 10
            dm_experience = 11
            playstyle = 12
            new_player_friendly = 13
            session_length = 14
            min_players = 15
            max_players = 16

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

            if "waitlist" in message.embeds[0].title.lower() and message.embeds[0].title not in self.finished_waitlist:
                await self.handle_waitlist(message, payload)
                self.finished_waitlist.append(message.embeds[0].title)
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

        if channel.id == self.bot.config["dm_receipts"]:
            print("Parsing new DM receipt")
            roles = [self.bot.config["admin_role"], self.bot.config["developer_role"]]
            if not any(role in [role.id for role in payload.member.roles] for role in roles):
                print("User is not an admin or developer")
                return
            if not message.embeds:
                print("No embeds found")
                return
            embed = message.embeds[0]
            if payload.emoji.name == "✅":
                print("DM receipt approved")
                website = False
                if "website" in embed.title.lower():
                    print("Website application detected")
                    website = True
                if website:
                    print(embed.fields[FieldValuesWebsite.discord_id].value)
                    dm = channel.guild.get_member(int(embed.fields[FieldValuesWebsite.discord_id].value))
                    print(dm)
                    campaign_info = await self.bot.CampaignBuilder.create_campaign(
                        channel.guild, embed.fields[FieldValuesWebsite.campaign_name].value, embed.fields[FieldValuesWebsite.location].value, dm)

                    campaign_info.min_players = int(embed.fields[FieldValuesWebsite.min_players].value)
                    campaign_info.max_players = int(embed.fields[FieldValuesWebsite.max_players].value)
                    campaign_info.location = embed.fields[FieldValuesWebsite.location].value
                    campaign_info.playstyle = embed.fields[FieldValuesWebsite.playstyle].value
                    campaign_info.info_message = embed.fields[FieldValuesWebsite.info_message].value
                    campaign_info.system = embed.fields[FieldValuesWebsite.system].value
                    campaign_info.meeting_frequency = embed.fields[FieldValuesWebsite.meeting_frequency].value
                    if "Day" in embed.fields[FieldValuesWebsite.meeting_day].name:
                        campaign_info.meeting_day = embed.fields[FieldValuesWebsite.meeting_day].value
                        campaign_info.meeting_date = ""
                    else:
                        campaign_info.meeting_day = ""
                        campaign_info.meeting_date = embed.fields[FieldValuesWebsite.meeting_day].value
                    campaign_info.meeting_time = embed.fields[FieldValuesWebsite.meeting_time].value
                    campaign_info.session_length = embed.fields[FieldValuesWebsite.session_length].value
                    campaign_info.new_player_friendly = embed.fields[FieldValuesWebsite.new_player_friendly].value
                else:
                    dm = channel.guild.get_member_named(embed.fields[FieldValues.discord_username].value)
                    campaign_info = await self.bot.CampaignBuilder.create_campaign(
                        channel.guild, embed.fields[FieldValues.campaign_name].value, embed.fields[FieldValuesWebsite.location].value, dm)

                    campaign_info.min_players = int(embed.fields[FieldValues.min_players].value)
                    campaign_info.max_players = int(embed.fields[FieldValues.max_players].value)
                    campaign_info.location = embed.fields[FieldValues.location].value
                    campaign_info.playstyle = embed.fields[FieldValues.playstyle].value
                    campaign_info.info_message = embed.fields[FieldValues.info_message].value
                    campaign_info.system = embed.fields[FieldValues.system].value
                    campaign_info.meeting_frequency = embed.fields[FieldValues.meeting_frequency].value
                    if "Day" in embed.fields[FieldValues.meeting_day].name:
                        campaign_info.meeting_day = embed.fields[FieldValues.meeting_day].value
                        campaign_info.meeting_date = ""
                    else:
                        campaign_info.meeting_day = ""
                        campaign_info.meeting_date = embed.fields[FieldValues.meeting_day].value
                    campaign_info.meeting_time = embed.fields[FieldValues.meeting_time].value
                    campaign_info.session_length = embed.fields[FieldValues.session_length].value
                    campaign_info.new_player_friendly = embed.fields[FieldValues.new_player_friendly].value

                commit = self.bot.CampaignSQLHelper.create_campaign(campaign_info)
                if commit:
                    self.bot.connection.commit()
                    await message.delete()
                    await channel.send(f"Campaign {campaign_info.name} has been created!")
                    if website:
                        info = self.bot.CampaignSQLHelper.select_campaign(campaign_info.name)
                        await self.bot.campaign_creation_callback(campaign=info)
                        return
                else:
                    await channel.send("An unknown error occurred while creating the campaign.")

            elif payload.emoji.name == "❌":
                print("DM receipt denied")
                await message.delete()

        if channel.id == self.bot.config["campaign_action_channel"]:
            success = await self.handle_campaign_action(message, payload)
            if success is None:
                return
            if not success:
                await message.remove_reaction(payload.emoji, payload.member)
            else:
                await message.delete()

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
            description=Confirmation.CONFIRM_PLAYER_VERIFICATION_DENIED.format(channel=member.guild.get_channel(self.bot.config['verification_channel'])),
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow()
        )
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            await self.bot.get_channel(self.bot.config["verification_channel"]).send(Error.ERROR_VERIFICATION_CLOSED_DMS.format(member=member))
        return False

    async def approve_player(self, message: discord.Message, member: discord.Member, reactor: discord.Member):
        """
        :param message: Message retrieved from reaction payload
        :param member: Member to approve
        :param reactor: Member who reacted, probably the DM
        :return: None
        """
        async with self.bot.mutex:
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
                    await message.channel.send(Error.ERROR_UNK)
                    return

    async def deny_player(self, message: discord.Message, member: discord.Member, reactor: discord.Member) -> None:
        """
        :param message: Message retrieved from reaction payload
        :param member: Member to deny
        :param reactor: Member who reacted, probably the DM
        :return: None
        """
        async with self.bot.mutex:
            channel = self.bot.get_channel(self.bot.config["player-sign-up"])
            message_embed = message.embeds[0]
            campaign_name = message_embed.fields[0].value
            campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_name)
            dm = await message.guild.fetch_member(campaign.dm)

            if reactor.id != dm.id:
                return
            await self.bot.try_send_message(member, channel,
                                            Confirmation.CONFIRM_PLAYER_CAMPAIGN_DENIED.format(member=member,
                                                                                               campaign=campaign))
            await message.delete()
            await channel.send(Confirmation.CONFIRM_DM_CAMPAIGN_DENIED.format(member=member, campaign=campaign))

    @staticmethod
    async def __create_waitlist_embed(member: discord.Member, campaign: CampaignInfo) -> discord.Embed:
        name = member.nick if member.nick else member.display_name

        dm = await member.guild.fetch_member(campaign.dm)
        embed = discord.Embed(
            title=f"New Application for {campaign.name} -- from waitlist",
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Campaign", value=campaign.name, inline=False)
        embed.add_field(name="DM", value=str(dm), inline=False)
        embed.add_field(name="Name", value=name)
        embed.add_field(name="Discord", value=str(member))
        embed.add_field(name="Discord ID", value=str(member.id))
        embed.set_footer(text="React with a green checkmark to approve or a red X to deny.")

        return embed

    async def handle_waitlist(self, message, payload: discord.RawReactionActionEvent):
        """
        :param message: Message retrieved from payload
        :param payload: Reaction payload
        :return: None
        """

        async def unwaitlist_apply():
            embed_ = await self.__create_waitlist_embed(member, campaign)
            dm = await member.guild.fetch_member(campaign.dm)
            app_channel = self.bot.get_channel(self.bot.config["applications_channel"])

            to_react = await app_channel.send(dm.mention, embed=embed_)

            await to_react.add_reaction("✅")
            await to_react.add_reaction("❌")
        async with self.bot.mutex:
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
                waitlisted_players = self.bot.CampaignSQLHelper.get_waitlisted_players(campaign)
                waitlisted_players.sort(key=lambda x: x['pid'])
                if len(waitlisted_players) > 0:
                    member = await message.guild.fetch_member(waitlisted_players[0]['id'])
                    await unwaitlist_apply()

    async def approve_waitlisted_player(self, message: discord.Message, member: discord.Member,
                                        reactor: discord.Member):
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
            waitlisted_players = self.bot.CampaignSQLHelper.get_waitlisted_players(campaign)
            if member.id in [player['id'] for player in waitlisted_players]:
                await channel.send(f"{member.mention} is already on the waitlist for {campaign.name}.")
                return
            commit = self.bot.CampaignSQLHelper.waitlist_player(campaign, member)
            if commit:
                await channel.send(f"{member.mention} has been added to the campaign {campaign.name}'s waitlist")
                await message.delete()
                self.bot.connection.commit()
            else:
                await message.channel.send("An unknown error occurred while adding the player to the waitlist.")
        if await self.bot.CampaignPlayerManager.add_player(message.channel, member, campaign_name, waitlisted=True):
            await channel.send(f"{member.mention} has been added to the campaign {campaign.name}'s waitlist")
            await message.delete()
        else:
            await message.channel.send(Error.ERROR_UNK)
            return

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
        await self.bot.try_send_message(member, channel, Confirmation.CONFIRM_PLAYER_WAITLIST_DENY.format(member=member,
                                                                                                          campaign=campaign))
        if self.bot.CampaignSQLHelper.remove_player(campaign, member):
            self.bot.connection.commit()
            await message.delete()
            await channel.send(Confirmation.CONFIRM_DM_WAITLIST_DENY.format(member=member, campaign=campaign))
        else:
            await channel.send(f"An unknown error occurred while removing the {member.mention} "
                               f"from the waitlist for {campaign.name}.")


    async def handle_campaign_action(self, message: discord.Message, payload: discord.RawReactionActionEvent) -> typing.Optional[bool]:
        """
        Handles campaign actions retrieved from the API
        :param message: Message retrieved from payload
        :param payload: Reaction payload
        :return: Whether the action was successful or not
        """
        async with self.bot.mutex:
            if not message.embeds:
                return False
            embed = message.embeds[0]
            reactor = message.guild.get_member(payload.user_id)
            if self.bot.config["admin_role"] not in [role.id for role in reactor.roles]:
                return False
            if "submission" in embed.title.lower():
                return
            if payload.emoji == "❌":
                await message.delete()
                return True
            elif payload.emoji == "✅":
                regex = re.compile(r"(\w+) \w+$")  # hacky way to get the action from the title
                action = regex.search(embed.title).group(1).lower()
                campaign_name = embed.fields[3].value
                campaign = self.bot.CampaignSQLHelper.select_campaign(campaign_name)
                func: Callable[['DNDBot', discord.TextChannel, int, discord.Embed], Awaitable[bool]] = (
                    getattr(ActionHandler, action))  # wow, this is a hack
                return await func(self.bot, message.channel, campaign.id, embed)


async def setup(bot):
    await bot.add_cog(CampaignReactionHandler(bot))
