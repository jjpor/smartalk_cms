import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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


async def get_table(db: DynamoDBServiceResource, table_name: str) -> Table:
    return await get_table(db, table_name)


def get_client(db: DynamoDBServiceResource) -> DynamoDBClient:
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
                response_json = json.dumps(response)
                # Misura la dimensione (stimata)
                received_bytes = len(response_json.encode("utf-8"))

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
