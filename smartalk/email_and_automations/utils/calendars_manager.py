# calendar_manager.py

import json

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds

from smartalk.core.settings import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarManager:
    def __init__(self, user_email: str, calendar_id: str):
        self.user_email = user_email
        self.calendar_id = calendar_id

    def _creds(self):
        info = json.loads(settings.CALENDAR_SERVICE)
        return ServiceAccountCreds(scopes=SCOPES, **info, subject=self.user_email)

    async def _client(self):
        return Aiogoogle(service_account_creds=self._creds())

    # ---------------------------------------------------------
    # CREATE EVENT
    # ---------------------------------------------------------
    async def create_event(self, summary: str, start: str, end: str, attendees=None, transparency="opaque"):
        """
        Crea un evento generico:
        - summary = "FREE" o "BUSY"
        - transparency = "transparent" (FREE) o "opaque" (BUSY)
        """
        attendees = attendees or []

        async with await self._client() as ag:
            api = await ag.discover("calendar", "v3")

            body = {
                "summary": summary,
                "start": {"dateTime": start, "timeZone": "Europe/Rome"},
                "end": {"dateTime": end, "timeZone": "Europe/Rome"},
                "transparency": transparency,
            }

            if attendees:
                body["attendees"] = [{"email": a} for a in attendees]

            return await ag.as_service_account(api.events.insert(calendarId=self.calendar_id, json=body))

    async def create_free_slot(self, start: str, end: str):
        return await self.create_event(summary="FREE", start=start, end=end, transparency="transparent")

    # ---------------------------------------------------------
    # UPDATE EVENT (FREE → BUSY, aggiungere meet link, ecc.)
    # ---------------------------------------------------------
    async def update_event(self, event_id: str, **fields):
        async with await self._client() as ag:
            api = await ag.discover("calendar", "v3")
            return await ag.as_service_account(
                api.events.patch(calendarId=self.calendar_id, eventId=event_id, json=fields)
            )

    async def convert_free_to_busy(self, event_id: str, meet_link=None):
        update_payload = {
            "summary": "BUSY",
            "transparency": "opaque",
        }
        if meet_link:
            update_payload["location"] = meet_link

        return await self.update_event(event_id, **update_payload)

    # ---------------------------------------------------------
    # DELETE EVENT
    # ---------------------------------------------------------
    async def delete_event(self, event_id: str):
        async with await self._client() as ag:
            api = await ag.discover("calendar", "v3")
            return await ag.as_service_account(api.events.delete(calendarId=self.calendar_id, eventId=event_id))

    # ---------------------------------------------------------
    # LIST EVENTS
    # ---------------------------------------------------------
    async def list_events(self):
        async with await self._client() as ag:
            api = await ag.discover("calendar", "v3")
            resp = await ag.as_service_account(api.events.list(calendarId=self.calendar_id))
            return resp.get("items", [])

    async def list_free_slots(self):
        events = await self.list_events()
        return [e for e in events if e.get("summary") == "FREE"]

    # ---------------------------------------------------------
    # READ ATTENDEES
    # ---------------------------------------------------------
    async def get_event_attendees(self, event_id: str):
        async with await self._client() as ag:
            api = await ag.discover("calendar", "v3")
            event = await ag.as_service_account(api.events.get(calendarId=self.calendar_id, eventId=event_id))
            return event.get("attendees", [])
