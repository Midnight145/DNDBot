import json
import typing

import discord
from fastapi import Response, status, APIRouter

from modules.api.Permissions import permissions, Permissions

from .structs import CampaignApplication, PartialCampaignInfo
from modules.CampaignInfo import CampaignInfo
from DNDBot import DNDBot
from .. import CampaignBuilder

router = APIRouter()
guild = None


@router.get("/campaigns")
@permissions(Permissions.CAMPAIGN_READ)
async def get_campaigns(auth: str, response: Response):
    campaigns = DNDBot.instance.CampaignSQLHelper.get_campaigns()
    return json.dumps(campaigns)


@router.get("/campaigns/{campaign_id}")
@permissions(Permissions.CAMPAIGN_READ)
async def get_campaign(campaign_id: typing.Union[int, str], auth: str, response: Response):
    if isinstance(campaign_id, int):
        resp = DNDBot.instance.db.execute(f"SELECT * FROM campaigns WHERE id = {campaign_id}").fetchone()
    else:
        resp = DNDBot.instance.db.execute(f"SELECT * FROM campaigns WHERE name LIKE ?", (campaign_id,)).fetchone()
    return json.dumps(resp)


@router.get("/campaigns/{campaign_id}/players")
@permissions(Permissions.USER_READ)
async def get_players(campaign_id: typing.Union[int, str], auth: str, response: Response):
    campaign = DNDBot.instance.CampaignSQLHelper.select_campaign(campaign_id)
    if campaign is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return json.dumps({"error": "Campaign not found"})
    resp = DNDBot.instance.CampaignSQLHelper.get_players(campaign)

    return json.dumps(resp)


@router.post("/campaigns/create")
@permissions(Permissions.CAMPAIGN_CREATE)
async def create_campaign(auth: str, campaign: PartialCampaignInfo, response: Response):
    global guild
    if guild is None:
        guild = DNDBot.instance.get_guild(DNDBot.instance.config["server"])
    campaign.dm = guild.get_member(campaign.dm)
    campaign_info = await DNDBot.instance.CampaignBuilder.create_campaign(guild, campaign.name, campaign.dm, campaign.min_players, campaign.max_players, campaign.location, campaign.playstyle, campaign.info_message)

    # todo: make this consistent with the rest of the code, most args to create_campaign are unnecessary
    for attr in campaign.__dict__:
        setattr(campaign_info, attr, getattr(campaign, attr))

    commit = DNDBot.instance.CampaignSQLHelper.create_campaign(campaign_info)
    if not commit:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return json.dumps({"error": "Failed to create campaign"})
    DNDBot.instance.connection.commit()

    return json.dumps({"success": True})


@router.post("/campaigns/apply")
@permissions(Permissions.USER_CREATE)
async def apply_to_campaigns(auth: str, application: CampaignApplication, response: Response):
    for campaign in application.campaigns:
        if "(waitlist)" in campaign:
            campaign = campaign[:-11]
        campaign = DNDBot.instance.CampaignSQLHelper.select_campaign(campaign)
        if campaign is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return json.dumps({"error": "Campaign not found"})
    embed = discord.Embed(
        title="New Player Sign-Up!",
    )
    embed.add_field(name="What is your first name?", value=application.first_name, inline=False)
    embed.add_field(name="What is your last name?", value=application.last_name, inline=False)
    embed.add_field(name="What is your Discord ID number?", value=application.discord_id, inline=False)
    embed.add_field(name="What is your Discord tag?", value=application.discord_tag, inline=False)
    embed.add_field(name="Are you a UNT student?", value="Yes" if application.unt_email is not None else "No", inline=False)
    if application.unt_email is not None:
        embed.add_field(name="What is your UNT email?", value=application.unt_email, inline=False)
    for i in application.campaigns:
        embed.add_field(name="Which of the following campaigns are you interested in joining?", value=i, inline=False)
    embed.set_footer(text="React with a green checkmark to approve or a red X to deny.")
    print("Sending embed...")
    channel = DNDBot.instance.get_channel(DNDBot.instance.config["staff_botspam"])
    await channel.send(embed=embed)

    return json.dumps({"success": True})