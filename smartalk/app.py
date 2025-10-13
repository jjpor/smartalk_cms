import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

# Importa i componenti chiave
from smartalk.core.dynamodb import AWS_EGRESS_DB_COUNTER_BYTES, get_dynamodb_resource_context
from smartalk.routes import auth, student
from smartalk.scripts.create_tables import ensure_tables

# Configura il logging per visualizzare i DEBUG e INFO
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")
logger = logging.getLogger("Start Application")

# --- CICLO DI VITA (LIFESPAN) ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestisce l'avvio e la chiusura dell'applicazione."""
    logger.info("\n[AVVIO APPLICAZIONE]")

    # 1. Inizializzazione DynamoDB per lo startup
    db_context_manager = get_dynamodb_resource_context()

    # Uso di async with per la connessione di startup
    async with db_context_manager as db_resource:
        # Esegui la creazione delle tabelle
        await ensure_tables(db_resource)

    logger.info("[AVVIO COMPLETATO]\n")
    yield

    # 2. Shutdown: Stampa il totale Egress stimato
    logger.info("\n[CHIUSURA APPLICAZIONE]")
    logger.info("------------------------------------------")
    egress_mb = AWS_EGRESS_DB_COUNTER_BYTES / (1024 * 1024)
    logger.info(f"Traffico DB Inviato (AWS Egress Est.): {egress_mb:.3f} MB")
    logger.info(f"Limite Gratuito (1024 MB) Rimanente: {1024 - egress_mb:.3f} MB")
    logger.info("------------------------------------------")


app = FastAPI(title="Smartalk CMS", description="CMS for Smartalk", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(student.router)
