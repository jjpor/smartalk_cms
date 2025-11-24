# calendar_setup.py

import asyncio
import json
import logging

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds

from smartalk.core.settings import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")
logger = logging.getLogger("Create Calendars")

SCOPES = ["https://www.googleapis.com/auth/calendar"]
BOOKING_CALENDAR_NAME = "Booking Calls"


def get_service_account_creds(user_email: str):
    """
    Crea credenziali impersonando l'utente.
    """
    info = json.loads(settings.CALENDAR_SERVICE)

    return ServiceAccountCreds(scopes=SCOPES, **info, subject=user_email)


# timezone personalizzata
USER_TIMEZONES = {
    "jj@smartalk.online": "Europe/Rome",
    "el@smartalk.online": "America/Mexico_City",
    "th@smartalk.online": "America/Sao_Paulo",
}


async def get_or_create_booking_calendar(user_email: str):
    creds = get_service_account_creds(user_email)

    async with Aiogoogle(service_account_creds=creds) as ag:
        api = await ag.discover("calendar", "v3")

        # 1) Lista calendari
        response_calendars = await ag.as_service_account(api.calendarList.list())

        for existing_calendar in response_calendars.get("items", []):
            logger.info(f"{user_email} -> {existing_calendar.get('summary')}")
            if existing_calendar.get("summary") == BOOKING_CALENDAR_NAME:
                logger.info(f"{user_email}: calendario {BOOKING_CALENDAR_NAME} già esistente")
                return existing_calendar["id"]

        # 2) Crea calendario
        new_calendar = {
            "summary": BOOKING_CALENDAR_NAME,
            "timeZone": USER_TIMEZONES[user_email],
        }

        created = await ag.as_service_account(api.calendars.insert(json=new_calendar))
        logger.info(f"{user_email}: calendario {BOOKING_CALENDAR_NAME} creato")

        calendar_id = created["id"]

        # 3) Inserimento del calendario nella lista dei calendari utilizzabili dall'utente
        await ag.as_service_account(api.calendarList.insert(json={"id": calendar_id}))
        logger.info(
            f"{user_email}: calendario {BOOKING_CALENDAR_NAME} aggiunto nella lista dei calendari utilizzabili da {user_email}"
        )

        return calendar_id


async def setup_calendars():
    """
    Per ogni utente crea/recupera il calendario Booking Calls.
    """
    results = {}
    for user in list(USER_TIMEZONES.keys()):
        try:
            calendar_id = await get_or_create_booking_calendar(user)
            results[user] = calendar_id
        except Exception as e:
            results[user] = f"Errore: {e}"
    return results


results = asyncio.run(setup_calendars())
logger.info(results)
