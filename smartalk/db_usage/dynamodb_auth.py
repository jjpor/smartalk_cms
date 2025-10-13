import datetime
import logging
import uuid
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

from smartalk.core.settings import settings

logger = logging.Logger("Auth")

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
    table = await db.Table(settings.USERS_TABLE)
    norm = normalize_email(email)

    resp = await table.query(
        IndexName="email-index",
        KeyConditionExpression="email = :email",
        ExpressionAttributeValues={":email": {"S": norm}},
        Limit=1,
    )

    items = resp.get("Items", [])
    if not items:
        return None

    user_id = items[0]["id"]["S"]
    full = await table.get_item(Key={"id": {"S": user_id}})
    return full.get("Item")


async def get_user_by_id(user_id: str, db: dict) -> Optional[Dict[str, Any]]:
    table = await db.Table(settings.USERS_TABLE)
    full = await table.get_item(Key={"id": {"S": user_id}})
    return full.get("Item")


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


async def create_user_if_not_exists(email: str, name: str, db) -> Dict[str, Any]:
    # La probabilità di avere un uuid già usato è bassissima
    # Avere 10 volte consecutive un uuid già usato è praticamente impossibile
    table = await db.Table(settings.USERS_TABLE)
    norm_email = normalize_email(email)

    for attempt in range(10):
        user_id = f"u_{uuid.uuid4().hex[:10]}"
        if attempt > 0:
            logger.info(f"Collisione ID DynamoDB rilevata. Tentativo {attempt + 1} con nuovo ID: {user_id}")

        item = {
            "id": user_id,
            "email": norm_email,
            "name": name,
            "created_at": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
        }

        try:
            # Atomicita' su ID: l'ID viene inserito solo se non esiste.
            await table.put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
            # Successo
            return item

        except ClientError as e:
            # Codice di eccezione specifico quando la condizione fallisce
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # Continua con il prossimo uuid
                continue
            else:
                # Altro errore DB, solleva
                raise e

    # Fallimento definitivo
    raise Exception("Impossibile creare l'utente. Falliti 10 tentativi per collisione ID.")
