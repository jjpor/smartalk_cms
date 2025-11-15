# smartalk/routes/coach.py

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, cast

import pandas as pd
from dateutil import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from smartalk.core.dynamodb import get_dynamodb_connection, get_table
from smartalk.core.settings import settings
from smartalk.db_usage import dynamodb_coach
from smartalk.db_usage.dynamodb_auth import hash_password
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


async def validate_head_coach_access(user: Dict[str, Any] | None = Depends(get_current_user)) -> Dict[str, Any]:
    """Verifica che l'utente loggato sia di tipo 'coach' e che sia con role "Head Coach". Restituisce l'oggetto utente completo."""
    if user.get("user_type") != "coach" or user.get("role") != "Head Coach":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accesso riservato a Head Coach")
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
    tasks = await dynamodb_coach.get_report_card_tasks_db(coach, DBDependency)

    return create_token_response(tasks, coach)


@router.get("/edit_company")
async def edit_company_endpoint(
    request: Request, head_coach: Dict[str, Any] = Depends(validate_head_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    params = dict(request.query_params)
    company, students = await dynamodb_coach.get_company_and_its_students(params["company_id"], DBDependency)
    company["students"] = students
    return create_token_response({"company": company}, head_coach)


@router.get("/get_clients")
async def get_clients(
    head_coach: Dict[str, Any] = Depends(validate_head_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    clients = await dynamodb_coach.get_students_and_company_list(DBDependency)
    return create_token_response({"clients": clients}, head_coach)


@router.get("/get_employee_students")
async def get_employee_students(
    request: Request, head_coach: Dict[str, Any] = Depends(validate_head_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    params = dict(request.query_params)
    students = await dynamodb_coach.get_employee_students_by_company(params["company_id"], DBDependency)
    return create_token_response({"students": students}, head_coach)


@router.get("/get_client_invoices")
async def get_client_invoices(
    request: Request, head_coach: Dict[str, Any] = Depends(validate_head_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    params = dict(request.query_params)
    invoices = await dynamodb_coach.get_invoices_by_client(params["client_id"], DBDependency)
    return create_token_response({"invoices": invoices}, head_coach)


# lista call fatte coinvolte nel report card
@router.get("/get_calls_for_report_card")
async def get_calls_for_report_card(
    request: Request, coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    params = dict(request.query_params)
    calls = await dynamodb_coach.get_calls_by_report_card(
        params["report_card_id"], params["start_month"], coach["id"], DBDependency
    )
    return create_token_response({"calls": calls}, coach)


@router.get("get_debrief")
async def get_debrief(
    request: Request, coach: Dict[str, Any] = Depends(validate_coach_access), DBDependency: Any = DBDependency
) -> JSONResponse:
    params = dict(request.query_params)
    student_id = params["student_id"]
    coach_id = params["coach_id"]
    date = params["date"]
    assert coach["id"] == coach_id, "Coach not authorized"
    debrief = await dynamodb_coach.get_item(
        DBDependency, settings.DEBRIEFS_TABLE, {"debrief_id": f"{student_id}#{coach_id}", "date": date}
    )
    return create_token_response({"debrief": debrief}, coach)


# @router.get("/getFlashcards")
# async def get_flashcards_endpoint(
#     studentId: str = Query(..., description="ID dello studente"),
#     coach: Dict[str, Any] = Depends(validate_coach_access),
#     db_flashcards: Any = DBFlashcards # FLASHCARDS TABLE
# ) -> JSONResponse:
#     """Replica doGet(action='getFlashcards')."""

#     cards = await dynamodb_coach.get_flashcards(db_flashcards, studentId) # Passo db_flashcards

#     return create_token_response({"cards": cards}, coach)

# @router.get("/getLessonPlanContent")
# async def get_lesson_plan_content_endpoint(
#     studentId: str = Query(..., description="ID dello studente"),
#     coach: Dict[str, Any] = Depends(validate_coach_access),
#     db_users: Any = DBUsers # USERS TABLE
# ) -> JSONResponse:
#     """Replica doGet(action='getLessonPlanContent')."""

#     content = await dynamodb_coach.get_lesson_plan_content_db(db_users, studentId) # Passo db_users
#     if not content:
#         raise HTTPException(status_code=404, detail="Lesson Plan not found")
#     return create_token_response({"content": content}, coach)

# # ====================================================================
# # POST ENDPOINTS
# # ====================================================================


@router.post("/create_company")
async def create_company(
    data: Dict[str, Any],
    head_coach: Dict[str, Any] = Depends(validate_head_coach_access),
    DBDependency: Any = DBDependency,
) -> JSONResponse:
    """New Company"""

    company = {
        "id": data["id"],
        "name": data["name"],
        "user_type": "company",
        "password_hash": hash_password(str(data["password"])),
    }
    result = await dynamodb_coach.insert_new_company(company, DBDependency)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response({}, head_coach)


@router.post("/add_employee")
async def add_employee(
    data: Dict[str, Any],
    head_coach: Dict[str, Any] = Depends(validate_head_coach_access),
    DBDependency: Any = DBDependency,
) -> JSONResponse:
    """Add an employee student to a company"""
    result = await dynamodb_coach.insert_new_company_employee(data["company_id"], data["student_id"], DBDependency)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response({}, head_coach)


@router.post("/remove_employee")
async def remove_employee(
    data: Dict[str, Any],
    head_coach: Dict[str, Any] = Depends(validate_head_coach_access),
    DBDependency: Any = DBDependency,
) -> JSONResponse:
    """Remove an employee student from a company"""
    result = await dynamodb_coach.delete_item(
        DBDependency,
        settings.COMPANY_EMPLOYEES_TABLE,
        {"company_id": data["company_id"], "student_id": data["student_id"]},
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response({}, head_coach)


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


@router.post("/newContract")
async def new_contract_endpoint(
    data: Dict[str, Any],
    head_coach: Dict[str, Any] = Depends(validate_head_coach_access),
    DBDependency: Any = DBDependency,
) -> JSONResponse:
    contract = {
        "contract_id": data["contract_id"],
        "student_id": data["student_id"],
        "product_id": data["product_id"],
        "status": "Active",
        "unlimited": data["unlimited"],
        "invoice_id": data["invoice_id"],
        "client_id": data["client_id"],
    }

    has_report_card_context = False

    if "report_card_cadency" in data and "report_card_start_month" in data and "report_card_email_recipients" in data:
        contract = {
            **contract,
            **{
                "report_card_cadency": data["report_card_cadency"],
                "report_card_start_month": data["report_card_start_month"],
                "report_card_email_recipients": data["report_card_email_recipients"],
                "report_card_generator_id": f"{contract['student_id']}#{contract['client_id']}#{contract['report_card_cadency']}",
            },
        }
        has_report_card_context = True

    if not contract["unlimited"]:
        products_table = await get_table(DBDependency, settings.PRODUCTS_TABLE)
        product_response = await products_table.get_item(Key={"product_id": contract["product_id"]})
        product = product_response.get("Item")
        if "package" in data:
            contract["total_calls"] = product["package"]
        else:
            contract["total_calls"] = data["total_calls"]

        contract["calls_per_week"] = int(60 / product["duration"])
        contract["used_calls"] = 0
        contract["left_calls"] = contract["total_calls"]

    report_card_generator = {}

    if has_report_card_context:
        # check se esiste report card generator che ha report_card_generator_id, devono avere stessa report_card_email_recipients e report_card_start_month allineati
        report_card_generators_table = await get_table(DBDependency, settings.REPORT_CARD_GENERATORS_TABLE)
        report_card_generator_response = await report_card_generators_table.get_item(
            Key={"report_card_generator_id": contract["report_card_generator_id"]}
        )
        report_card_generator = report_card_generator_response.get("Item", {})
        if report_card_generator:
            assert report_card_generator["report_card_email_recipients"] == contract["report_card_email_recipients"], (
                "This contract has different report_card_email_recipients"
            )
            start_month_aligned = contract["report_card_start_month"] == report_card_generator["current_start_month"]
            if not start_month_aligned:
                min_multiple = 0
                max_multiple = 0
                if contract["report_card_start_month"] < report_card_generator["current_start_month"]:
                    min_multiple = -12
                if contract["report_card_start_month"] > report_card_generator["current_start_month"]:
                    max_multiple = 13
                starting_aligning_date = datetime.fromisoformat(
                    report_card_generator["current_start_month"] + "-01"
                ).date()
                for i in range(min_multiple, max_multiple):
                    align_to_test = (
                        starting_aligning_date + relativedelta(months=(i * contract["report_card_cadency"]))
                    ).strftime("%Y-%m")
                    if contract["report_card_start_month"] == align_to_test:
                        start_month_aligned = True
                        break

            assert start_month_aligned, (
                "report_card_start_month not aligned with report_card_cadency and other contracts"
            )

    result = await dynamodb_coach.create_contract(
        contract,
        has_report_card_context,
        report_card_generator,
        DBDependency,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response({"message": result.get("message", "Contratto registrato!")}, head_coach)


@router.post("/save_report_card_draft")
async def save_report_card_draft(
    data: Dict[str, Any],
    coach: Dict[str, Any] = Depends(validate_coach_access),
    DBDependency: Any = DBDependency,
) -> JSONResponse:
    result = await dynamodb_coach.update_report_card_draft(data, coach["id"], DBDependency)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response(result, coach)


@router.post("/report_card_completed")
async def report_card_completed(
    data: Dict[str, Any],
    coach: Dict[str, Any] = Depends(validate_coach_access),
    DBDependency: Any = DBDependency,
) -> JSONResponse:
    result = await dynamodb_coach.update_report_card_to_completed(data, coach["id"], DBDependency)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response(result, coach)


# from completed to no_show or draft
@router.post("/restore_report_card_status")
async def restore_report_card_status(
    data: Dict[str, Any],
    head_coach: Dict[str, Any] = Depends(validate_head_coach_access),
    DBDependency: Any = DBDependency,
) -> JSONResponse:
    result = await dynamodb_coach.restore_report_card_from_completed(data, DBDependency)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return create_token_response(result, head_coach)


# send all completed report cards
@router.post("/send_all_completed_report_cards")
async def send_all_completed_report_cards(
    head_coach: Dict[str, Any] = Depends(validate_head_coach_access),
    DBDependency: Any = DBDependency,
) -> JSONResponse:
    # validazione assenza report card scaduti in modalità no show o draft
    check = await dynamodb_coach.is_empty_no_show_or_draft_expired_report_cards(DBDependency)
    if not check.get("success"):
        raise HTTPException(status_code=400, detail=check.get("error"))

    # creazione report da inviare raggruppati per client
    completed_report_cards = await dynamodb_coach.get_completed_expired_report_cards(DBDependency)
    if not completed_report_cards:
        raise HTTPException(status_code=400, detail="Empty completed expired report cards")

    # invio report tramite email

    completed_report_cards_df = pd.DataFrame.from_dict(completed_report_cards)
    completed_report_cards_df = completed_report_cards_df[["report_card_generator_id", "report_card_id", "start_month"]]

    for report_card_generator_id in completed_report_cards_df["report_card_generator_id"].unique():
        # aggiornamento o eliminazione report card generator
        response = {}
        min_report_card_start_month = await dynamodb_coach.get_min_report_card_start_month_by_report_card_generator_id(
            report_card_generator_id, DBDependency
        )
        if min_report_card_start_month:
            # aggiornamento current_start_month e next_start_month, metto a sent gli attuali report card e creazione eventuale report card no_show
            response = await dynamodb_coach.update_report_card_and_generator(
                completed_report_cards_df[
                    completed_report_cards_df["report_card_generator_id"] == report_card_generator_id
                ].to_dict("records")[["report_card_id", "start_month"]],
                report_card_generator_id,
                min_report_card_start_month,
                DBDependency,
            )
        else:
            # elimino report card generator, metto a sent gli attuali report card
            response = await dynamodb_coach.update_report_card_and_delete_generator(
                completed_report_cards_df[
                    completed_report_cards_df["report_card_generator_id"] == report_card_generator_id
                ].to_dict("records")[["report_card_id", "start_month"]],
                report_card_generator_id,
                DBDependency,
            )

        if not response.get("success"):
            raise HTTPException(status_code=400, detail=check.get("error"))

    return create_token_response({}, head_coach)


# @router.post("/saveDebrief")
# async def save_debrief_endpoint(
#     data: Dict[str, Any],
#     coach: Dict[str, Any] = Depends(validate_coach_access),
#     db_debriefs: Any = DBDebriefs # DEBRIEFS TABLE
# ) -> JSONResponse:
#     """Replica doPost(action='saveDebrief')."""

#     data["coachId"] = coach.get("id")

#     result = await dynamodb_coach.handle_debrief_submission_db(db_debriefs, data) # Passo db_debriefs

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

#     result = await dynamodb_coach.update_flashcard_status(db_flashcards, data) # Passo db_flashcards

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

#     result = await dynamodb_coach.save_lesson_plan_content_db(db_users, data.get('studentId'), data.get('content')) # Passo db_users

#     if not result.get("success"):
#         raise HTTPException(status_code=400, detail=result.get("error"))

#     return create_token_response(result, coach)
