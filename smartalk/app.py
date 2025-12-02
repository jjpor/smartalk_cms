import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from smartalk.core.dynamodb import AWS_EGRESS_DB_COUNTER_BYTES, get_dynamodb_resource_context, get_table
from smartalk.core.settings import settings

# from smartalk.db_usage.data_scheduler import (
#     get_all_coaches,
#     process_calendar_delta,
#     setup_watch_for_calendar,
# )
from smartalk.db_usage.sync_calendars import get_sync_item
from smartalk.routes import auth, coach, student, website

# from smartalk.routes import calendar_sync, scheduler
from smartalk.scripts.create_tables import ensure_tables
from smartalk.scripts.migrate_data import migrate_all_data

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s — %(levelname)s — %(name)s — %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("Smartalk Startup")


# -----------------------------------------------------
# STARTUP FLAG (evita doppia esecuzione)
# -----------------------------------------------------
DO_STARTUP = True


# -----------------------------------------------------
# LIFESPAN (solo creazione tabelle)
# -----------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestisce l'avvio e la chiusura dell'applicazione."""
    logger.info("\n[AVVIO APPLICAZIONE]")

    db_context = get_dynamodb_resource_context()
    async with db_context as db:
        # 1. crea tabelle
        await ensure_tables(db)
        logger.info("Tabelle DynamoDB pronte.")

    yield

    logger.info("\n[CHIUSURA APPLICAZIONE]")
    mb = AWS_EGRESS_DB_COUNTER_BYTES / (1024 * 1024)
    logger.info(f"Egress DB inviato: {mb:.4f} MB")
    logger.info("Shutdown completato.")


