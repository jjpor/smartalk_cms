import datetime
from decimal import Decimal
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from smartalk.core.dynamodb import get_dynamodb_connection, get_table
from smartalk.core.settings import settings
from smartalk.db_usage import dynamodb_student
from smartalk.email_and_automations.utils.calendars_manager import CalendarManager
from smartalk.routes.auth import create_token_response, get_current_user

router = APIRouter(prefix="/student", tags=["student"])

DBDependency = Depends(get_dynamodb_connection)


async def validate_student_access(user: Dict[str, Any] | None = Depends(get_current_user)) -> Dict[str, Any]:
    """Verifica che l'utente autenticato sia uno studente."""

    if not user or user.get("user_type") != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso riservato agli studenti")
    return user


@router.get("/coach_free_slots")
async def get_coach_free_slots(
    request: Request,
    student: Dict[str, Any] = Depends(validate_student_access),
    DBDependency: Any = DBDependency,
) -> JSONResponse:
    """Restituisce gli slot liberi del coach per la settimana richiesta."""

    params = dict(request.query_params)
    contract_id = params["contract_id"]
    coach_id = params["coach_id"]
    year = int(params["year"])
    week = int(params["week"])
    student_id = student["id"]

    if week < 1 or week > 53:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Settimana non valida")

    current_iso_year, current_iso_week, _ = datetime.datetime.now(datetime.timezone.utc).isocalendar()
    if (year, week) < (current_iso_year, current_iso_week):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Settimana già passata")

    try:
        week_start_date = datetime.date.fromisocalendar(year, week, 1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anno o settimana non validi")

    start_date = datetime.datetime.combine(week_start_date, datetime.time.min, tzinfo=datetime.timezone.utc)
    end_date = start_date + datetime.timedelta(days=7)

    free_slots = await dynamodb_student.get_free_coach_slots(
        coach_id, student_id, contract_id, start_date, end_date, DBDependency
    )

    return create_token_response({"slots": free_slots}, student)


@router.post("/book")
async def book_call_endpoint(
    request: Request,
    student: Dict[str, Any] = Depends(validate_student_access),
    DBDependency: Any = DBDependency,
):
    params = dict(request.query_params)
    coach_id = params["coach_id"]
    contract_id = params["contract_id"]
    start = params["start"]
    end = params["end"]

    await dynamodb_student.book_call(student, coach_id, contract_id, start, end, DBDependency)
    return create_token_response({"message": "Slot prenotato"}, student)
