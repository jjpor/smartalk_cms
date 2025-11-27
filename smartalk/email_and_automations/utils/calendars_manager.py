# calendar_manager.py

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds
from fastapi import HTTPException

from smartalk.core.settings import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _parse_event_datetime(value: str) -> datetime:
    # Google Calendar può restituire date in vari formati ISO, ad esempio:
    # - "2025-03-01T12:30:00Z"           → Z = UTC
    # - "2025-03-01T12:30:00+01:00"      → offset specificato
    # - "2025-03-01"                     → eventi "all-day" senza orario
    #
    # La funzione normalizza tutto in un datetime timezone-aware in UTC.

    # 1) Sostituisce "Z" (che significa Zulu = UTC) con "+00:00"
    #    perché datetime.fromisoformat NON riconosce la lettera "Z",
    #    ma accetta invece offset numerici.
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

    # 2) Se l'orario NON ha informazione sul fuso (naive datetime),
    #    assume che sia in UTC (scelta ragionevole per dati provenienti da API).
    #    Questo evita errori e rende sempre il datetime timezone-aware.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # 3) Converte l’orario in UTC.
    #    Se era già UTC → non cambia nulla.
    #    Se aveva un offset (es. +01:00, -05:00) → viene convertito.
    return dt.astimezone(timezone.utc)


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

    async def book_call(self, start: str, end: str, product_name: str, product_unit_duration: int, student_email: str):
        # -------------------------
        # 1. Parsing start/end
        # -------------------------
        try:
            start_dt = _parse_event_datetime(start)
            end_dt = _parse_event_datetime(end)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid datetime format")

        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="Start must be < end")

        # -------------------------
        # 2. Verifica che il subslot sia libero e multiplo della product unit duration
        # -------------------------
        call_duration = int((end_dt - start_dt).total_seconds() // 60)
        if call_duration % product_unit_duration == 0:
            raise HTTPException(status_code=400, detail="Start must be < end")
        free_slots = await self.list_free_slots_by_period_and_duration(
            start_date=start_dt, end_date=end_dt, required_duration=call_duration
        )

        # Deve esserci uno slot che combacia
        slot_ok = any(
            s["start"] == start_dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
            and s["end"] == end_dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
            for s in free_slots
        )
        if not slot_ok:
            raise HTTPException(400, "Lo slot non è disponibile")

        # -------------------------
        # 3. Recupera l'evento FREE che contiene lo slot
        # -------------------------
        events = await self.list_events_in_range(start_dt, end_dt)
        container_event = None

        for e in events:
            if e.get("transparency") != "transparent":
                continue
            s_raw = e.get("start", {}).get("dateTime")
            e_raw = e.get("end", {}).get("dateTime")
            if not s_raw or not e_raw:
                continue

            evt_start = _parse_event_datetime(s_raw)
            evt_end = _parse_event_datetime(e_raw)

            # contiene?
            if evt_start <= start_dt and evt_end >= end_dt:
                container_event = (e, evt_start, evt_end)
                break

        if container_event is None:
            raise HTTPException(409, "Lo slot non è più disponibile")

        event_obj, evt_start, evt_end = container_event
        event_id = event_obj["id"]

        # -------------------------
        # 6. Cancella l'evento FREE originale
        # -------------------------
        await self.delete_event(event_id)

        # -------------------------
        # 7. Crea i 3 nuovi eventi
        # -------------------------

        # FREE PRIMA
        if evt_start < start_dt:
            await self.create_free_slot(start=evt_start.isoformat(), end=start_dt.isoformat())

        # EVENTO BUSY
        event_busy = await self.create_event(
            summary=f"Smartalk call - {product_name}",
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
            attendees=[
                {"email": self.user_email, "responseStatus": "accepted"},
                {"email": student_email, "responseStatus": "accepted"},
            ],
            transparency="opaque",
        )
        event_id = event_busy["id"]

        # FREE DOPO
        if end_dt < evt_end:
            await self.create_free_slot(start=end_dt.isoformat(), end=evt_end.isoformat())

        return int(call_duration / product_unit_duration), start_dt, end_dt, event_id

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
    async def list_events_in_range(self, start_date: datetime, end_date: datetime):
        async with await self._client() as ag:
            api = await ag.discover("calendar", "v3")

            resp = await ag.as_service_account(
                api.events.list(
                    calendarId=self.calendar_id,
                    timeMin=start_date.astimezone(timezone.utc).isoformat(),
                    timeMax=end_date.astimezone(timezone.utc).isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
            )

            return resp.get("items", [])

    async def list_free_slots_by_period_and_duration(
        self, start_date: datetime, end_date: datetime, required_duration: int
    ) -> List[Dict[str, str]]:
        """
        Ritorna tutti gli slot FREE compresi nel range richiesto:
        - recupera eventi con transparency == "transparent"
        - individua i sotto intervalli con
            - durata >= required_duration (minuti)
            - lo start deve essere esattamente alle :00 o :30
            - risultati in timestamp ISO UTC (Z)
        """

        events = await self.list_events(start_date, end_date)
        free_slots: List[Dict[str, str]] = []

        # durata richiesta come oggetto timedelta
        slot_delta = timedelta(minutes=required_duration)

        for event in events:
            # deve essere uno slot FREE
            if event.get("transparency") != "transparent":
                continue

            start_raw = event.get("start", {}).get("dateTime")
            end_raw = event.get("end", {}).get("dateTime")
            if not start_raw or not end_raw:
                continue

            try:
                start_dt = _parse_event_datetime(start_raw)
                end_dt = _parse_event_datetime(end_raw)
            except Exception:
                continue

            # il range deve essere completamente contenuto tra start_date e end_date
            if start_dt < start_date or end_dt > end_date:
                continue

            # durata minima richiesta
            duration_minutes = (end_dt - start_dt).total_seconds() / 60
            if duration_minutes < required_duration:
                continue

            # genera i sotto-intervalli all'interno dello slot FREE
            current = start_dt

            # allinea il primo slot alla prossima mezz’ora
            minute = current.minute
            if minute not in (0, 30):
                if minute < 30:
                    current = current.replace(minute=30, second=0, microsecond=0)
                else:
                    # minute > 30 → vai all'ora successiva
                    current = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

                # ora generiamo slot che iniziano a :00 o :30
                while True:
                    sub_start = current
                    sub_end = current + slot_delta

                    # se il sottoslot supera l'evento FREE → fine
                    if sub_end > end_dt:
                        break

                    # se il sottoslot è fuori dal range richiesto → salta
                    if sub_start < start_date or sub_end > end_date:
                        current += timedelta(minutes=30)
                        continue

                    # aggiungi sottoslot
                    free_slots.append(
                        {
                            "start": sub_start.astimezone(timezone.utc).isoformat(),
                            "end": sub_end.astimezone(timezone.utc).isoformat(),
                        }
                    )

                    # passo al prossimo inizio (:00 → :30 → +1 ora → :00 → ...)
                    current += timedelta(minutes=30)

        return free_slots

    # ---------------------------------------------------------
    # READ ATTENDEES
    # ---------------------------------------------------------
    async def get_event_attendees(self, event_id: str):
        async with await self._client() as ag:
            api = await ag.discover("calendar", "v3")
            event = await ag.as_service_account(api.events.get(calendarId=self.calendar_id, eventId=event_id))
            return event.get("attendees", [])
