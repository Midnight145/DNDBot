from typing import Union, Optional, TYPE_CHECKING

import discord

from modules import CampaignInfo

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..bot import DNDBot


class CampaignSQLHelper:
    """
    WILL NEVER COMMIT TO DATABASE
    """

    def __init__(self, bot: 'DNDBot'):
        self.bot = bot

    def create_campaign(self, name: str, dm_id: int, vals: CampaignInfo, min_players: int, max_players: int) -> bool:
        """
        Adds a new campaign to the database
        :param name: Campaign name
        :param dm_id: Dungeon master member ID
        :param vals: Campaign info created by SQLHelper
        :param min_players: Minimum players required
        :param max_players: Maximum players allowed
        :return: Whether campaign was created successfully
        """
        self.bot.db.execute(f"CREATE TABLE IF NOT EXISTS {name + '_players'} "
                            "(id INTEGER PRIMARY KEY, waitlisted INTEGER, name TEXT)")
        self.bot.db.execute(
            f"INSERT INTO campaigns (name, dm, role, category, information, min_players, max_players, current_players)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            (name, dm_id, vals.role.id, vals.category.id, vals.information_channel, int(min_players), int(max_players)))
        self.bot.connection.commit()
        return True

    def delete_campaign(self, campaign: Union[int, str]):
        """
        Deletes a campaign from the database
        :param campaign: Either campaign name or campaign ID
        :return: None
        """

        # checks whether we passed ID or name
        if isinstance(campaign, int):
            resp = self.select_campaign(campaign)
            self.bot.db.execute(f"DELETE FROM campaigns WHERE id = {campaign}")
            self.bot.db.execute(f"DROP TABLE {resp['name'] + '_players'}")
        else:
            self.bot.db.execute(f"DELETE FROM campaigns WHERE name LIKE {campaign}")
            self.bot.db.execute(f"DROP TABLE {campaign + '_players'}")
        self.bot.connection.commit()

    def select_campaign(self, campaign: Union[int, str]) -> CampaignInfo:
        """
        Selects a row from the campaign table
        :param campaign: Either campaign name or campaign ID
        :return: Row corresponding to that campaign
        """
        # checks whether we passed ID or name
        if isinstance(campaign, int):
            return self.dict_to_campaign(self.bot.db.execute(f"SELECT * FROM campaigns WHERE id = {campaign}").fetchone())
        else:
            return self.dict_to_campaign(self.bot.db.execute(f"SELECT * FROM campaigns WHERE name LIKE {campaign}").fetchone())

    def select_field(self, field) -> Optional[list[dict]]:
        """
        Selects a certain field from the main table
        :param field: the field to be selected
        :return: The rows found
        """
        return self.bot.db.execute(f"SELECT {field} FROM campaigns").fetchall()

    @staticmethod
    def dict_to_campaign(resp: dict) -> CampaignInfo:
        """
        Converts a row: dict returned by SELECT to a CampaignInfo object
        :param resp: The dictionary to be converted
        :return: The created CampaignInfo object
        """
        campaign = CampaignInfo()
        for key, value in resp.items():
            setattr(campaign, key, value)
        return campaign

    def add_player(self, campaign: CampaignInfo, player: discord.Member):
        waitlisted = 1 if campaign.current_players >= campaign.max_players else 0
        self.bot.db.execute(f"INSERT INTO {campaign.name}_players (id, waitlisted, name) VALUES ({player.id}, {waitlisted}, {player.display_name}")
        if not waitlisted:
            self.__increment_players(campaign, 1)
        self.bot.connection.commit()

    def remove_player(self, campaign: CampaignInfo, player: discord.Member):
        self.bot.db.execute(f"DELETE FROM {campaign.name}_players WHERE id = {player.id}")
        self.__increment_players(campaign, -1)
        self.bot.connection.commit()

    def __increment_players(self, campaign: CampaignInfo, amount):
        self.bot.db.execute(f"UPDATE campaigns SET current_players = {campaign.current_players + amount} WHERE name LIKE {campaign.name}")
        self.bot.connection.commit()