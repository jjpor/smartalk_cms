# smartalk/calendar_sync/router.py

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from smartalk.core.dynamodb import get_dynamodb_connection
from smartalk.db_usage import data_scheduler
from smartalk.db_usage.sync_calendars import get_sync_item_by_resource, list_all_sync_items

router = APIRouter(prefix="/calendar-sync")

# Uso della Dependency Injection per ottenere la connessione resiliente
DBDependency = Depends(get_dynamodb_connection)

logger = logging.getLogger("Calendar Sync")


# ---------------------------------------------------------------------
# CALLBACK DA GOOGLE CALENDAR (webhook)
# ---------------------------------------------------------------------
@router.post("/callback")
async def calendar_callback(
    request: Request,
    db: Any = DBDependency,
):
    """
    Endpoint chiamato da Google quando ci sono modifiche
    su un calendario sotto watch.
    """
    channel_id = request.headers.get("X-Goog-Channel-ID")
    resource_state = request.headers.get("X-Goog-Resource-State")
    resource_id = request.headers.get("X-Goog-Resource-ID")

    if not channel_id or not resource_id:
        raise HTTPException(status_code=400, detail="Invalid Google headers")

    # Trova il watcher associato
    sync_item = await get_sync_item_by_resource(db, resource_id)
    if not sync_item:
        # Google potrebbe notificare vecchi canali ormai non attivi
        logger.warning(f"Unknown or inactive resource_id {resource_id}")
        return JSONResponse(status_code=200, content={"status": "ignored"})

    calendar_id = sync_item["calendar_id"]
    coach_email = sync_item["email"]
    sync_token = sync_item.get("sync_token") or None

    logger.info(
        f"Google notification for calendar {calendar_id}, resource_state={resource_state}, channel_id={channel_id}"
    )

    # Esegui la sync dei delta
    await data_scheduler.process_calendar_delta(
        db=db,
        calendar_id=calendar_id,
        coach_email=coach_email,
        channel_id=channel_id,
        sync_token=sync_token,
    )

    return {"status": "ok"}


# ---------------------------------------------------------------------
# BOOTSTRAP: Sync iniziale & creazione watchers
# Puoi chiamarla:
# - all'avvio server (startup event)
# - da un cron interno
# ---------------------------------------------------------------------
@router.post("/bootstrap")
async def bootstrap_calendar_sync(
    db: Any = DBDependency,
):
    """
    1) Recupera tutti i coach con calendar_id
    2) Per ognuno crea/aggiorna il watcher
    3) Sincronizza i calendari da zero (sync_token=None)
    """
    # TODO: sostituisci con la tua query sui coach
    # es: coaches = await get_all_coaches(db)
    coaches = []  # <-- placeholder

    results = []

    for coach in coaches:
        calendar_id = coach["calendar_id"]
        email = coach["email"]
        coach_id = coach["id"]

        # setup/renew watcher
        channel_id, resource_id = await data_scheduler.setup_watch_for_calendar(
            db=db,
            coach_email=email,
            calendar_id=calendar_id,
            coach_id=coach_id,
        )

        # prima sync completa
        res = await data_scheduler.process_calendar_delta(
            db=db,
            calendar_id=calendar_id,
            coach_email=email,
            channel_id=channel_id,
            sync_token=None,
        )
        results.append(res.dict())

    return {"bootstrapped": len(results), "details": results}


# ---------------------------------------------------------------------
# RENEW: rinnova watchers vicini alla scadenza
# Da chiamare via cron (es. ogni ora)
# ---------------------------------------------------------------------
@router.post("/renew-watchers")
async def renew_watchers(
    db: Any = DBDependency,
):
    now_ms = int(time.time() * 1000)
    items = await list_all_sync_items(db)

    renewed = 0
    for item in items:
        calendar_id = item["calendar_id"]
        email = item["email"]
        coach_id = item.get("coach_id") or None
        expiration = int(item["expiration"])

        # Se scade entro 24 ore → rinnova
        if expiration - now_ms < 24 * 3600 * 1000:
            await data_scheduler.setup_watch_for_calendar(
                db=db,
                coach_email=email,
                calendar_id=calendar_id,
                coach_id=coach_id,
            )
            renewed += 1

    return {"renewed": renewed}
