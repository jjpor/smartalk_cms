# smartalk/routes/coach.py

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from smartalk.core.dynamodb import get_dynamodb_connection, get_table
from smartalk.core.settings import settings
from smartalk.db_usage import dynamodb_coach
from smartalk.routes.auth import create_token_response, get_current_user

router = APIRouter(tags=["Coach Dashboard"], prefix="/api/coach")

# Uso della Dependency Injection per ottenere la connessione resiliente
DBDependency = Depends(get_dynamodb_connection)


def to_decimal(value):
    """Converte float/int in Decimal per DynamoDB."""
    try:
        if value is None:
            return Decimal(0)
        return Decimal(str(value))
    except Exception:
        return Decimal(0)


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
    """Replica doGet(action='getStudentContracts') versione individuale"""

    params = dict(request.query_params)
    student_contracts = await dynamodb_coach.get_student_contracts_for_individual(
        params["studentId"], coach["role"], DBDependency
    )

    return create_token_response({"contracts": student_contracts}, coach)


@router.get("/getStudentContractsForGroup")
async def get_student_contracts_for_group_endpoint(
    coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getStudentContracts') versione di gruppo"""

    grouped_contracts = await dynamodb_coach.get_student_contracts_for_group(DBDependency)

    return create_token_response({"contracts": grouped_contracts}, coach)


@router.get("/getStudentsAndContractsByClientAndProduct")
async def get_students_by_client_and_product_endpoint(
    request: Request, coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Fornisce una lista di studenti attivi che hanno un contratto legato ad un determinato cliente e prodotto"""

    params = dict(request.query_params)
    students = await dynamodb_coach.get_students_and_contracts_by_client_and_product(
        params["clientId"], params["productId"], DBDependency
    )
    participants = await dynamodb_coach.get_participants(params["productId"], DBDependency)
    assert participants <= len(students)

    return create_token_response({"students": students, "participants": participants}, coach)


@router.get("/getMonthlyEarnings")
async def get_earnings_endpoint(
    coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getMonthlyEarnings')."""

    coach_id = coach.get("id")
    earnings = await dynamodb_coach.get_monthly_earnings(coach_id, DBDependency)

    return create_token_response({"earnings": earnings}, coach)


@router.get("/getCallHistory")
async def get_call_history_endpoint(
    coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doGet(action='getCallHistory')."""

    coach_id = coach.get("id")
    history = await dynamodb_coach.get_calls_by_coach(coach_id, DBDependency)

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

    calls = await dynamodb_coach.get_calls_by_student(params.get("studentId"), DBDependency)
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


@router.post("/logCallForIndividual")
async def log_call_for_individual_endpoint(
    data: Dict[str, Any], coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doPost(action='logCall') versione individuale."""

    contract_id = data["contract_id"]
    student_id = data["student_id"]
    call_date = datetime.fromisoformat(data["callDate"]).date().isoformat()

    contract_table = await get_table(DBDependency, settings.CONTRACTS_TABLE)
    product_table = await get_table(DBDependency, settings.PRODUCTS_TABLE)
    contract_response = contract_table.get_item(Key={"contract_id": contract_id})
    contract = contract_response["Item"]
    product_response = product_table.get_item(Key={"product_id": contract.get("product_id")})
    product = product_response["Item"]

    standard_duration = product["duration"]
    effective_duration = data.get("callDuration", standard_duration)
    units = to_decimal(effective_duration / standard_duration)
    standard_rate = to_decimal(product[f"{coach['role'].split(' ')[0].lower()}_coach_rate"])
    coach_rate = to_decimal(standard_rate * units)
    head_rate = to_decimal(product["head_coach_rate"])
    prod_cost = to_decimal(head_rate * units)
    attendance = data.get("attendance", True)
    notes = data.get("notes", "")

    # PK: contract_id, SK: session_id (coach_id#student_id#ISO_DATE)
    session_id = f"{coach['id']}#{student_id}#{call_date}"

    call = {
        "contract_id": contract_id,
        "session_id": session_id,
        "coach_id": coach["id"],
        "student_id": student_id,
        "product_id": product["product_id"],
        "date": call_date,
        "coach_rate": coach_rate,
        "prod_cost": prod_cost,
        "attendance": attendance,
        "duration": effective_duration,
        "units": units,
        "notes": notes,
    }

    result = await dynamodb_coach.log_call_to_db(
        [
            {
                "call": call,
                "contract": contract,
            }
        ],
        DBDependency,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response({"message": result.get("message", "Chiamata registrata!")}, coach)


@router.post("/logCallForGroup")
async def log_call_for_group_endpoint(
    data: Dict[str, Any], coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    """Replica doPost(action='logCall') versione di gruppo."""

    # TODO: far evolvere log_call_to_db in log_call_to_db con data_list, in cui per individuale è [{"call": call, "contract": contract}]
    # check a priori globale e poi esegui una transazione per studente (di solito 5–7 item ciascuna)
    group = data["group"]
    client_id = data["client_id"]
    product_id = data["product_id"]
    call_date = datetime.fromisoformat(data["callDate"]).date().isoformat()

    contract_table = await get_table(DBDependency, settings.CONTRACTS_TABLE)
    product_table = await get_table(DBDependency, settings.PRODUCTS_TABLE)

    product_response = product_table.get_item(Key={"product_id": product_id})
    product = product_response["Item"]

    assert product["participants"] == len(group), (
        f"Product {product['product_id']} has a different number of participants"
    )

    standard_duration = product["duration"]
    effective_duration = data.get("callDuration", standard_duration)
    units = to_decimal(effective_duration / standard_duration)
    standard_rate = to_decimal(product[f"{coach['role'].split(' ')[0].lower()}_coach_rate"])
    splitted_unit_cost_per_student = units / product["participants"]
    coach_rate = to_decimal(standard_rate * splitted_unit_cost_per_student)
    head_rate = to_decimal(product["head_coach_rate"])
    prod_cost = to_decimal(head_rate * splitted_unit_cost_per_student)

    group_call = []
    students_already_in_group = []

    for participant in group:
        contract_id = participant["contract_id"]
        student_id = participant["student_id"]

        # check no student repetitions
        assert student_id not in students_already_in_group, f"{student_id} duplicated"
        students_already_in_group.append(student_id)

        # check right contract for student, client, product
        contract_response = contract_table.get_item(Key={"contract_id": contract_id})
        contract = contract_response["Item"]
        assert contract["student_id"] == student_id, f"{student_id} has a different contract"
        assert contract["product_id"] == product_id, f"{student_id} has a different product"
        assert contract["client_id"] == client_id, f"{student_id} is under a different client"

        attendance = participant.get("attendance", True)
        notes = participant.get("notes", "")

        # PK: contract_id, SK: session_id (coach_id#student_id#ISO_DATE)
        session_id = f"{coach['id']}#{student_id}#{call_date}"

        call = {
            "contract_id": contract_id,
            "session_id": session_id,
            "coach_id": coach["id"],
            "student_id": student_id,
            "product_id": product_id,
            "date": call_date,
            "coach_rate": coach_rate,
            "prod_cost": prod_cost,
            "attendance": attendance,
            "duration": effective_duration,
            "units": units,
            "notes": notes,
        }
        group_call.append(
            {
                "call": call,
                "contract": contract,
            }
        )

    result = await dynamodb_coach.log_call_to_db(
        group_call,
        DBDependency,
    )

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
