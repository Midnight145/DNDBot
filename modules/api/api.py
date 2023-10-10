import string
import traceback
import typing
from enum import IntEnum

from fastapi import FastAPI, Response, status, APIRouter
import sqlite3
import json
import functools


def check_authorization(auth: str) -> int:
    authorized_users = db.execute("SELECT * FROM authorized_users").fetchall()
    for user in authorized_users:
        if user["token"] == auth:
            return user["permissions"]
    return 0


def permissions(permissions_value: 'Permissions'):
    def decorator(func):
        @functools.wraps(func)
        def wrapper_decorator(*args, **kwargs):
            token = kwargs.get("auth", 0)
            permissions_level = check_authorization(token)
            print(token, permissions_level, permissions_value, permissions_level & permissions_value)
            if permissions_level & permissions_value == 0:
                response = kwargs.get("response", None)
                if response is not None:
                    response.status_code = status.HTTP_401_UNAUTHORIZED
                return json.dumps({"error": "Unauthorized"})
            return func(*args, **kwargs)

        return wrapper_decorator
    return decorator


class Permissions(IntEnum):
    NONE = 0b0
    CAMPAIGN_READ = 0b1
    CAMPAIGN_WRITE = 0b10
    CAMPAIGN_CREATE = 0b100
    USER_READ = 0b1000
    USER_WRITE = 0b10000
    USER_CREATE = 0b100000
    FULL = 0b11111111


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


db = sqlite3.connect("dnd.db", check_same_thread=False)
db.row_factory = dict_factory

router = APIRouter()


@router.get("/campaigns")
@permissions(Permissions.CAMPAIGN_READ)
def get_campaigns(auth: str, response: Response):
    test: list = db.execute("SELECT * FROM campaigns").fetchall()
    return json.dumps(test)


@router.get("/campaigns/{campaign_id}")
@permissions(Permissions.CAMPAIGN_READ)
def get_campaign(campaign_id: typing.Union[int, str], auth: str, response: Response):
    if isinstance(campaign_id, int):
        resp = db.execute(f"SELECT * FROM campaigns WHERE id = {campaign_id}").fetchone()
    else:
        resp = db.execute(f"SELECT * FROM campaigns WHERE name LIKE ?", (campaign_id,)).fetchone()
    return json.dumps(resp)


@router.get("/campaigns/{campaign_id}/players")
@permissions(Permissions.USER_READ)
def get_players(campaign_id: typing.Union[int, str], auth: str, response: Response):
    if isinstance(campaign_id, int):
        resp = db.execute(f"SELECT * FROM campaigns WHERE id = {campaign_id}").fetchone()
        table = __get_table_name(resp["name"])
    else:
        table = __get_table_name(campaign_id)
    resp = db.execute(f"SELECT * FROM {table} WHERE waitlisted=0").fetchall()
    return json.dumps(resp)


@router.post("/campaigns/create")
@permissions(Permissions.CAMPAIGN_CREATE)
def create_campaign(auth: str, campaign: CampaignInfo, response: Response):
    try:
        db.execute(
                    f"INSERT INTO campaigns (name, dm, role, category, information_channel, min_players, max_players, "
                    f"current_players, status_message, information_message) "
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (campaign.name, campaign.dm, campaign.role, campaign.category, campaign.information_channel, campaign.min_players,
                     campaign.max_players, campaign.current_players, campaign.status_message, campaign.information_message))
        db.execute(f"CREATE TABLE IF NOT EXISTS {__get_table_name(campaign.name)} "
                   "(pid INTEGER PRIMARY KEY AUTOINCREMENT, id INTEGER UNIQUE, waitlisted INTEGER, "
                   "name TEXT, locked INTEGER DEFAULT 0)")
        db.commit()
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return json.dumps({'error': "".join(traceback.format_exception_only(type(e), e)).strip()})

    return json.dumps({"success": True})


@router.get("/manage/campaigns")
def manage_campaigns(auth: str = None):
    pass




def __get_table_name(campaign_name: str) -> str:
    return "_" + ''.join([i for i in campaign_name.replace(" ", "_") if i in string.ascii_letters or i == "_" or
                          i.isdigit()]) + "_players"

