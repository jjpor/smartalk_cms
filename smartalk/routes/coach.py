# smartalk/routes/coach.py

from typing import Any, Dict, List, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from smartalk.core.dynamodb import get_dynamodb_connection
from smartalk.db_usage import dynamodb_coach
from smartalk.routes.auth import create_jwt_token, create_token_response, get_current_user

router = APIRouter(tags=["Coach Dashboard"], prefix="/api/coach")

# Uso della Dependency Injection per ottenere la connessione resiliente
DBDependency = Depends(get_dynamodb_connection)


# ====================================================================
# VALIDAZIONE TIPO UTENTE (Dependency)
# ====================================================================
async def validate_coach_access(user: Dict[str, Any] | None = Depends(get_current_user)) -> Dict[str, Any]:
    """Verifica che l'utente loggato sia di tipo 'coach' e restituisce l'oggetto utente completo."""
    if user.get("user_type") != "coach":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso riservato ai coach")
    return user


# ====================================================================
# GET ENDPOINTS
# ====================================================================


@router.get("/check_coach")
async def check_coach(coach: Dict[str, Any] = Depends(validate_coach_access)) -> JSONResponse:
    """Verifica di un utente autenticato (dopo il caricamento di una pagina della dashboard)"""
    return create_token_response({"name": coach["name"]}, coach)


@router.get("/getStudents")
async def get_students_endpoint(
    coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getStudents')."""
    DBDependency = cast(DynamoDBServiceResource, DBDependency)

    students_data = await dynamodb_coach.get_active_students(DBDependency)

    return create_token_response({"students": students_data}, coach)


@router.get("/getStudentContractsForIndividual")
async def get_student_contracts_for_individual_endpoint(
    request: Request, coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getStudentContracts')."""

    params = dict(request.query_params)
    student_contracts = await dynamodb_coach.get_student_contracts_for_individual(
        params.get("studentId"), coach["role"], DBDependency
    )

    return create_token_response({"contracts": student_contracts}, coach)


@router.get("/getMonthlyEarnings")
async def get_earnings_endpoint(
    coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getMonthlyEarnings')."""

    coach_id = coach.get("id")
    earnings = dynamodb_coach.get_monthly_earnings(coach_id, DBDependency)

    return create_token_response({"earnings": earnings}, coach)


@router.get("/getCallHistory")
async def get_call_history_endpoint(
    coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getCallHistory')."""

    coach_id = coach.get("id")
    history = dynamodb_coach.get_calls_by_coach(coach_id, DBDependency)

    return create_token_response({"history": history}, coach)


@router.get("/getStudentInfo")
async def get_student_info_endpoint(
    request: Request, coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getStudentInfo')."""

    params = dict(request.query_params)
    student_info = await dynamodb_coach.get_student_info(params.get("studentId"), DBDependency)
    if not student_info:
        raise HTTPException(status_code=404, detail="Student not found")

    calls = dynamodb_coach.get_calls_by_student(params.get("studentId"), DBDependency)
    student_info["calls"] = calls
    return create_token_response({"studentInfo": student_info}, coach)


@router.get("/getStudentContracts")
async def get_student_contracts_endpoint(
    request: Request, coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getStudentContracts')."""

    params = dict(request.query_params)
    student_contracts = await dynamodb_coach.get_student_contracts(params.get("studentId"), DBDependency)

    return create_token_response({"contracts": student_contracts}, coach)


@router.get("/getReportCardTasks")
async def get_report_card_tasks_endpoint(
    coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getReportCardTasks')."""
    tasks = dynamodb_coach.get_report_card_tasks_db(coach, DBDependency)

    return create_token_response(tasks, coach)


# @router.get("/getFlashcards")
# async def get_flashcards_endpoint(
#     studentId: str = Query(..., description="ID dello studente"),
#     coach: Dict[str, Any] = Depends(validate_coach_access),
#     db_flashcards: Any = DBFlashcards # FLASHCARDS TABLE
# ) -> JSONResponse:
#     """Replica doGet(action='getFlashcards')."""

#     cards = dynamodb_coach.get_flashcards(db_flashcards, studentId) # Passo db_flashcards

#     return create_token_response({"cards": cards}, coach)

# @router.get("/getLessonPlanContent")
# async def get_lesson_plan_content_endpoint(
#     studentId: str = Query(..., description="ID dello studente"),
#     coach: Dict[str, Any] = Depends(validate_coach_access),
#     db_users: Any = DBUsers # USERS TABLE
# ) -> JSONResponse:
#     """Replica doGet(action='getLessonPlanContent')."""

#     content = dynamodb_coach.get_lesson_plan_content_db(db_users, studentId) # Passo db_users
#     if not content:
#         raise HTTPException(status_code=404, detail="Lesson Plan not found")
#     return create_token_response({"content": content}, coach)

# # ====================================================================
# # POST ENDPOINTS
# # ====================================================================


@router.post("/logCall")
async def log_call_endpoint(
    data: Dict[str, Any], coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doPost(action='logCall')."""

    result = dynamodb_coach.log_call_to_db(data, coach, DBDependency)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response({"message": result.get("message", "Chiamata registrata!")}, coach)


# @router.post("/saveDebrief")
# async def save_debrief_endpoint(
#     data: Dict[str, Any],
#     coach: Dict[str, Any] = Depends(validate_coach_access),
#     db_debriefs: Any = DBDebriefs # DEBRIEFS TABLE
# ) -> JSONResponse:
#     """Replica doPost(action='saveDebrief')."""

#     data["coachId"] = coach.get("id")

#     result = dynamodb_coach.handle_debrief_submission_db(db_debriefs, data) # Passo db_debriefs

#     if not result.get("success"):
#         raise HTTPException(status_code=400, detail=result.get("error"))

#     return create_token_response(result, coach)


# @router.post("/submitReportCard")
# async def submit_report_card_endpoint(
#     data: Dict[str, Any],
#     coach: Dict[str, Any] = Depends(validate_coach_access),
#     db_reports: Any = DBReportCards # REPORT_CARDS TABLE
# ) -> JSONResponse:
#     """Replica doPost(action='submitReportCard')."""

#     data["coachId"] = coach.get("id")

#     result = dynamodb_coach.handle_report_card_submission(db_reports, data) # Passo db_reports

#     if not result.get("success"):
#         raise HTTPException(status_code=400, detail=result.get("error"))

#     return create_token_response(result, coach)


# @router.post("/updateFlashcardStatus")
# async def update_flashcard_status_endpoint(
#     data: Dict[str, Any],
#     coach: Dict[str, Any] = Depends(validate_coach_access),
#     db_flashcards: Any = DBFlashcards # FLASHCARDS TABLE
# ) -> JSONResponse:
#     """Replica doPost(action='updateFlashcardStatus')."""

#     result = dynamodb_coach.update_flashcard_status(db_flashcards, data) # Passo db_flashcards

#     if not result.get("success"):
#         raise HTTPException(status_code=400, detail=result.get("error"))

#     return create_token_response(result, coach)

# @router.post("/saveLessonPlanContent")
# async def save_lesson_plan_content_endpoint(
#     data: Dict[str, Any],
#     coach: Dict[str, Any] = Depends(validate_coach_access),
#     db_users: Any = DBUsers # USERS TABLE
# ) -> JSONResponse:
#     """Replica doPost(action='saveLessonPlanContent')."""

#     result = dynamodb_coach.save_lesson_plan_content_db(db_users, data.get('studentId'), data.get('content')) # Passo db_users

#     if not result.get("success"):
#         raise HTTPException(status_code=400, detail=result.get("error"))

#     return create_token_response(result, coach)
