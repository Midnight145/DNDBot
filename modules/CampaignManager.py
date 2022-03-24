import discord
from discord.ext import commands
import datetime
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..bot import DNDBot


class CampaignManager(commands.Cog):
    def __init__(self, bot: 'DNDBot'):
        self.bot = bot
        self.CampaignBuilder = self.bot.CampaignBuilder
        self.CampaignSQLHelper = self.bot.CampaignSQLHelper

    @commands.command()
    @commands.has_any_role("Officer", "Dungeon Master")
    async def create_campaign(self, context: commands.Context, name: str, dungeon_master: discord.Member,
                              min_players: int, max_players: int):
        """
        :param context: Command context
        :param name: Campaign name
        :param dungeon_master: Campaign DM, can be Union[str, int] as it is typecasted
        :param min_players: Minimum number of players necessary to start
        :param max_players: Maximum number of players allowed
        :return: None
        """

        campaign_info = await self.CampaignBuilder.create_campaign(context, name)
        self.CampaignSQLHelper.create_campaign(name, dungeon_master.id, campaign_info, int(min_players),
                                               int(max_players))

        embed = discord.Embed(
            title="Campaign Created",
            description=f"Campaign {name} created.",
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="DM", value=f"{str(dungeon_master)} ({dungeon_master.id})")
        embed.add_field(name="Role", value=str(campaign_info["role"]))
        embed.add_field(name="Category", value=str(campaign_info["category"].name))
        embed.add_field(name="Max Players", value=f"{max_players}")
        await context.send(embed=embed)
        self.bot.connection.commit()

    @commands.command()
    @commands.has_any_role("Officer", "Dungeon Master")
    async def delete_campaign(self, context: commands.Context, campaign: Union[int, str]):
        """
        :param context: Command context
        :param campaign: Either campaign name or campaign ID
        :return: None
        """

        resp = self.CampaignSQLHelper.select_campaign(campaign)
        commit = await self.CampaignBuilder.delete_campaign(resp)

        if commit:
            await context.send(f"Campaign \"{resp['name']}\" deleted.")
            self.bot.connection.commit()
        else:
            await context.send(f"There was an error deleting \"{resp['name']}\"")

    @commands.command()
    @commands.has_any_role("Officer", "Dungeon Master")
    async def drop_campaign(self, context: commands.Context, campaign: Union[int, str]):
        """
        Will drop a campaign from the database without deleting any channels

        :param context: Command context
        :param campaign: Either campaign name or campaign ID
        :return: None
        """
        self.CampaignSQLHelper.delete_campaign(campaign)
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


def setup(bot):
    bot.add_cog(CampaignManager(bot))