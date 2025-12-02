import logging
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
from typing import Any, Dict, List, Optional

import pandas as pd
from aiogoogle import Aiogoogle
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from pydantic import BaseModel

from smartalk.core.dynamodb import (
    delete_item,
    get_item,
    get_table,
    get_today_string,
    make_atomic_transaction,
    put_item,
    to_dynamodb_item,
    to_low_level_item,
)
from smartalk.core.settings import settings
from smartalk.db_usage.sync_calendars import (
    deactivate_existing_channels,
    list_all_sync_items,
    put_sync_item,
    update_sync_token,
)
from smartalk.email_and_automations.utils.calendars_manager import CalendarManager

logger = logging.getLogger(__name__)


class CalendarSyncItem(BaseModel):
    calendar_id: str
    channel_id: str
    resource_id: str
    coach_id: str | None = None
    email: str
    sync_token: str | None = None
    expiration: int  # epoch ms
    active: bool = True


class CalendarDeltaResult(BaseModel):
    calendar_id: str
    processed_events: int
    new_sync_token: str | None = None


async def get_all_coaches(
    db: DynamoDBServiceResource,
):
    pass


async def process_calendar_delta(
    db: DynamoDBServiceResource,
    calendar_id: str,
    coach_email: str,
    channel_id: str,
    sync_token: Optional[str],
) -> CalendarDeltaResult:
    """
    Usa events.list con syncToken (se presente) per ottenere
    solo i delta, e aggiorna DynamoDB (prenotazioni/slot).
    """

    calendar_manager = CalendarManager(coach_email, calendar_id)
    async with calendar_manager._client() as ag:
        api = await ag.discover("calendar", "v3")

        if sync_token:
            resp = await ag.as_service_account(
                api.events.list(
                    calendarId=calendar_id,
                    syncToken=sync_token,
                    showDeleted=True,
                )
            )
        else:
            # Prima sync completa (occhio se il calendario è grande)
            resp = await ag.as_service_account(
                api.events.list(
                    calendarId=calendar_id,
                    showDeleted=True,
                    singleEvents=True,
                    maxResults=2500,
                )
            )

    items = resp.get("items", [])
    logger.info(f"Calendar {calendar_id}: received {len(items)} delta events")

    # QUI: logica di mapping evento -> DynamoDB
    for event in items:
        await handle_event_delta(db, calendar_id, event)

    new_sync_token = resp.get("nextSyncToken")
    if new_sync_token:
        await update_sync_token(db, calendar_id, channel_id, new_sync_token)

    return CalendarDeltaResult(
        calendar_id=calendar_id,
        processed_events=len(items),
        new_sync_token=new_sync_token,
    )


async def setup_watch_for_calendar(
    db: DynamoDBServiceResource,
    coach_email: str,
    calendar_id: str,
    coach_id: str | None = None,
):
    """
    Crea un watcher (webhook channel) per il calendario indicato.
    Deattiva eventuali watcher precedenti per quel calendario
    e salva su DynamoDB.
    """
    channel_id = f"smartalk-{uuid.uuid4()}"
    address = settings.CALENDAR_SYNC_WEBHOOK_URL

    calendar_manager = CalendarManager(coach_email, calendar_id)
    async with calendar_manager._client() as ag:
        api = await ag.discover("calendar", "v3")

        body = {
            "id": channel_id,
            "type": "web_hook",
            "address": address,
        }

        resp = await ag.as_service_account(api.events.watch(calendarId=calendar_id, json=body))

    resource_id = resp["resourceId"]
    expiration = int(resp["expiration"])

    # Deattiva canali precedenti
    await deactivate_existing_channels(db, calendar_id)

    # Salva il nuovo sync item
    await put_sync_item(
        db=db,
        calendar_id=calendar_id,
        channel_id=channel_id,
        resource_id=resource_id,
        expiration=expiration,
        coach_email=coach_email,
        coach_id=coach_id,
        sync_token=None,
        active=True,
    )

    logger.info(f"Created watch channel for {calendar_id} with id {channel_id}")

    return channel_id, resource_id


async def renew_all_watchers():
    items = await list_all_sync_items()
    now_ms = int(time.time() * 1000)

    for item in items:
        if item["expiration"] - now_ms < 24 * 3600 * 1000:
            await setup_watch_for_calendar(item["email"], item["calendar_id"])


# async def update_booked_calls(db: DynamoDBServiceResource) -> None:
#     """
#     Prende le prenotazioni dal db con status "cancelable"
#         Per ogni call che avverrà entro 23 ore
#             se è ancora sul calendario con i partecipanti accettati
#                 sul db aggiorna lo status a "confirmed"
#             se sul calendario lo studente ha rifiutato ma il coach no
#                 sul db aggiorna lo status a "confirmed" (la call verrà conteggiata e lo studente sarà segnato assente)
#             se sul calendario lo studente non ha rifiutato ma il coach sì
#                 sul db aggiorna lo status a "canceled_by_coach"
#                 si allunga in maniera coerente la max_end_date del contratto legato alla prenotazione
#             se non è più presente sul calendario o entrambi hanno rifiutato
#                 elimina dal db la prenotazione
#         Per ogni call che avverrà fra oltre 23 ore
#             se sul calendario lo studente ha rifiutato ma il coach no
#                 sul db aggiorna lo status a "canceled_by_student"
#             se sul calendario lo studente non ha rifiutato ma il coach sì
#                 sul db aggiorna lo status a "canceled_by_coach"
#                 si allunga in maniera coerente la max_end_date del contratto legato alla prenotazione
#             se non è più presente sul calendario o entrambi hanno rifiutato
#                 elimina dal db la prenotazione


#     Legge le prenotazioni con status in ["cancelable", "confirmed"] che avverranno fra 23 ore
#     """
#     pass


# ---------------------------------------------------------------------
# Qui metti la logica di sincronizzazione con le tue tabelle DynamoDB
# (BOOKING_CALLS, eventuale tabella SLOTS, ecc.)
# ---------------------------------------------------------------------
# TODO: mettere logica specifica
async def handle_event_delta(
    db: DynamoDBServiceResource,
    calendar_id: str,
    event: dict,
) -> None:
    """
    Aggiorna DynamoDB in base al singolo evento cambiato.
    Qui devi mappare la tua logica FREE/BUSY, booking, ecc.
    """
    event_id = event["id"]
    status = event.get("status")  # confirmed | cancelled
    transparency = event.get("transparency", "opaque")  # transparent | opaque

    start_raw = (event.get("start") or {}).get("dateTime")
    end_raw = (event.get("end") or {}).get("dateTime")

    # Evento cancellato → togli eventuale prenotazione o slot
    if status == "cancelled":
        # TODO: rimuovere o aggiornare su BOOKING_CALLS / SLOTS
        # es: await delete_booking_or_slot(db, calendar_id, event_id)
        return

    if not start_raw or not end_raw:
        # all-day events o eventi inconsistenti
        return

    # Parse a datetime UTC
    start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00")).astimezone(timezone.utc)

    # FREE slot (transparent)
    if transparency == "transparent":
        # TODO: sincronizzare la rappresentazione dello slot libero
        # es: await upsert_free_slot(db, calendar_id, event_id, start_dt, end_dt)
        return

    # BUSY (evento prenotato)
    attendees = event.get("attendees") or []
    # TODO:
    # - estrarre coach_id/student_id dalle attendees o da event.extendedProperties
    # - aggiornare BOOKING_CALLS o eventuale stato prenotazione
    # es: await upsert_busy_booking(db, calendar_id, event_id, attendees, start_dt, end_dt)
    return
