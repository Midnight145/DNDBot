import sqlite3
import string
from typing import Union, Optional, TYPE_CHECKING

import discord

from .CampaignInfo import CampaignInfo
import traceback

if TYPE_CHECKING:  # TYPE_CHECKING is always false, allows for type hinting without circular import
    from ..bot import DNDBot


class CampaignSQLHelper:
    """
    WILL NEVER COMMIT TO DATABASE
    """

    def __init__(self, bot: 'DNDBot'):
        self.bot = bot

    def create_campaign(self, vals: CampaignInfo) -> bool:
        """
        Adds a new campaign to the database
        :param vals: Campaign info created by SQLHelper
        :param current_players: Current players in the campaign
        :return: Whether we should commit to database
        """
        try:
            self.bot.db.execute(f"CREATE TABLE IF NOT EXISTS {self.__get_table_name(vals.name)} "
                                "(id INTEGER PRIMARY KEY, waitlisted INTEGER, name TEXT)")
            self.bot.db.execute(
                f"INSERT INTO campaigns (name, dm, role, category, information_channel, min_players, max_players, current_players)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (vals.name, vals.dm, vals.role, vals.category, vals.information_channel, vals.min_players, vals.max_players, vals.current_players))
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def delete_campaign(self, campaign: Union[int, str]) -> bool:
        """
        Deletes a campaign from the database
        :param campaign: Either campaign name or campaign ID
        :return: Whether we should commit to database
        """

        try:
            # checks whether we passed ID or name
            if isinstance(campaign, int):
                resp = self.select_campaign(campaign)
                self.bot.db.execute(f"DELETE FROM campaigns WHERE id = {campaign}")
                self.bot.db.execute(f"DROP TABLE {self.__get_table_name(resp['name'])}")
            else:
                self.bot.db.execute(f"DELETE FROM campaigns WHERE name LIKE {campaign}")
                self.bot.db.execute(f"DROP TABLE {self.__get_table_name(campaign)}")
            return True
        except Exception as e:
            traceback.print_exc()
            return False

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
            return self.dict_to_campaign(self.bot.db.execute(f"SELECT * FROM campaigns WHERE name LIKE ?", (campaign,)).fetchone())


    def select_field(self, field) -> Optional[list[dict]]:
        """
        Selects a certain field from the main table
        :param field: the field to be selected
        :return: The rows found
        """
        return self.bot.db.execute(f"SELECT {field} FROM campaigns").fetchall()

    @staticmethod
    def dict_to_campaign(resp: Union[sqlite3.Row, dict]) -> CampaignInfo:
        """
        Converts a row: dict returned by SELECT to a CampaignInfo object
        :param resp: The dictionary to be converted
        :return: The created CampaignInfo object
        """
        if isinstance(resp, sqlite3.Row):
            resp = dict(zip(resp.keys(), resp))
        campaign = CampaignInfo()
        for key, value in resp.items():
            setattr(campaign, key, value)
        return campaign

    def add_player(self, campaign: CampaignInfo, player: discord.Member):
        try:
            waitlisted = 0
            self.bot.db.execute(f"INSERT INTO {self.__get_table_name(campaign.name)} (id, waitlisted, name) VALUES (?, ?, ?)", (player.id, waitlisted, player.display_name))
            if not waitlisted:
                self.__increment_players(campaign, 1)
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def waitlist_player(self, campaign: CampaignInfo, player: discord.Member):
        try:
            waitlisted = 1
            self.bot.db.execute(f"INSERT INTO {self.__get_table_name(campaign.name)} (id, waitlisted, name) VALUES (?, ?, ?)", (player.id, waitlisted, player.display_name))
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def unwaitlist(self, campaign: CampaignInfo, player: discord.Member):
        try:
            waitlisted = 0
            self.bot.db.execute(f"UPDATE {self.__get_table_name(campaign.name)} SET waitlisted = ? WHERE id = ?", (waitlisted, player.id))
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def remove_player(self, campaign: CampaignInfo, player: discord.Member):
        try:
            self.bot.db.execute(f"DELETE FROM {self.__get_table_name(campaign.name)} WHERE id = {player.id}")
            self.__increment_players(campaign, -1)
            self.bot.connection.commit()
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def __increment_players(self, campaign: CampaignInfo, amount):
        try:
            self.bot.db.execute(f"UPDATE campaigns SET current_players = {campaign.current_players + amount} WHERE name LIKE ?", (campaign.name,))
            self.bot.connection.commit()
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def get_waitlist(self, campaign: CampaignInfo):
        try:
            return self.bot.db.execute(f"SELECT * FROM {self.__get_table_name(campaign.name)} WHERE waitlisted = 1").fetchall()
        except Exception as e:
            traceback.print_exc()
            return None

    def __get_table_name(self, campaign_name: str) -> str:
        return ''.join([i for i in campaign_name.replace(" ", "_") if i in string.ascii_letters or i == "_"]) + "_players"

    def get_waitlisted_players(self, campaign: CampaignInfo):
        try:
            return self.bot.db.execute(f"SELECT * FROM {self.__get_table_name(campaign.name)} WHERE waitlisted = 1").fetchall()
        except Exception as e:
            traceback.print_exc()
            return None

