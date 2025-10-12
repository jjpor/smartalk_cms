import datetime
import uuid
from typing import Any, Dict, List, Optional

import aioboto3
from botocore.exceptions import ClientError

from smartalk.core.settings import settings

# -----------------------------
# COSTANTI
# -----------------------------

USERS_TABLE = "Users"

# -----------------------------
# SESSIONE DYNAMODB
# -----------------------------

_session = None


async def get_dynamodb():
    """
    Restituisce una risorsa DynamoDB configurata per ambiente locale o cloud.
    """
    global _session
    if _session is None:
        session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        endpoint = settings.DYNAMO_ENDPOINT or None
        _session = await session.resource("dynamodb", endpoint_url=endpoint)
    return _session


# -----------------------------
# UTILITIES
# -----------------------------


def normalize_email(email: str) -> str:
    """
    Canonicalizza un indirizzo email:
    - lowercase
    - per @gmail.com e @googlemail.com rimuove i punti
    """
    email = email.strip().casefold()
    local, _, domain = email.partition("@")
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
    return f"{local}@{domain}"


def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds") + "Z"


# -----------------------------
# USERS
# -----------------------------


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Recupera un utente tramite il GSI email-index (KEYS_ONLY).
    """
    db = await get_dynamodb()
    client = db.meta.client
    norm = normalize_email(email)

    resp = await client.query(
        TableName=USERS_TABLE,
        IndexName="email-index",
        KeyConditionExpression="email = :email",
        ExpressionAttributeValues={":email": {"S": norm}},
        Limit=1,
    )

    items = resp.get("Items", [])
    if not items:
        return None

    user_id = items[0]["id"]["S"]
    full = await client.get_item(TableName=USERS_TABLE, Key={"id": {"S": user_id}})
    return full.get("Item")


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    db = await get_dynamodb()
    table = await db.Table(USERS_TABLE)
    resp = await table.get_item(Key={"id": user_id})
    return resp.get("Item")


async def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggiorna campi specifici dell'utente (merge).
    """
    db = await get_dynamodb()
    table = await db.Table(USERS_TABLE)

    update_expr = []
    expr_vals = {}
    for k, v in updates.items():
        update_expr.append(f"{k} = :{k}")
        expr_vals[f":{k}"] = v

    resp = await table.update_item(
        Key={"id": user_id},
        UpdateExpression="SET " + ", ".join(update_expr),
        ExpressionAttributeValues=expr_vals,
        ReturnValues="ALL_NEW",
    )
    return resp["Attributes"]


async def create_user_if_not_exists(user_id: str, email: str, name: str) -> Dict[str, Any]:
    """
    Crea un nuovo utente se non esiste già.
    """
    db = await get_dynamodb()
    table = await db.Table(USERS_TABLE)

    norm_email = normalize_email(email)
    item = {
        "id": user_id,
        "email": norm_email,
        "name": name,
        "coins": 0,
        "ads_seen": 0,
        "subscription": {"type": None, "status": "inactive", "renew_at": None},
        "created_at": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
        "current_portfolio_snapshot_id": None,
        "current_sop_snapshot_id": None,
    }

    await table.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
    return item


