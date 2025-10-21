import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# Importa i componenti chiave
from smartalk.core.dynamodb import AWS_EGRESS_DB_COUNTER_BYTES, get_dynamodb_resource_context
from smartalk.core.settings import settings
from smartalk.routes import auth, coach, student, website
from smartalk.scripts.create_tables import ensure_tables
from smartalk.scripts.migrate_data import migrate_all_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")
logger = logging.getLogger("Start Application")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestisce l'avvio e la chiusura dell'applicazione."""
    logger.info("\n[AVVIO APPLICAZIONE]")
    db_context_manager = get_dynamodb_resource_context()
    async with db_context_manager as db_resource:
        await ensure_tables(db_resource)
    logger.info("[AVVIO COMPLETATO]\n")
    yield
    logger.info("\n[CHIUSURA APPLICAZIONE]")
    egress_mb = AWS_EGRESS_DB_COUNTER_BYTES / (1024 * 1024)
    logger.info(f"Traffico DB Inviato (AWS Egress Est.): {egress_mb:.4f} MB")

# --- CREAZIONE APP ---
app = FastAPI(
    title="Smartalk CMS API",
    description="API per la gestione dei dati di Smartalk",
    version="1.0.0",
    lifespan=lifespan,
)

# every not defined path
@app.exception_handler(404)
async def custom_404_handler(request: Request,_):
    return await website.get_no_handled_path(request)


# --- 2. CONFIGURAZIONE CORS ---
# Definisci quali origini (frontend) possono chiamare le tue API
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://smartalk.online"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INCLUSIONE ROUTERS ---
app.include_router(auth.router)
app.include_router(student.router)
app.include_router(coach.router)
app.include_router(website.router) # <-- Inclusa la nuova rotta per le pagine HTML



# -------------------------------------------------
# migration ENDPOINTS
# -------------------------------------------------


@app.get("/migration")
async def migration():
    if settings.RUN_DATA_MIGRATION:
        db_context_manager = get_dynamodb_resource_context()
        async with db_context_manager as db_resource:        
            await migrate_all_data(db_resource)


# -------------------------------------------------
# test see data ENDPOINTS
# -------------------------------------------------

@app.get("/test_gsi")
async def test_gsi(student_id):
    db_context_manager = get_dynamodb_resource_context()
    async with db_context_manager as db:  
        contract_table = await db.Table(settings.CONTRACTS_TABLE)
        response = await contract_table.query(
            IndexName="student-id-index",
            KeyConditionExpression="student_id = :student_id",
            ExpressionAttributeValues={":student_id": student_id},
            Limit=1,
        )
        contract_id = response['Items'][0]['contract_id']
        return contract_id

# Mappa per mappare i nomi brevi ai nomi completi delle tabelle
TABLE_MAP = {
    "users": settings.USERS_TABLE,
    "products": settings.PRODUCTS_TABLE,
    "contracts": settings.CONTRACTS_TABLE,
    "tracker": settings.TRACKER_TABLE,
    "invoices": settings.INVOICES_TABLE,
    "reportcards": settings.REPORT_CARDS_TABLE,
    "debriefs": settings.DEBRIEFS_TABLE,
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
                status_code=404,
                detail=f"Nome tabella non valido. Usare uno tra: {list(TABLE_MAP.keys())}"
            )

        table_name = TABLE_MAP[table_short_name]
        
        try:
            table = await db.Table(table_name)
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
            raise HTTPException(
                status_code=500,
                detail=f"Errore durante la lettura della tabella {table_name}: {e}"
            )
        

@app.get("/reset")
async def reset_database():
    """
    ATTENZIONE: Servizio distruttivo. Cancella e ricrea tutte le tabelle.
    Esegue l'operazione in background per non bloccare la risposta.
    """
    
    db_ = get_dynamodb_resource_context()
    async with db_ as db: 
        logger = logging.getLogger("db_reset")
        logger.warning("--- INIZIO RESET DATABASE ---")
        
        # FASE 1: Cancella tutte le tabelle esistenti
        for table_name in TABLE_MAP.values():
            try:
                logger.info(f"Cancellazione tabella: {table_name}...")
                table = await db.Table(table_name)
                await table.delete()
                # Attende che la tabella sia effettivamente cancellata
                waiter = db.meta.client.get_waiter('table_not_exists')
                await waiter.wait(TableName=table_name)
                logger.info(f"Tabella {table_name} cancellata con successo.")
            except db.meta.client.exceptions.ResourceNotFoundException:
                logger.warning(f"La tabella {table_name} non esisteva, skipped.")
            except Exception as e:
                logger.error(f"Errore durante la cancellazione di {table_name}: {e}")

        # Breve attesa per stabilizzare DynamoDB
        await asyncio.sleep(5)

        # FASE 2: Ricrea le tabelle vuote
        logger.info("--- Recreazione di tutte le tabelle ---")
        await ensure_tables(db)
        logger.warning("--- RESET DATABASE COMPLETATO ---")
