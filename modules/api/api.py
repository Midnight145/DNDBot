import datetime
import json
import typing

import discord
from fastapi import Response, status, APIRouter

from modules.api.Permissions import permissions, Permissions

from .structs import CampaignApplication, PartialCampaignInfo, CampaignActionRequest
from modules.CampaignInfo import CampaignInfo
from DNDBot import DNDBot
from .. import CampaignBuilder

router = APIRouter()
guild = None


@router.get("/campaigns")
@permissions(Permissions.CAMPAIGN_READ)
async def get_campaigns(auth: str, response: Response):
    global guild
    campaigns = DNDBot.instance.CampaignSQLHelper.get_campaigns()
    if guild is None:
        guild = DNDBot.instance.get_guild(DNDBot.instance.config["server"])
    for val in campaigns:
        val["dm_username"] = guild.get_member(val["dm"]).name
        val["dm_nickname"] = guild.get_member(val["dm"]).display_name
        players = DNDBot.instance.db.execute(f"SELECT * FROM players WHERE campaign = ?", (val["id"],)).fetchall()
        val["players"] = [i["id"] for i in players if i["waitlisted"] == 0]
        val["waitlist"] = [i["id"] for i in players if i["waitlisted"] == 1]
    return json.dumps(campaigns)


@router.get("/campaigns/{campaign_id}")
@permissions(Permissions.CAMPAIGN_READ)
async def get_campaign(campaign_id: typing.Union[int, str], auth: str, response: Response):
    global guild
    try:
        campaign_id = int(campaign_id)
    except ValueError:
        pass
    if isinstance(campaign_id, int):
        resp = DNDBot.instance.db.execute(f"SELECT * FROM campaigns WHERE id = {campaign_id}").fetchone()
    else:
        resp = DNDBot.instance.db.execute(f"SELECT * FROM campaigns WHERE name LIKE ?", (campaign_id,)).fetchone()
    players = DNDBot.instance.db.execute(f"SELECT * FROM players WHERE campaign = ?", (resp["id"],)).fetchall()
    resp["players"] = [i["id"] for i in players if i["waitlisted"] == 0]
    resp["waitlist"] = [i["id"] for i in players if i["waitlisted"] == 1]
    if guild is None:
        guild = DNDBot.instance.get_guild(DNDBot.instance.config["server"])
    resp["dm_username"] = guild.get_member(resp["dm"]).name
    resp["dm_nickname"] = guild.get_member(resp["dm"]).display_name
    resp["new_player_friendly"] = resp["new_player_friendly"]
    return json.dumps(resp)


@router.get("/campaigns/{campaign_id}/players")
@permissions(Permissions.USER_READ)
async def get_players(campaign_id: typing.Union[int, str], auth: str, response: Response):
    try:
        campaign_id = int(campaign_id)
    except ValueError:
        pass
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
    if not campaign.meeting_date and not campaign.meeting_day:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return json.dumps({"error": "Meeting date or day must be specified"})
    embed = discord.Embed(
        title="New Campaign Sign-Up! (Website)",
    )
    embed.add_field(name="First Name", value=campaign.dm.first_name, inline=True)
    embed.add_field(name="Last Name", value=campaign.dm.last_name, inline=True)
    embed.add_field(name="UNT Email", value=campaign.dm.unt_email, inline=True)
    embed.add_field(name="Discord Username", value=campaign.dm.discord_tag, inline=True)
    embed.add_field(name="Discord ID", value=campaign.dm.discord_id, inline=True)
    embed.add_field(name="DM Experience", value=campaign.dm.dm_experience, inline=True)
    embed.add_field(name="Playstyle", value=campaign.playstyle, inline=False)
    embed.add_field(name="Campaign Name", value=campaign.name, inline=True)
    embed.add_field(name="Description", value=campaign.info_message, inline=False)
    embed.add_field(name="System", value=campaign.system, inline=True)
    embed.add_field(name="Location", value=campaign.location, inline=True)
    embed.add_field(name="Meeting Frequency", value=campaign.meeting_frequency, inline=True)
    if campaign.meeting_day:
        embed.add_field(name="Meeting Day", value=campaign.meeting_day, inline=True)
    elif campaign.meeting_date:
        embed.add_field(name="Meeting Date", value=campaign.meeting_date, inline=True)
    embed.add_field(name="Meeting Time", value=campaign.meeting_time, inline=True)
    embed.add_field(name="Session Length", value=campaign.session_length, inline=True)
    embed.add_field(name="Min Players", value=campaign.min_players, inline=True)
    embed.add_field(name="Max Players", value=campaign.max_players, inline=True)
    embed.add_field(name="New Player Friendly", value=campaign.new_player_friendly, inline=True)

    channel = DNDBot.instance.get_channel(DNDBot.instance.config["dm_receipts"])

    message = await channel.send(embed=embed)
    if not message:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return json.dumps({"error": "Failed to create campaign"})
    await message.add_reaction("✅")
    await message.add_reaction("❌")

    # campaign_info = await DNDBot.instance.CampaignBuilder.create_campaign(guild, campaign.name, campaign.dm, campaign.min_players, campaign.max_players, campaign.location, campaign.playstyle, campaign.info_message)

    # todo: make this consistent with the rest of the code, most args to create_campaign are unnecessary
    # for attr in campaign.__dict__:
    #     setattr(campaign_info, attr, getattr(campaign, attr))
    #
    # commit = DNDBot.instance.CampaignSQLHelper.create_campaign(campaign_info)
    # if not commit:
    #     response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    #     return json.dumps({"error": "Failed to create campaign"})
    # DNDBot.instance.connection.commit()

    return json.dumps({"success": True})


