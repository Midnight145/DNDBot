import sys

import discord
from discord.ext import commands
import datetime
from typing import Union, TYPE_CHECKING
from .CampaignInfo import CampaignInfo
from .errorhandler import TracebackHandler

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..bot import DNDBot


class CampaignManager(commands.Cog):
    def __init__(self, bot: 'DNDBot'):
        self.bot = bot
        self.CampaignBuilder = self.bot.CampaignBuilder
        self.CampaignSQLHelper = self.bot.CampaignSQLHelper

    @commands.command(aliases=["register"])
    async def register_campaign(self, context: commands.Context, name: str, role: discord.Role,
                                category: discord.CategoryChannel, information_channel: discord.TextChannel,
                                dm: discord.Member, min_players: str, max_players: str, current_players: str):
        """
        :param context: Command context
        :param name: Campaign name
        :param role: Campaign role
        :param category: Campaign category
        :param information_channel: Campaign "global" information channel
        :param dm: Campaign DM
        :param min_players: Minimum number of players necessary to start
        :param max_players: Maximum number of players allowed
        :param current_players: Current number of players in the campaign
        :return: None
        """
        campaign_info = CampaignInfo()
        campaign_info.name = name
        campaign_info.role = role.id
        campaign_info.category = category.id
        campaign_info.information_channel = information_channel.id
        campaign_info.dm = dm.id
        campaign_info.min_players = int(min_players)
        campaign_info.max_players = int(max_players)
        campaign_info.current_players = int(current_players)

        commit = self.CampaignSQLHelper.create_campaign(campaign_info)
        if commit:
            embed = discord.Embed(
                title="Campaign Registered",
                description=f"Campaign {name} Registered.",
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="DM", value=f"{str(dm)} ({dm.id})")
            embed.add_field(name="Role", value=str(context.guild.get_role(campaign_info["role"])))
            embed.add_field(name="Category", value=str(context.guild.get_channel(campaign_info["category"]).name))
            embed.add_field(name="Max Players", value=f"{max_players}")

            await context.send(embed=embed)
            self.bot.connection.commit()
        else:
            await context.send("Something went wrong.")

    @commands.command()
    async def delete_category(self, context: commands.Context, category: discord.CategoryChannel):
        """
        :param context: Command context
        :param category: Category to delete
        :return: None
        """
        for i in category.channels:
            await i.delete()
        await category.delete()
        await context.send(f"Category {category.name} deleted.")

    @commands.command()
    @commands.has_any_role("Officer", "Dungeon Master")
    async def create_campaign(self, context: commands.Context, name: str, dungeon_master: discord.Member,
                              min_players: int, max_players: int):
        """
        :param context: Command context
        :param name: Campaign name
        :param dungeon_master: Campaign DM, can be Union[str, int] as it is typecast
        :param min_players: Minimum number of players necessary to start
        :param max_players: Maximum number of players allowed
        :return: None
        """

        campaign_info = await self.CampaignBuilder.create_campaign(context, name, dungeon_master, min_players,
                                                                   max_players)

        commit = self.CampaignSQLHelper.create_campaign(campaign_info)
        if commit:
            embed = discord.Embed(
                title="Campaign Created",
                description=f"Campaign {name} created.",
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="DM", value=f"{str(dungeon_master)} ({dungeon_master.id})")
            embed.add_field(name="Role", value=str(context.guild.get_role(campaign_info["role"])))
            embed.add_field(name="Category", value=str(context.guild.get_channel(campaign_info["category"]).name))
            embed.add_field(name="Max Players", value=f"{max_players}")
            await context.send(embed=embed)

            self.bot.connection.commit()
        #    await self.bot.CampaignPlayerManager.update_status(campaign_info)
            await (context.guild.get_channel(self.bot.config["notification_channel"])).send(
                f"<@&{self.bot.config['new_campaign_role']}>: A new campaign has opened: "
                f"<#{campaign_info.information_channel}> run by <@{campaign_info.dm}>! "
                f"Sign up in <#{812549890227437588}>")
        else:
            await context.send("Something went wrong.")

    @commands.command()
    @commands.has_any_role("Officer", "Dungeon Master")
    async def delete_campaign(self, context: commands.Context, campaign: Union[int, str], *, reason="Campaign deleted"):
        """
        :param context: Command context
        :param campaign: Either campaign name (wrapped in quotes) or campaign ID
        :param reason: The reason the campaign was deleted, DM'd to the members of the campaign.
        :return: None
        """

        resp = self.CampaignSQLHelper.select_campaign(campaign)
        members = [i["id"] for i in self.CampaignSQLHelper.get_players(resp)]

        commit = self.CampaignSQLHelper.delete_campaign(campaign)

        commit2 = await self.CampaignBuilder.delete_campaign(resp)

        status_channel = context.guild.get_channel(self.bot.config["status_channel"])
        status_message = await status_channel.fetch_message(resp.status_message)
        await status_message.delete()

        if commit:
            await context.send(f"Campaign \"{resp.name}\" deleted.")
            self.bot.connection.commit()
        else:
            await context.send(f"There was an error deleting \"{resp.name}\"")
            await self.handle_error()

            return

        if commit2 is None:
            await context.send(f"There was an error deleting \"{resp.name}\", fuck if I know what happened. Ping "
                               f"Ryan, he'll know what to do.")
            return

        for member_id in members:
            member = context.guild.get_member(member_id)
            if member is None:
                await context.send(f"Member {member_id} not found- this shouldn't happen, but it did. Ping Ryan, he'll know what "
                                   f"to do.")
                continue
            try:
                await member.send(f'You have been removed from a campaign due to it being ended by its DM or the '
                                  f'President. Campaign: {resp.name}. Reason: {reason}.')
            except discord.Forbidden:
                await context.send(f"Member {str(member)} has DMs disabled, they will not be notified of their "
                                   f"removal from the campaign.")

    @commands.command()
    async def rename_campaign(self, context: commands.Context, campaign: Union[int, str], *, name: str):
        """
        :param context: Command context
        :param campaign: Either campaign name (wrapped in quotes) or campaign ID
        :param name: New campaign name
        :return: None
        """

        resp = self.CampaignSQLHelper.select_campaign(campaign)
        commit = self.CampaignSQLHelper.rename_campaign(resp, name)
        resp2 = self.CampaignSQLHelper.select_campaign(campaign)

        if commit:
            await context.send(f"Campaign \"{resp.name}\" renamed to \"{name}\".")
            self.bot.connection.commit()
            # update status
            await self.bot.CampaignPlayerManager.update_status(resp2)

        else:
            await context.send(f"There was an error renaming \"{resp.name}\"")
            await self.handle_error()

    @commands.command()
    async def message_players_campaign_deleted(self, context: commands.Context, role: discord.Role):
        for member in role.members:
            try:
                await member.send(f'You have been removed from a campaign due to it being ended by its DM or the '
                                  f'President. Campaign: {role.name}.')
            except discord.Forbidden:
                await context.send(f"Member {str(member)} has DMs disabled, they will not be notified of their "
                                   f"removal from the campaign.")
        await context.send("Players messaged.")
        await role.delete()
        await context.send(f"Role {role.name} deleted.")

    @commands.command()
    @commands.has_any_role("Officer", "Dungeon Master")
    async def drop_campaign(self, context: commands.Context, campaign: Union[int, str]):
        """
        Will drop a campaign from the database without deleting any channels
        :param context: Command context
        :param campaign: Either campaign name or campaign ID
        :return: None
        """
        if self.CampaignSQLHelper.delete_campaign(campaign):
            await context.send(f"Campaign {campaign} deregistered.")
            self.bot.connection.commit()

    @commands.command()
    async def list_campaigns(self, context: commands.Context):
        """
        :param context: Command context
        :return: None
        """
        message_content = ""
        resp = self.bot.db.execute(f"SELECT * FROM campaigns").fetchall()
        for row in resp:
            message_content += f"{row['id']}: {row['name']}, DM: {str(context.guild.get_member(row['dm']))}, " \
                               f"{row['current_players']}/{row['max_players']}\n"

        await context.send(message_content)

    @commands.command()
    async def list_players(self, context: commands.Context, campaign: Union[int, str]):
        campaign = self.CampaignSQLHelper.select_campaign(campaign)
        players = self.CampaignSQLHelper.get_players(campaign)
        message = ""
        if players is None:
            await context.send("An error occurred.")
            return
        for i in players:
            if (member := context.guild.get_member(i["id"])) is not None:
                message += f"{member.display_name} ({member.id})\n"
            else:
                message += f"Could not resolve user {i['id']} -- Perhaps they left?\n"
        await context.send(message)

    async def handle_error(self):
        exc_type, exc_name, exc_traceback = sys.exc_info()
        channel = self.bot.get_channel(self.bot.config["staff_botspam"])
        err_code = 255
        for i in range(len(self.bot.traceback) + 1):
            if i in self.bot.traceback:
                continue
            err_code = i
        original = getattr(exc_traceback, '__cause__', exc_traceback)
        handler = TracebackHandler(err_code, f"{exc_type.__name__}: {str(exc_name)}", original)
        self.bot.traceback[err_code] = handler
        await channel.send(f"An error occurred. Error code: {str(err_code)}")


async def setup(bot):
    await bot.add_cog(CampaignManager(bot))
