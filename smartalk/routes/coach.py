# smartalk/routes/coach.py

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from smartalk.core.dynamodb import get_dynamodb_connection
from smartalk.core.settings import settings
from smartalk.db_usage import dynamodb_coach as db_ops
from smartalk.routes.auth import create_token_response, get_current_user

router = APIRouter(tags=["Coach Dashboard"], prefix="/api/coach")

# ====================================================================
# DEFINIZIONE DELLE DIPENDENZE DELLE TABELLE
# ====================================================================


def get_specific_table(table_name: str):
    """Factory che crea una dependency per iniettare una Tabella specifica."""

    async def _get_table_dependency():
        # Chiama la funzione di connessione con il nome della tabella desiderata
        return await get_dynamodb_connection(table_name)

    # L'oggetto restituito è una Dependency, non la Tabella stessa
    return Depends(_get_table_dependency)


# Dependency Factory: Usiamo i nomi delle tabelle da settings
DBUsers = get_specific_table(settings.USERS_TABLE)
DBTracker = get_specific_table(settings.TRACKER_TABLE)
DBReportCards = get_specific_table(settings.REPORT_CARDS_TABLE)
DBDebriefs = get_specific_table(settings.DEBRIEFS_TABLE)
# Flashcards: assumiamo che il nome sia qui


# ====================================================================
# VALIDAZIONE TIPO UTENTE (Dependency)
# ====================================================================
async def validate_coach_access(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Verifica che l'utente loggato sia di tipo 'coach' e restituisce l'oggetto utente completo."""
    if user.get("user_type") != "coach":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso riservato ai coach")
    return user


# ====================================================================
# GET ENDPOINTS
# ====================================================================


@router.get("/getStudents")
async def get_students_endpoint(
    user_data: Dict[str, Any] = Depends(validate_coach_access),
    db_users: Any = DBUsers,  # USERS TABLE
) -> JSONResponse:
    """Replica doGet(action='getStudents')."""

    coach_id = user_data.get("id")
    students_data = db_ops.get_active_students(db_users, coach_id)  # Passo db_users

    return create_token_response({"students": students_data}, user_data)


@router.get("/getMonthlyEarnings")
async def get_earnings_endpoint(
    user_data: Dict[str, Any] = Depends(validate_coach_access),
    db_tracker: Any = DBTracker,  # TRACKER TABLE
) -> JSONResponse:
    """Replica doGet(action='getMonthlyEarnings' e 'getCallHistory')."""

    coach_id = user_data.get("id")
    earnings = db_ops.get_monthly_earnings(db_tracker, coach_id)  # Passo db_tracker
    history = db_ops.get_call_history(db_tracker, coach_id)  # Passo db_tracker

    return create_token_response({"earnings": earnings, "history": history}, user_data)


@router.get("/getStudentInfo")
async def get_student_info_endpoint(
    studentId: str = Query(..., description="ID dello studente"),
    user_data: Dict[str, Any] = Depends(validate_coach_access),
    db_users: Any = DBUsers,  # USERS TABLE
) -> JSONResponse:
    """Replica doGet(action='getStudentInfo')."""

    info = db_ops.get_student_info(db_users, studentId)  # Passo db_users
    if not info:
        raise HTTPException(status_code=404, detail="Student not found")

    return create_token_response({"studentInfo": info}, user_data)


@router.get("/getReportCardTasks")
async def get_report_card_tasks_endpoint(
    user_data: Dict[str, Any] = Depends(validate_coach_access),
    db_tracker: Any = DBTracker,  # TRACKER TABLE
) -> JSONResponse:
    """Replica doGet(action='getReportCardTasks')."""

    coach_id = user_data.get("id")
    tasks = db_ops.get_report_card_tasks_db(db_tracker, coach_id)  # Passo db_tracker

    return create_token_response(tasks, user_data)


@router.get("/getLessonPlanContent")
async def get_lesson_plan_content_endpoint(
    studentId: str = Query(..., description="ID dello studente"),
    user_data: Dict[str, Any] = Depends(validate_coach_access),
    db_users: Any = DBUsers,  # USERS TABLE
) -> JSONResponse:
    """Replica doGet(action='getLessonPlanContent')."""

    content = db_ops.get_lesson_plan_content_db(db_users, studentId)  # Passo db_users
    if not content:
        raise HTTPException(status_code=404, detail="Lesson Plan not found")
    return create_token_response({"content": content}, user_data)


# ====================================================================
# POST ENDPOINTS
# ====================================================================


@router.post("/logCall")
async def log_call_endpoint(
    data: Dict[str, Any],
    user_data: Dict[str, Any] = Depends(validate_coach_access),
    db_tracker: Any = DBTracker,  # TRACKER TABLE
) -> JSONResponse:
    """Replica doPost(action='logCall')."""

    data["coachId"] = user_data.get("id")
    data["role"] = user_data.get("role", "Senior Coach")

    result = db_ops.log_call_to_db(db_tracker, data)  # Passo db_tracker

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response({"message": result.get("message", "Chiamata registrata!")}, user_data)


@router.post("/saveDebrief")
async def save_debrief_endpoint(
    data: Dict[str, Any],
    user_data: Dict[str, Any] = Depends(validate_coach_access),
    db_debriefs: Any = DBDebriefs,  # DEBRIEFS TABLE
) -> JSONResponse:
    """Replica doPost(action='saveDebrief')."""

    data["coachId"] = user_data.get("id")

    result = db_ops.handle_debrief_submission_db(db_debriefs, data)  # Passo db_debriefs

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response(result, user_data)


@router.post("/submitReportCard")
async def submit_report_card_endpoint(
    data: Dict[str, Any],
    user_data: Dict[str, Any] = Depends(validate_coach_access),
    db_reports: Any = DBReportCards,  # REPORT_CARDS TABLE
) -> JSONResponse:
    """Replica doPost(action='submitReportCard')."""

    data["coachId"] = user_data.get("id")

    result = db_ops.handle_report_card_submission(db_reports, data)  # Passo db_reports

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response(result, user_data)


@router.post("/saveLessonPlanContent")
async def save_lesson_plan_content_endpoint(
    data: Dict[str, Any],
    user_data: Dict[str, Any] = Depends(validate_coach_access),
    db_users: Any = DBUsers,  # USERS TABLE
) -> JSONResponse:
    """Replica doPost(action='saveLessonPlanContent')."""

    result = db_ops.save_lesson_plan_content_db(db_users, data.get("studentId"), data.get("content"))  # Passo db_users

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response(result, user_data)
