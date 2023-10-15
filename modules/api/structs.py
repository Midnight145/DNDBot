import typing

from pydantic import BaseModel


class PartialCampaignInfo(BaseModel):
    """
    Class that holds all basic information about a given campaign
    :param name: Name of the campaign
    :param dm: DM ID of the campaign
    :param min_players: Minimum number of players for the campaign
    :param max_players: Maximum number of players for the campaign
    :param info_message: Information message sent in the information channel
    :param location: Location of the campaign
    :param playstyle: Playstyle of the campaign
    :param session_length: The campaign's session length
    :param meeting_frequency: The campaign's meeting frequency
    :param meeting_time: The campaign's meeting time
    :param system: The campaign's system
    :param new_player_friendly: Whether the campaign is new player friendly
    """
    name: str
    dm: int
    min_players: int
    max_players: int
    info_message: str
    location: str
    playstyle: str
    session_length: str
    meeting_frequency: str
    meeting_time: str
    system: str
    new_player_friendly: int


class CampaignInfo(BaseModel):
    """
    Holds the information about a given campaign, normally created by CampaignSQLHelper from a row. Can be
    initialized to  and filled manually, or can be filled via constructor.
    :param name: The campaign's name
    :param role: The campaign's role
    :param category: The campaign's category channel
    :param information_channel: The "global" information channel
    :param dm: Dungeon master
    :param min_players: Minimum players required
    :param max_players: Maximum players allowed
    :param current_players: Current players
    :param status_message: The status message
    :param id: The campaign's ID
    :param locked: Whether the campaign is locked
    :param info_message: The campaign's info message
    :param location: The campaign's location
    :param playstyle: The campaign's playstyle
    :param session_length: The campaign's session length
    :param meeting_frequency: The campaign's meeting frequency
    :param meeting_time: The campaign's meeting time
    :param system: The campaign's system
    :param new_player_friendly: Whether the campaign is new player friendly
    """
    name: str
    role: int
    category: int
    information_channel: int
    dm: int
    min_players: int
    max_players: int
    current_players: int
    status_message: int
    id: str
    locked: str
    info_message: str
    location: str
    playstyle: str
    session_length: str
    meeting_frequency: str
    meeting_time: str
    system: str
    new_player_friendly: int


class CampaignApplication(BaseModel):
    campaigns: list[str]
    first_name: str
    last_name: str
    discord_tag: str
    discord_id: int
    unt_email: typing.Optional[str]
