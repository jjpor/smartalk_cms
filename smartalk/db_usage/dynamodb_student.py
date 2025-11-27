# smartalk/db_usage/dynamodb_coach.py

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
from typing import Any, Dict, List, Optional

import pandas as pd
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from dateutil import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from smartalk.core.dynamodb import (
    delete_item,
    get_item,
    get_table,
    get_today_string,
    make_atomic_transaction,
    to_dynamodb_item,
    to_low_level_item,
)
from smartalk.core.settings import settings
from smartalk.email_and_automations.utils.calendars_manager import CalendarManager

logger = logging.getLogger(__name__)


# Funzioni per recuperare gli slot liberi del coach
async def get_free_coach_slots(
    coach_id: str,
    student_id: str,
    contract_id: str,
    start_date: datetime,
    end_date: datetime,
    db: DynamoDBServiceResource,
) -> List[dict]:
    """Recupera gli gli slot liberi di un coach rispetto al prodotto del contratto attivo dello studente."""
    try:
        # validate contract
        contract = await get_item(db, settings.CONTRACTS_TABLE, {"contract_id": contract_id})
        if not contract:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contratto non trovato")

        if contract.get("student_id") != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Contratto non accessibile")

        status_value = str(contract.get("status", "")).lower()
        if status_value != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contratto non attivo")

        if contract.get("left_calls", 0) <= 0 and not contract.get("unlimited"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nessuna chiamata residua")

        # get duration from product
        product = await get_item(db, settings.PRODUCTS_TABLE, {"product": contract.get("product_id")})

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prodotto non trovato")

        required_duration = product.get("duration")
        if not isinstance(required_duration, (int, float, Decimal)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Durata prodotto non valida")

        required_duration = int(required_duration)

        # get coach calendar
        coach = await get_item(db, settings.USERS_TABLE, {"id": coach_id})

        if not coach:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach non trovato")

        calendar_id = coach.get("calendar_id")
        coach_email = coach.get("email")
        if not calendar_id or not coach_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Calendario coach non configurato")

        calendar_manager = CalendarManager(user_email=coach_email, calendar_id=calendar_id)
        return await calendar_manager.list_free_slots_by_period_and_duration(start_date, end_date, required_duration)
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_active_students (USERS table): {e}")
        return []


async def book_call(
    student: dict,
    coach_id: str,
    contract_id: str,
    start: str,
    end: str,
    db: DynamoDBServiceResource,
) -> None:
    """
    Prenota uno slot:
    - valida studente/contratto
    - verifica disponibilità subslot
    - trasforma lo slot che lo contiene in 3 eventi (free, busy, free)
    - salva prenotazione su DynamoDB BOOKING_CALLS
    """

    # -------------------------
    # 2. Recupera contratto e prodotto
    # -------------------------
    student_id = student["id"]
    contract = await get_item(db, settings.CONTRACTS_TABLE, {"contract_id": contract_id})
    if not contract or contract.get("student_id") != student_id:
        raise HTTPException(403, "Contratto non accessibile o inesistente")

    if str(contract.get("status", "")).lower() != "active":
        raise HTTPException(400, "Contratto non attivo")

    if contract.get("left_calls", 0) <= 0 and not contract.get("unlimited"):
        raise HTTPException(400, "Nessuna chiamata residua")

    product = await get_item(db, settings.PRODUCTS_TABLE, {"product": contract["product_id"]})
    if not product:
        raise HTTPException(404, "Prodotto non trovato")

    product_unit_duration = int(product["duration"])
    product_name = product.get("name", "Smartalk call")

    # -------------------------
    # 3. Recupera coach e calendario
    # -------------------------
    coach = await get_item(db, settings.USERS_TABLE, {"id": coach_id})
    if not coach:
        raise HTTPException(404, "Coach non trovato")

    calendar_id = coach.get("calendar_id")
    coach_email = coach.get("email")

    if not calendar_id or not coach_email:
        raise HTTPException(400, "Calendario coach non configurato")

    calendar = CalendarManager(user_email=coach_email, calendar_id=calendar_id)
    units, start_dt, end_dt, event_id = await calendar.book_call(
        start, end, product_name, product_unit_duration, student["email"]
    )

    # -------------------------
    # 8. Salva prenotazione su DynamoDB
    # -------------------------
    booking_item = {
        "attendees": f"{coach_id}#{student_id}",  # PK
        "start": start_dt.isoformat(),  # SK
        "coach_id": coach_id,
        "student_id": student_id,
        "contract_id": contract_id,
        "end": end_dt.isoformat(),
        "status": "cancelable",
        "units": units,
        "event_id": event_id,
    }

    booking_calls_table = await get_table(db, settings.BOOKING_CALLS_TABLE)
    await booking_calls_table.put_item(
        Item=to_dynamodb_item(booking_item),
        ConditionExpression=Attr("attendees").not_exists() & Attr("start").not_exists(),
    )
