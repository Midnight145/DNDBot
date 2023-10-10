import typing

from pydantic import BaseModel


class PartialCampaignInfo(BaseModel):
    """
    Class that holds all basic information about a given campaign
    :param name: Name of the campaign
    :param dm: DM ID of the campaign
    :param min_players: Minimum number of players for the campaign
    :param max_players: Maximum number of players for the campaign
    :param information_message: Information message sent in the information channel
    """
    name: str
    dm: int
    min_players: int
    max_players: int
    information_message: str


class CampaignInfo(BaseModel):
    """
    Class that holds all basic information about a given campaign
    :param name: Name of the campaign
    :param role: Role ID of the campaign
    :param category: Category ID of the campaign
    :param information_channel: Information channel ID of the campaign
    :param dm: DM ID of the campaign
    :param min_players: Minimum number of players for the campaign
    :param max_players: Maximum number of players for the campaign
    :param current_players: Current number of players for the campaign
    :param status_message: Status message ID of the campaign
    :param id: ID of the campaign
    :param locked: Whether the campaign is locked
    :param information_message: Information message sent in the information channel
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
    id: int
    locked: bool
    information_message: str


class CampaignApplication(BaseModel):
    campaigns: list[str]
    first_name: str
    last_name: str
    discord_tag: str
    discord_id: int
    unt_email: typing.Optional[str]
