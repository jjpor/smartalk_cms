import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, AsyncGenerator, Dict, List, Optional

from aioboto3 import Session as AioSession
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
from types_aiobotocore_dynamodb.client import DynamoDBClient

from smartalk.core.settings import settings

# Inizializzazione logger
logger = logging.getLogger("aws_egress_db_counter")
logger.setLevel(logging.INFO)  # Mantenere INFO per vedere il conteggio

# Contatore globale che stima il traffico in uscita da AWS (DB -> Server)
AWS_EGRESS_DB_COUNTER_BYTES = 0
lock = asyncio.Lock()


def get_today_string(today: date = None):
    if today is None:
        return datetime.now(timezone.utc).date().isoformat()
    else:
        return today.isoformat()


def to_low_level_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte un dizionario Python (alto livello) in formato DynamoDB low-level.
    Es.: {"a": "x", "b": 5, "c": True} → {"a": {"S": "x"}, "b": {"N": "5"}, "c": {"BOOL": True}}
    """
    low_level_item = {}

    for k, v in item.items():
        if isinstance(v, str):
            low_level_item[k] = {"S": v}
        elif isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
            low_level_item[k] = {"N": str(v)}
        elif isinstance(v, bool):
            low_level_item[k] = {"BOOL": v}
        elif v is None:
            low_level_item[k] = {"NULL": True}
        elif isinstance(v, dict):
            # ricorsivo per nested map
            low_level_item[k] = {"M": to_low_level_item(v)}
        elif isinstance(v, (list, tuple, set)):
            # ricorsivo per liste
            low_level_item[k] = {"L": [to_low_level_item({"_": i})["_"] for i in v]}
        else:
            raise TypeError(f"Tipo non supportato per l'attributo '{k}': {type(v)}")

    return low_level_item


def to_dynamodb_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Converts a dictionary to a clean format for DynamoDB."""
    final_item = {}
    for key, value in item.items():
        if isinstance(value, date):
            final_item[key] = value.isoformat()
        elif isinstance(value, datetime):
            final_item[key] = value.isoformat()
        # Convert any float to a Decimal before sending to DynamoDB
        elif isinstance(value, float):
            final_item[key] = Decimal(str(value))
        elif value is not None and value != "":
            final_item[key] = value
    return final_item


async def get_table(db: DynamoDBServiceResource, table_name: str) -> Table:
    return await db.Table(table_name)


async def get_item(db: DynamoDBServiceResource, table_name: str, keys: dict) -> Table:
    table = await get_table(db, table_name)
    item_response = await table.get_item(Key=keys)
    return item_response.get("Item", {})


def get_db_client(db: DynamoDBServiceResource) -> DynamoDBClient:
    return db.meta.client


def get_dynamodb_resource_context():
    """
    Restituisce l'AsyncContextManager (session.resource(...)).
    Gestisce la logica condizionale per l'ambiente (Locale vs AWS).
    """

    # Prepara i parametri della Sessione AioBoto3.
    # Se le variabili sono stringhe vuote (""), 'or None' le converte in None,
    # affidandosi alle credenziali implicite (IAM, variabili d'ambiente).
    session = AioSession(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        region_name=settings.AWS_REGION,
    )

    kwargs = {}

    # Configura endpoint_url solo se specificato (caso locale/custom)
    if settings.DYNAMO_ENDPOINT:
        kwargs["endpoint_url"] = settings.DYNAMO_ENDPOINT
        logger.info(f"Connessione a Endpoint Locale/Custom: {settings.DYNAMO_ENDPOINT}")
    else:
        logger.info(f"Connessione a Endpoint AWS Standard in regione: {settings.AWS_REGION}")

    # Restituisce il gestore di contesto asincrono
    return session.resource("dynamodb", **kwargs)


class DynamoDBResourceWrapper:
    """
    Wrapper che avvolge la risorsa DynamoDB per intercettare i metodi di lettura
    e misurare i byte della risposta.
    """

    def __init__(self, resource):
        self._resource = resource

    def __getattr__(self, name):
        # Ottiene l'attributo/metodo reale dalla risorsa sottostante
        attr = getattr(self._resource, name)

        # Intercetta solo i metodi che restituiscono dati
        if callable(attr) and name in ("get_item", "scan", "query", "batch_get_item"):
            return self._wrap_method(attr, name)

        return attr

    def _wrap_method(self, original_method, method_name):
        # Funzione di wrapping asincrona
        async def wrapped_method(*args, **kwargs):
            try:
                # Esegue l'operazione reale su DynamoDB
                response = await original_method(*args, **kwargs)

                # Misurazione: serializza la risposta per stimare i byte ricevuti
                response_json = json.dumps(response, separators=(",", ":")).encode("utf-8")
                # Misura la dimensione (stimata)
                received_bytes = len(response_json)

                # Aggiornamento del Contatore Globale
                global AWS_EGRESS_DB_COUNTER_BYTES
                current_counter = None
                async with lock:
                    AWS_EGRESS_DB_COUNTER_BYTES += received_bytes
                    current_counter = AWS_EGRESS_DB_COUNTER_BYTES

                logger.info(f"-> DB {method_name} | Received: {received_bytes / 1024:.2f} KB")
                logger.info(f"Total current received from db: {current_counter / 1024**2:.2f} MB")

                return response
            except Exception as e:
                logger.error(f"Errore DB in {method_name}: {e}")
                raise

        return wrapped_method


