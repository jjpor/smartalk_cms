import datetime
from typing import Any, Dict, Optional

from smartalk.core.settings import settings

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


async def get_user_by_email(email: str, db: dict) -> Optional[Dict[str, Any]]:
    """
    Recupera un utente tramite il GSI email-index (KEYS_ONLY).
    """
    client = db.meta.client
    norm = normalize_email(email)

    resp = await client.query(
        TableName=settings.USERS_TABLE,
        IndexName="email-index",
        KeyConditionExpression="email = :email",
        ExpressionAttributeValues={":email": {"S": norm}},
        Limit=1,
    )

    items = resp.get("Items", [])
    if not items:
        return None

    user_id = items[0]["id"]["S"]
    full = await client.get_item(TableName=settings.USERS_TABLE, Key={"id": {"S": user_id}})
    return full.get("Item")


async def get_user_by_id(user_id: str, db: dict) -> Optional[Dict[str, Any]]:
    table = await db.Table(settings.USERS_TABLE)
    resp = await table.get_item(Key={"id": user_id})
    return resp.get("Item")


async def update_user(user_id: str, updates: Dict[str, Any], db: dict) -> Dict[str, Any]:
    """
    Aggiorna campi specifici dell'utente (merge).
    """
    table = await db.Table(settings.USERS_TABLE)

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


async def create_user_if_not_exists(user_id: str, email: str, name: str, db: dict) -> Dict[str, Any]:
    """
    Crea un nuovo utente se non esiste già.
    """
    table = await db.Table(settings.USERS_TABLE)

    norm_email = normalize_email(email)
    item = {
        "id": user_id,
        "email": norm_email,
        "name": name,
        "created_at": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
    }

    await table.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
    return item
