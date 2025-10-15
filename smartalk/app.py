import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles  # <-- Importato

# Importa i componenti chiave
from smartalk.core.dynamodb import AWS_EGRESS_DB_COUNTER_BYTES, get_dynamodb_resource_context
from smartalk.core.settings import settings
from smartalk.routes import auth, coach, student, website  # <-- Aggiunto website
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
        if settings.RUN_DATA_MIGRATION:
            await migrate_all_data(db_resource)
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

# --- MONTAGGIO FILE STATICI ---
# Questo serve tutti i file (CSS, JS, immagini) direttamente dalla cartella 'website'
# Qualsiasi richiesta a /static/... verrà cercata in website/...
app.mount("/static", StaticFiles(directory="smartalk/website"), name="website")

# --- INCLUSIONE ROUTERS ---
app.include_router(auth.router)
app.include_router(student.router)
app.include_router(coach.router)
app.include_router(website.router) # <-- Inclusa la nuova rotta per le pagine HTML