@router.post("/campaigns/{campaign_id}/action")
@permissions(Permissions.CAMPAIGN_CREATE)
async def campaign_action(auth: str, action: CampaignActionRequest, response: Response):
    global guild
    if guild is None:
        guild = DNDBot.instance.get_guild(DNDBot.instance.config["server"])

    embed = discord.Embed(
        title="Campaign Action Request Form Submission"
    )
    embed.add_field(name="First Name", value=action.first_name, inline=True)
    embed.add_field(name="Last Name", value=action.last_name, inline=True)
    embed.add_field(name="Discord", value=action.discord_tag, inline=True)
    embed.add_field(name="Campaign Title", value=action.campaign_name, inline=True)
    embed.add_field(name="Action", value=action.action, inline=True)
    if action.reasons:
        embed.add_field(name="Reasons", value="\n".join(action.reasons), inline=True)
    if action.elaboration:
        embed.add_field(name="Elaboration", value=action.elaboration, inline=False)
    if action.new_player_count:
        embed.add_field(name="Max Players", value=action.max_players, inline=True)


@router.post("/campaigns/apply")
@permissions(Permissions.USER_CREATE)
async def apply_to_campaigns(auth: str, application: CampaignApplication, response: Response):
    global guild
    if guild is None:
        guild = DNDBot.instance.get_guild(DNDBot.instance.config["server"])
    for campaign in application.campaigns:
        if "(waitlist)" in campaign:
            campaign = campaign[:-11]
        campaign = DNDBot.instance.CampaignSQLHelper.select_campaign(campaign)
        if campaign is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return json.dumps({"error": "Campaign not found"})
    for i in application.campaigns:
        campaign = DNDBot.instance.CampaignSQLHelper.select_campaign(i)
        dm = guild.get_member(campaign.dm)
        embed = discord.Embed(
            title=f"New Application for {campaign.name}",
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Campaign", value=campaign.name, inline=False)
        embed.add_field(name="DM", value=str(dm), inline=False)
        embed.add_field(name="Name", value=f"{application.first_name} {application.last_name}", inline=False)
        embed.add_field(name="Discord", value=f"{str(guild.get_member(application.discord_id))}")
        embed.add_field(name="Discord ID", value=str(application.discord_id))
        embed.set_footer(text="React with a green checkmark to approve or a red X to deny.")

        channel = DNDBot.instance.get_channel(DNDBot.instance.config["applications_channel"])
        message = await channel.send(content=dm.mention, embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

    return json.dumps({"success": True})


@router.get("/users/{user_id}")
@permissions(Permissions.USER_READ)
async def get_user(user_id: int, auth: str, response: Response):
    global guild
    if guild is None:
        guild = DNDBot.instance.get_guild(DNDBot.instance.config["server"])
    user = guild.get_member(user_id)
    if user is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        user = DNDBot.instance.get_user(user_id)
        if user is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return json.dumps({"error": "User not found"})
        resp = {"id": user.id, "name": user.name, "discriminator": user.discriminator, "nickname": user.display_name,
                "in_discord": False, "officer": False, "developer": False, "verified": False, "guest": False,
                "player": False, "dm": False, "banned_player": False, "banned_dm": False, "joined": "",
                "campaigns_player": [], "campaigns_dm": [], "warnings": {}}
        return json.dumps(resp)

    officer_role = guild.get_role(DNDBot.instance.config["officer_role"])
    developer_role = guild.get_role(DNDBot.instance.config["developer_role"])
    verified_role = guild.get_role(DNDBot.instance.config["verified_role"])
    guest_role = guild.get_role(DNDBot.instance.config["guest_role"])
    player_role = guild.get_role(DNDBot.instance.config["member_role"])
    dm_role = guild.get_role(DNDBot.instance.config["dm_role"])
    banned_player_role = guild.get_role(DNDBot.instance.config["banned_player_role"])
    banned_dm_role = guild.get_role(DNDBot.instance.config["banned_dm_role"])

    resp = {"id": user.id, "name": user.name, "discriminator": user.discriminator, "nickname": user.display_name,
            "in_discord": True, "officer": officer_role in user.roles, "developer": developer_role in user.roles,
            "verified": verified_role in user.roles, "guest": guest_role in user.roles,
            "player": player_role in user.roles, "dm": dm_role in user.roles,
            "banned_player": banned_player_role in user.roles, "banned_dm": banned_dm_role in user.roles,
            "joined": user.joined_at.isoformat(), "campaigns_player": [], "campaigns_dm": [], "warnings": {}}

    res = DNDBot.instance.db.execute("select * from campaigns where dm = ?", (user.id,)).fetchall()
    for i in res:
        resp["campaigns_dm"].append(i["id"])
    res = DNDBot.instance.db.execute("select * from players where id = ? and waitlisted = 0", (user.id,)).fetchall()
    for i in res:
        resp["campaigns_player"].append(i["campaign"])
    res = DNDBot.instance.db.execute("select * from warns where member = ?", (user.id,)).fetchall()
    for i in res:
        resp["warnings"][i["id"]] = i["reason"]
    return json.dumps(resp)


@router.get("/users/{user_id}/warnings")
@permissions(Permissions.USER_READ)
async def get_user_warnings(user_id: int, auth: str, response: Response):
    warns = DNDBot.instance.db.execute("select * from warns where member = ?", (user_id,)).fetchall()
    resp = [{i["id"]: i["reason"]} for i in warns]
    return json.dumps(resp)


# async def campaign_creation_callback(instance: DNDBot, campaign_info: CampaignInfo):
async def campaign_creation_callback(*args, campaign_info=None):
    global guild
    if guild is None:
        guild = DNDBot.instance.get_guild(DNDBot.instance.config["server"])
    name = campaign_info.name
    dungeon_master = guild.get_member(campaign_info.dm)
    embed = discord.Embed(
        title="Campaign Created",
        description=f"Campaign {name} created.",
        timestamp=datetime.datetime.utcnow()
    )
    receipts = guild.get_channel(DNDBot.instance.config["dm_receipts"])
    embed.add_field(name="DM", value=f"{str(dungeon_master)} ({dungeon_master.id})")
    embed.add_field(name="Role", value=str(guild.get_role(campaign_info.role)))
    embed.add_field(name="Category", value=str(guild.get_channel(campaign_info.category).name))
    embed.add_field(name="Max Players", value=f"{campaign_info.max_players}")
    await receipts.send(embed=embed)

    DNDBot.instance.connection.commit()
    await (guild.get_channel(DNDBot.instance.config["notification_channel"])).send(
        f"<@&{DNDBot.instance.config['new_campaign_role']}>: A new campaign has opened: "
        f"<#{campaign_info.information_channel}> run by <@{campaign_info.dm}>! "
        f"Apply to join here: <https://www.untcriticalhit.org/apply/{campaign_info.id}>")
    await DNDBot.instance.CampaignPlayerManager.update_status(campaign_info)