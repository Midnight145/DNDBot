import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from modules import CampaignInfo

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..DNDBot import DNDBot

from .Strings import New


class CampaignBuilder(commands.Cog):
    """
    WILL NEVER COMMIT TO DATABASE
    """

    def __init__(self, bot: 'DNDBot'):
        self.bot = bot

    # noinspection PyMethodMayBeStatic
    async def create_campaign(self, guild: discord.Guild, name: str, location: str, dm: discord.Member) -> CampaignInfo:
        """
        Creates all the necessary channels when creating a new campaign
        :param guild: Guild to create campaign in
        :param name: Campaign name
        :param dm: Campaign dm
        :return: CampaignInfo object
        """

        # return value
        retval = CampaignInfo()
        retval.name = name
        retval.current_players = 0
        retval.dm = dm.id
        retval.locked = 0
        retval.timestamp = int(time.time())

        verified = guild.get_role(809567701407629371)
        member = guild.get_role(950470805538611200)
        player = guild.get_role(809567701735440467)

        # create campaign role
        role = await guild.create_role(reason="new campaign", name=name, mentionable=True)
        # add campaign role to CampaignInfo object
        retval.role = role.id

        # handle permission overwrites
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False),
                      role: discord.PermissionOverwrite(read_messages=True),
                      dm: discord.PermissionOverwrite(manage_channels=True, manage_permissions=True,
                                                      send_messages=True, manage_messages=True)
                      }
        await dm.add_roles(role, guild.get_role(self.bot.config["dm_role"]), guild.get_role(self.bot.config["member_role"]))
        await dm.remove_roles(guild.get_role(self.bot.config["guest_role"]))

        # create campaign category and add to CampaignInfo
        category = await guild.create_category(name, overwrites=overwrites)
        retval.category = category.id

        retval.information_channel = 0
        # Create campaign announcement channel
        announcements = await category.create_text_channel(name="announcements")
        await announcements.send(New.NEW_CAMPAIGN_ANNOUNCEMENT_MESSAGE.format(campaign=retval))

        # Create campaign-specific information channel
        info = await category.create_text_channel(name="information")
        await info.send(New.NEW_CAMPAIGN_INFO_MESSAGE)
        # Create campaign lobby channel
        await category.create_text_channel(name="lobby")

        if location.lower() in ["online", "virtually", "discord", "virtual", "hybrid"]:
            # Create campaign voice channel
            await category.create_voice_channel(name=name)

        retval.status_message = 0
        return retval

    async def delete_campaign(self, info: CampaignInfo) -> bool:

        # fetch campaign's category
        category = self.bot.get_channel(info.category)
        guild = category.guild
        # fetch global campaign information channel
        global_channel = self.bot.get_channel(info.information_channel)
        try:
            await global_channel.delete()
        except Exception:
            pass
        # delete channels
        for channel in category.channels:
            await channel.delete()
        await category.delete()

        channel = self.bot.get_channel(self.bot.config["staff_botspam"])
        campaign_role = category.guild.get_role(info.role)
        if campaign_role is None:
            return False
        resp = self.bot.CampaignSQLHelper.select_field("role")
        for member in campaign_role.members:
            member: discord.Member

            await member.remove_roles(campaign_role)
            found = False
            for role_ in resp:
                role = category.guild.get_role(int(role_["role"]))
                if role is None:
                    await channel.send(str(role_[0]) + " couldn't resolve")
                    continue
                if member in role.members:
                    # member is in another campaign, stop
                    found = True
                    break

            # if member not in any other campaigns
            if not found:
                # remove member, add guest
                await member.remove_roles(guild.get_role(self.bot.config["member_role"]))
                await member.add_roles(guild.get_role(self.bot.config["guest_role"]))

        # delete role
        await campaign_role.delete()

        return True

    @commands.command()
    @commands.has_any_role(1050188024287338567, 873734392458145912, 809567701735440469)  # dev, admin, officer
    async def get_roles(self, context: commands.Context):
        message = ""
        async with self.bot.mutex:
            resp = self.bot.CampaignSQLHelper.select_field("role")
        for role_ in resp:
            role = context.guild.get_role(role_[0])
            if role is None:
                message += f"Failed to get role {role_[0]}\n"
            else:
                message += f"{role.id}: {role.name}\n"
        await context.send(message)

    def create_status_message(self, campaign: CampaignInfo) -> discord.Embed:
        embed = discord.Embed(
            title=f"{campaign.name} Campaign Status",
            color=0x00ff00
        )
        embed.add_field(name="DM", value=self.bot.get_user(campaign.dm).mention, inline=False)
        embed.add_field(name="Status: ", value="✅ Open" if campaign.current_players < campaign.max_players
                        else "❌ Closed", inline=False)

        embed.add_field(name="Channel: ", value=f"<#{campaign.information_channel}>", inline=False)
        embed.add_field(name="Players: ", value=f"{campaign.current_players}/{campaign.max_players}", inline=False)

        return embed


async def setup(bot):
    await bot.add_cog(CampaignBuilder(bot))
