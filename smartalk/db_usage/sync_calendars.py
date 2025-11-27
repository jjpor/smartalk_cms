# smartalk/calendar_sync/dynamodb_sync.py

import logging
from typing import List, Optional

from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from smartalk.core.dynamodb import delete_item, get_item, put_item
from smartalk.core.settings import settings

logger = logging.getLogger(__name__)


CALENDAR_SYNC_TABLE = settings.CALENDAR_SYNC_TABLE


async def put_sync_item(
    db: DynamoDBServiceResource,
    calendar_id: str,
    channel_id: str,
    resource_id: str,
    expiration: int,
    coach_email: str,
    coach_id: Optional[str] = None,
    sync_token: Optional[str] = None,
    active: bool = True,
) -> None:
    item = {
        "calendar_id": calendar_id,
        "channel_id": channel_id,
        "resource_id": resource_id,
        "expiration": expiration,
        "email": coach_email,
        "coach_id": coach_id or "",
        "sync_token": sync_token or "",
        "active": active,
    }
    await put_item(db, CALENDAR_SYNC_TABLE, item, ["calendar_id", "channel_id"])


def get_sync_item_by_resource(
    db: DynamoDBServiceResource,
    resource_id: str,
) -> Optional[dict]:
    table = db.Table(CALENDAR_SYNC_TABLE)

    resp = table.query(
        IndexName="GSI1-resource",
        KeyConditionExpression=Key("resource_id").eq(resource_id),
        Limit=1,
    )
    items = resp.get("Items") or []
    return items[0] if items else None


def get_sync_item(
    db: DynamoDBServiceResource,
    calendar_id: str,
) -> Optional[dict]:
    table = db.Table(CALENDAR_SYNC_TABLE)

    resp = table.query(
        KeyConditionExpression=Key("calendar_id").eq(calendar_id),
        Limit=5,
    )
    items = resp.get("Items") or []

    for it in items:
        if it.get("active") == "true":
            return it

    return None


def update_sync_token(
    db: DynamoDBServiceResource,
    calendar_id: str,
    channel_id: str,
    sync_token: str,
) -> None:
    table = db.Table(CALENDAR_SYNC_TABLE)
    table.update_item(
        Key={"calendar_id": calendar_id, "channel_id": channel_id},
        UpdateExpression="SET sync_token = :st",
        ExpressionAttributeValues={":st": sync_token},
    )


def deactivate_existing_channels(
    db: DynamoDBServiceResource,
    calendar_id: str,
) -> None:
    table = db.Table(CALENDAR_SYNC_TABLE)

    resp = table.query(
        KeyConditionExpression=Key("calendar_id").eq(calendar_id),
    )
    items = resp.get("Items") or []

    for it in items:
        table.update_item(
            Key={"calendar_id": it["calendar_id"], "channel_id": it["channel_id"]},
            UpdateExpression="SET active = :false",
            ExpressionAttributeValues={":false": "false"},
        )


def list_active_for_renew(
    db: DynamoDBServiceResource,
) -> List[dict]:
    table = db.Table(CALENDAR_SYNC_TABLE)

    resp = table.query(
        IndexName="GSI2-active",
        KeyConditionExpression=Key("active").eq("true"),
    )
    return resp.get("Items") or []
