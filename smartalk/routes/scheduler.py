# routes/cron_jobs.py

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from smartalk.core.dynamodb import get_dynamodb_connection
from smartalk.core.settings import settings
from smartalk.db_usage import data_scheduler

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

# Uso della Dependency Injection per ottenere la connessione resiliente
DBDependency = Depends(get_dynamodb_connection)


###########################################################################################################
#
#            Scheduler chiamato via cron-job.org
#
# Ogni chiamata
#   - verifica l'esistenza in header del paramentro X-CRON-SECRET che deve essere uguale a CRON_SECRET
#   - usa un BackgroundTasks per rispondere subito "ok" 2 poi eseguire in background un task asincrono
#       -> lo scheduler non si ferma mai
#       -> il task viene eseguito senza fermare altre richieste di normale gestione utenti
#
###########################################################################################################


def verify_cron_secret(request: Request):
    secret = request.headers.get("X-CRON-SECRET")
    if not secret or secret != settings.CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized cron access",
        )


@router.post("/renew-watchers", dependencies=[Depends(verify_cron_secret)])
async def renew_watchers(background: BackgroundTasks):
    background.add_task(data_scheduler.renew_all_watchers)
    return {"status": "ok"}
