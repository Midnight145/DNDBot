import discord


class CampaignInfo:
    def __init__(self, name: str = None, role: int = None, category: int = None,
                 information_channel: int = None, dm: int = None, min_players: int = None,
                 max_players: int = None, current_players: int = 0):
        """
        Holds the information about a given campaign, normally created by CampaignSQLHelper from a row. Can be
        initialized to None and filled manually, or can be filled via constructor.
        # TODO: this is currently used as integers once, but objects elsewhere. STANDARDIZE THIS
        :param name: The campaign's name
        :param role: The campaign's role
        :param category: The campaign's category channel
        :param information_channel: The "global" information channel
        :param dm: Dungeon master
        :param min_players: Minimum players required
        :param max_players: Maximum players allowed
        :param current_players: Current players
        """
        self.name: str = name
        self.role: int = role
        self.category: int = category
        self.information_channel: int = information_channel
        self.dm: int = dm
        self.min_players: int = min_players
        self.max_players: int = max_players
        self.current_players: int = current_players

    # allows for dictionary-like retrieval syntax as necessary
    def __getitem__(self, item):
        return getattr(self, item)