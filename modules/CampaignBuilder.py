from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from modules import CampaignInfo

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..bot import DNDBot


class CampaignBuilder(commands.Cog):
    """
    WILL NEVER COMMIT TO DATABASE
    """

    def __init__(self, bot: 'DNDBot'):
        self.bot = bot

    async def create_campaign(self, context: commands.Context, name: str) -> CampaignInfo:
        """
        Creates all of the necessary channels when creating a new campaign
        :param context: Command context
        :param name: Campaign name
        :return: CampaignInfo object
        """

        # return value
        retval = CampaignInfo()
        guild = context.guild
        # create campaign role
        role = await guild.create_role(reason="new campaign", name=name, mentionable=True)
        # add campaign role to CampaignInfo object
        retval.role = role.id
        # fetch dm role
        dm_role = guild.get_role(self.bot.config["dm_role"])

        # handle permission overwrites
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False),
                      role: discord.PermissionOverwrite(send_messages=True, read_messages=True),
                      dm_role: discord.PermissionOverwrite(manage_channels=True, manage_permissions=True,
                                                           send_messages=True)
                      }

        # create campaign category and add to CampaignInfo
        category = await guild.create_category(name, overwrites=overwrites)
        retval.category = category.id

        # Fetch "Information" category
        info_category = guild.get_channel(self.bot.config["info_category"])
        # Create campaign's information channel and add to CampaignInfo
        global_channel = await info_category.create_text_channel(name=name)
        retval.information_channel = global_channel.id

        # Create campaign announcement channel
        announcements = await category.create_text_channel(name="announcements")
        await announcements.send(announcement_message(name))

        # Create campaign-specific information channel
        info = await category.create_text_channel(name="information")
        await info.send(INFO_MESSAGE)

        # Create campaign lobby channel
        lobby = await category.create_text_channel(name="lobby")

        # Create campaign notes channel
        notes = await category.create_text_channel(name="notes")
        await notes.send(NOTES_MESSAGE)

        # Create campaign picture channel
        pics = await category.create_text_channel(name="pics")
        await pics.send(PICS_MESSAGE)

        # Create campaign voice channel
        voice = await category.create_voice_channel(name=name)

        return retval

    async def delete_campaign(self, info: CampaignInfo) -> bool:
        try:
            # fetch campaign's category
            category = self.bot.get_channel(info.category)
            # fetch global campaign information channel
            global_channel = self.bot.get_channel(info.information_channel)
            # move channel to archive category
            await global_channel.move(category=category.guild.get_channel(self.bot.config["archive_category"]), reason="campaign deleted", end=True, sync_permissions=True)

            # delete channels
            for channel in category.channels:
                await channel.delete()
            await category.delete()

            resp = self.bot.CampaignSQLHelper.select_field("role")
            campaign_role = category.guild.get_role(info.role)

            for member in campaign_role.members:
                member: discord.Member
                found = False
                for role_ in resp:
                    role = category.guild.get_role(role_)
                    if member in role.members:
                        # member is in another campaign, stop
                        found = True
                        break

                # if member not in any other campaigns
                if not found:
                    # remove member, add guest
                    await member.remove_roles(self.bot.config["member_role"])
                    await member.add_roles(self.bot.config["guest_role"])

            # delete role
            await (category.guild.get_role(info.role)).delete()

            return True
        except Exception as e:
            print(e)
            return False


def setup(bot):
    bot.add_cog(CampaignBuilder(bot))


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