@asynccontextmanager
async def get_dynamodb_connection() -> AsyncGenerator:
    """
    Dependency Injection per ottenere la connessione resiliente (risolve TypeError)
    e applica il wrapper di misurazione.
    """
    db_context_manager = get_dynamodb_resource_context()

    # Uso di async with per creare la risorsa in modo asincrono
    async with db_context_manager as db_resource:
        try:
            # Passa la risorsa DynamoDB wrappata alla funzione che la richiede
            yield DynamoDBResourceWrapper(db_resource)
        except Exception as e:
            logger.critical(f"Errore CRITICO durante l'inizializzazione/uso di DynamoDB: {e}")
            raise


async def _count_db_egress_bytes(op_name: str, response: Dict) -> None:
    """Stima i byte ricevuti serializzando la response come JSON compatto."""
    try:
        # JSON “compatto” per non sovrastimare con spaziature
        payload = json.dumps(response, separators=(",", ":")).encode("utf-8")
        received_bytes = len(payload)

        global AWS_EGRESS_DB_COUNTER_BYTES
        async with lock:
            AWS_EGRESS_DB_COUNTER_BYTES += received_bytes
            total = AWS_EGRESS_DB_COUNTER_BYTES

        logger.info(f"-> DB {op_name} | Received: {received_bytes / 1024:.2f} KB")
        logger.info(f"Total current received from db: {total / 1024**2:.2f} MB")
    except Exception as e:
        logger.warning(f"Impossibile stimare egress per {op_name}: {e}")


# ---------------------------
# Funzione unica
# ---------------------------
async def make_atomic_transaction(
    db: DynamoDBServiceResource,
    checks: Optional[List[Dict]] = None,
    puts: Optional[List[Dict]] = None,
    updates: Optional[List[Dict]] = None,
    deletes: Optional[List[Dict]] = None,
    gets: Optional[List[Dict]] = None,
) -> Dict | None:
    """
    Esegue una transazione DynamoDB “generica”:
      - Se passi SOLO `gets`: usa TransactGetItems.
      - In tutti gli altri casi: TransactWriteItems (combinando checks/puts/updates/deletes).

    I singoli item vanno in *wire format* DynamoDB (uguali a quelli di boto/aioboto),
    es.: {"Update": {...}}, {"Put": {...}}, {"ConditionCheck": {...}}, {"Get": {...}}.

    Lancia errori non transitori.
    """
    checks = checks or []
    puts = puts or []
    updates = updates or []
    deletes = deletes or []
    gets = gets or []

    # Validazioni base
    if any([checks, puts, updates, deletes]) and gets:
        raise ValueError("TransactGetItems e TransactWriteItems non si possono mescolare nella stessa chiamata.")
    if not any([checks, puts, updates, deletes, gets]):
        raise ValueError("Nessuna operazione passata.")

    # ----- TransactGetItems -----
    if gets and not any([checks, puts, updates, deletes]):
        if len(gets) > 25:
            raise ValueError("TransactGetItems: max 25 operazioni.")

        response = await get_db_client(db).transact_get_items(
            TransactItems=[{"Get": g["Get"]} if "Get" in g else {"Get": g} for g in gets]
        )

        # Conteggio egress per le get transaction
        await _count_db_egress_bytes("transact_get_items", response)
        return response

    # ----- TransactWriteItems -----
    if not gets and any([checks, puts, updates, deletes]):
        items: List[Dict] = []

        for chk in checks:
            items.append({"ConditionCheck": chk.get("ConditionCheck", chk)})

        for put in puts:
            items.append({"Put": put.get("Put", put)})

        for upd in updates:
            items.append({"Update": upd.get("Update", upd)})

        for dele in deletes:
            items.append({"Delete": dele.get("Delete", dele)})

        if len(items) == 0:
            raise ValueError("Nessun item di write (checks/puts/updates/deletes).")
        if len(items) > 25:
            raise ValueError("TransactWriteItems: max 25 operazioni.")

        await get_db_client(db).transact_write_items(TransactItems=items)