# --- CREAZIONE APP ---
app = FastAPI(
    title="Smartalk CMS API",
    description="API per gestione Smartalk",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files
app.mount("/static", StaticFiles(directory="smartalk/website/static"), name="static")


# every not defined path
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return await website.get_no_handled_path(request)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://smartalk.online",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(student.router)
app.include_router(coach.router)
# app.include_router(scheduler.router)
# app.include_router(calendar_sync.router)
app.include_router(website.router)


@app.get("/startup")
async def unified_startup(x_internal_key: str | None = None):
    """
    Esegue:
    - migrazione dati
    - setup watchers Google Calendar
    - sync iniziale

    Può essere eseguito *una sola volta*.
    """

    global DO_STARTUP

    if x_internal_key != settings.INTERNAL_STARTUP_KEY:
        raise HTTPException(403, "Invalid startup key")

    if not DO_STARTUP:
        raise HTTPException(403, "Startup già eseguito. Operazione non ammessa.")

    # Disattiva ulteriori invocazioni
    DO_STARTUP = False

    db_context = get_dynamodb_resource_context()
    async with db_context as db:
        # 1. Migrazione (se abilitata)
        if settings.RUN_DATA_MIGRATION:
            logger.info("Eseguo MIGRAZIONE DATI...")
            await migrate_all_data(db)
            logger.info("Migrazione completata.")

        # if settings.RUN_INIT_CALENDARS:
        #     # 2. Watchers Google Calendar
        #     logger.info("Avvio watchers Google Calendar...")
        #     coaches = await get_all_coaches(db)

        #     for c in coaches:
        #         calendar_id = c["calendar_id"]
        #         email = c["email"]

        #         sync_item = await get_sync_item(db, calendar_id)

        #         # se non c'è watcher → crealo
        #         if not sync_item:
        #             await setup_watch_for_calendar(db, email, calendar_id)
        #             sync_token = None  # primo sync
        #         else:
        #             sync_token = sync_item.get("sync_token")

        #         # sync incrementale se disponibile, full se no
        #         await process_calendar_delta(
        #             db=db,
        #             calendar_id=calendar_id,
        #             coach_email=email,
        #             sync_token=sync_token,
        #         )

        #     logger.info("Watchers attivi e sincronizzazione completa.")

    return {"status": "startup_completed"}


# -------------------------------------------------
# test see data ENDPOINTS
# -------------------------------------------------


# @app.get("/test_gsi")
# async def test_gsi(student_id):
#     db_context_manager = get_dynamodb_resource_context()
#     async with db_context_manager as db:
#         contract_table = await get_table(db, settings.CONTRACTS_TABLE)
#         response = await contract_table.query(
#             IndexName="student-id-status-index",
#             KeyConditionExpression="student_id = :student_id",
#             ExpressionAttributeValues={":student_id": student_id},
#             Limit=1,
#         )
#         contract_id = response["Items"][0]["contract_id"]
#         return contract_id


# Mappa per mappare i nomi brevi ai nomi completi delle tabelle
TABLE_MAP = {
    "users": settings.USERS_TABLE,
    "products": settings.PRODUCTS_TABLE,
    "contracts": settings.CONTRACTS_TABLE,
    "calls": settings.CALLS_TABLE,
    "invoices": settings.INVOICES_TABLE,
    "report_cards": settings.REPORT_CARDS_TABLE,
    "report_card_generators": settings.REPORT_CARD_GENERATORS_TABLE,
    "debriefs": settings.DEBRIEFS_TABLE,
    "company_employees": settings.COMPANY_EMPLOYEES_TABLE,
    "booking_calls": settings.BOOKING_CALLS_TABLE,
}


@app.get("/see_data")
async def see_table_data(table_short_name: str):
    """
    Servizio di debug per visualizzare tutti i dati di una tabella.
    Usa un nome breve per la tabella (es. 'users', 'products').
    """
    db_ = get_dynamodb_resource_context()
    async with db_ as db:
        if table_short_name not in TABLE_MAP:
            raise HTTPException(
                status_code=404, detail=f"Nome tabella non valido. Usare uno tra: {list(TABLE_MAP.keys())}"
            )

        table_name = TABLE_MAP[table_short_name]

        try:
            table = await get_table(db, table_name)
            # L'operazione 'scan' legge tutti gli item in una tabella.
            # ATTENZIONE: può essere costosa su tabelle molto grandi in produzione.
            response = await table.scan()
            items = response.get("Items", [])

            # Gestisce la paginazione se la tabella è grande
            while "LastEvaluatedKey" in response:
                response = await table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))

            return {"quantity": len(items), "items": items}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Errore durante la lettura della tabella {table_name}: {e}")


# @app.get("/reset")
# async def reset_database():
#     """
#     ATTENZIONE: Servizio distruttivo. Cancella e ricrea tutte le tabelle.
#     Esegue l'operazione in background per non bloccare la risposta.
#     """

#     db_ = get_dynamodb_resource_context()
#     async with db_ as db:
#         logger = logging.getLogger("db_reset")
#         logger.warning("--- INIZIO RESET DATABASE ---")

#         # FASE 1: Cancella tutte le tabelle esistenti
#         for table_name in TABLE_MAP.values():
#             try:
#                 logger.info(f"Cancellazione tabella: {table_name}...")
#                 table = await get_table(db, table_name)
#                 await table.delete()
#                 # Attende che la tabella sia effettivamente cancellata
#                 waiter = db.meta.client.get_waiter("table_not_exists")
#                 await waiter.wait(TableName=table_name)
#                 logger.info(f"Tabella {table_name} cancellata con successo.")
#             except db.meta.client.exceptions.ResourceNotFoundException:
#                 logger.warning(f"La tabella {table_name} non esisteva, skipped.")
#             except Exception as e:
#                 logger.error(f"Errore durante la cancellazione di {table_name}: {e}")

#         # Breve attesa per stabilizzare DynamoDB
#         await asyncio.sleep(5)

#         # FASE 2: Ricrea le tabelle vuote
#         logger.info("--- Recreazione di tutte le tabelle ---")
#         await ensure_tables(db)
#         logger.warning("--- RESET DATABASE COMPLETATO ---")
