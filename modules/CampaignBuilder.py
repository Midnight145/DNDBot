from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from modules import CampaignInfo
import time

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..DNDBot import DNDBot


class CampaignBuilder(commands.Cog):
    """
    WILL NEVER COMMIT TO DATABASE
    """

    def __init__(self, bot: 'DNDBot'):
        self.bot = bot

    # noinspection PyMethodMayBeStatic
    async def create_campaign(self, guild: discord.Guild, name: str, dm: discord.Member) -> CampaignInfo:
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

        # create campaign role
        role = await guild.create_role(reason="new campaign", name=name, mentionable=True)
        # add campaign role to CampaignInfo object
        retval.role = role.id

        # handle permission overwrites
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False),
                      role: discord.PermissionOverwrite(send_messages=True, read_messages=True),
                      dm: discord.PermissionOverwrite(manage_channels=True, manage_permissions=True,
                                                      send_messages=True, manage_messages=True)
                      }
        await dm.add_roles(role, guild.get_role(812785919727894539))
        # create campaign category and add to CampaignInfo
        category = await guild.create_category(name, overwrites=overwrites)
        retval.category = category.id

        retval.information_channel = 0
        # Create campaign announcement channel
        announcements = await category.create_text_channel(name="announcements")
        await announcements.send(announcement_message(name))

        # Create campaign-specific information channel
        info = await category.create_text_channel(name="information")
        await info.send(INFO_MESSAGE)

        # Create campaign lobby channel
        await category.create_text_channel(name="lobby")

        # Create campaign notes channel
        notes = await category.create_text_channel(name="notes")
        await notes.send(NOTES_MESSAGE)

        # Create campaign picture channel
        pics = await category.create_text_channel(name="pics")
        await pics.send(PICS_MESSAGE)

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
    async def get_roles(self, context: commands.Context):
        message = ""
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


def announcement_message(name: str):
    return __ANNOUNCEMENT_MESSAGE.format(name=name)


def verification_denied(channel):
    return __VERIFICATION_DENIED.format(channel=channel)


INFO_MESSAGE = ("Here is where the Dungeon Master can post important information regarding the campaign that players "
                "may need to refer back to. This information can include a description of the **location** the "
                "campaign takes place in, the **mission** the players are taking on, and a **map** of the land.")

NOTES_MESSAGE = ("This is where players and the DM can post notes that they want to remember. Meet an important "
                 "character? Write it down! Don't wanna forget a tidbit of information a character gave you? Write it "
                 "down! Keep in mind the DM may ask you not to write down notes if they choose to.")

PICS_MESSAGE = ("This is where anyone can post pictures of their characters, locations, etc. Be sure to label it so "
                "you can refer back to it later! ")

__ANNOUNCEMENT_MESSAGE = ("Welcome to the **{name}** campaign category! This is where your Dungeon Master can post "
                          "announcements, information, and other important information regarding the campaign. "
                          "Players and the DM may also communicate in #lobby. If your sessions are virtual, "
                          "they will be held through this category's voice channel. Let me know if you have any "
                          "questions, and have fun!")

__VERIFICATION_DENIED = ("Your verification has been denied due to your nickname not following the instructions as "
                         "described in <#{channel}>. If you believe this to be a mistake, please contact the "
                         "President.")
