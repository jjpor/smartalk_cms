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
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from smartalk.core.dynamodb import get_table, make_atomic_transaction, to_low_level_item
from smartalk.core.settings import settings

logger = logging.getLogger(__name__)

# --- UTILITY ---


def generate_debrief_text_ai(payload: Dict[str, Any]) -> Dict[str, Any]:
    """STUB: Chiama Gemini/AI per la generazione di testo (Debrief)."""
    field = payload.get("fieldType", "goals")
    text = payload.get("currentText", "Nessun testo fornito")
    return {"success": True, "suggestion": f"[AI SUGGESTION per {field.upper()}]: Revisione basata su: '{text}'."}


# ====================================================================
# FUNZIONI PER LA DASHBOARD COACH (Ora richiedono 'db' - l'oggetto Table)
# ====================================================================


# Funzioni per Tabella USERS
async def get_active_students(db: DynamoDBServiceResource) -> List[str]:
    """Recupera gli ID degli studenti attivi (USERS Table)."""
    try:
        # HASH: user_type (index: user-type-index)
        table = await get_table(db, settings.USERS_TABLE)
        response = await table.query(
            IndexName="user-type-index",
            KeyConditionExpression=Key("user_type").eq("student"),
            FilterExpression=Attr("status").eq("active"),
            ProjectionExpression="#id",
            ExpressionAttributeNames={"#id": "id"},
        )
        return [item.get("id") for item in response.get("Items", [])]
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_active_students (USERS table): {e}")
        return []


async def get_client_name(client_id: str, db: DynamoDBServiceResource) -> str:
    """Recupera gli ID degli studenti attivi (USERS Table)."""
    # HASH: user_type (index: user-type-index)
    table = await get_table(db, settings.USERS_TABLE)
    response = await table.get_item(Key={"id": client_id})
    client = response["Item"]
    if client["user_type"] == "student":
        return f"{client['name']} {client['surname']}"
    if client["user_type"] == "company":
        return client["name"]


async def get_student_contracts_for_individual(
    student_id: str, coach_role: str, db: DynamoDBServiceResource
) -> List[Dict[str, Any]]:
    contracts_table = await get_table(db, settings.CONTRACTS_TABLE)
    contracts_response = await contracts_table.query(
        IndexName="student-id-status-index",
        KeyConditionExpression=Key("student_id").eq(student_id) & Key("status").eq("active"),
        FilterExpression=Attr("unlimited").eq(True)
        | Attr("max_end_date").not_exists()
        | Attr("max_end_date").gte(get_today_string()),
        ScanIndexForward=False,
        ProjectionExpression=", ".join(["product_id"]),
    )
    products_table = await get_table(db, settings.PRODUCTS_TABLE)

    contracts = []
    for item in contracts_response.get("Items", []):
        product_response = await products_table.get_item(Key={"product_id": item.get("product_id")})
        product = product_response["Item"]
        if product["participants"] == 1:
            client_name = await get_client_name(item["client_id"], db)
            contracts.append(
                {
                    "productName": product_response["Item"]["product_name"],
                    "duration": product_response["Item"]["duration"],
                    "clientName": client_name,
                    "contract_id": item["contract_id"],
                    "coach_rate": product[f"{coach_role.split(' ')[0].lower()}_coach_rate"],
                }
            )
    # validazione unicità
    assert max(pd.DataFrame.from_dict(contracts).groupby("contract_id").size()) == 1, (
        "Contract mapping for individual call not unique"
    )

    return contracts


async def get_student_contracts_for_group(db: DynamoDBServiceResource) -> List[Dict[str, Any]]:
    contracts_table = await get_table(db, settings.CONTRACTS_TABLE)
    contracts_response = await contracts_table.query(
        IndexName="status-index",
        KeyConditionExpression=Key("status").eq("Active"),
        FilterExpression=Attr("unlimited").eq(True)
        | Attr("max_end_date").not_exists()
        | Attr("max_end_date").gte(get_today_string()),
        ScanIndexForward=False,
        ProjectionExpression=", ".join(["product_id"]),
    )
    products_table = await get_table(db, settings.PRODUCTS_TABLE)

    contracts = []
    for item in contracts_response.get("Items", []):
        product_response = await products_table.get_item(Key={"product_id": item.get("product_id")})
        product = product_response["Item"]
        if product["participants"] > 1:
            client_name = await get_client_name(item["client_id"], db)
            contracts.append(
                {
                    "productName": product_response["Item"]["product_name"],
                    "product_id": item["product_id"],
                    "clientName": client_name,
                    "client_id": item["client_id"],
                    "student_id": item["student_id"],
                    "contract_id": item["contract_id"],
                }
            )

    # validazione unicità
    assert max(pd.DataFrame.from_dict(contracts).groupby(["client_id", "product_id", "student_id"]).size()) == 1, (
        "Grouped contract mapping for grouped call not unique"
    )

    # grouping
    grouped_contracts = (
        pd.DataFrame.from_dict(contracts)[["client_id", "product_id", "clientName", "productName"]]
        .drop_duplicates()
        .to_dict("records")
    )

    return grouped_contracts


async def get_students_and_contracts_by_client_and_product(
    client_id: str, product_id: str, db: DynamoDBServiceResource
) -> List[Dict[str, Any]]:
    contracts_table = await get_table(db, settings.CONTRACTS_TABLE)
    contracts_response = await contracts_table.query(
        IndexName="client-id-product-id-index",
        KeyConditionExpression=Key("client_id").eq(client_id) & Key("product_id").eq(product_id),
        FilterExpression=Attr("status").eq("active")
        & (
            Attr("unlimited").eq(True)
            | Attr("max_end_date").not_exists()
            | Attr("max_end_date").gte(get_today_string())
        ),
        ScanIndexForward=False,
        ProjectionExpression=", ".join(["student_id"]),
    )
    students_table = await get_table(db, settings.USERS_TABLE)

    students = []
    for item in contracts_response.get("Items", []):
        student_response = await students_table.get_item(Key={"id": item.get("student_id")})
        student = student_response["Item"]
        students.append(
            {
                "student_id": student["id"],
                "contract_id": item["contract_id"],
                "student_fullname": f"{student['name']} {student['surname']}",
            }
        )

    return students


async def get_participants(product_id: str, db: DynamoDBServiceResource) -> int:
    products_table = await get_table(db, settings.PRODUCTS_TABLE)
    product_response = await products_table.get_item(Key={"product_id": product_id})
    product = product_response["Item"]

    return product["participants"]


def create_student_response(student_info: dict) -> dict:
    student = {}
    student["Name"] = student_info.get("name", "")
    student["Surname"] = student_info.get("surname", "")
    student["Student ID"] = student_info.get("id", "")
    student["Email"] = student_info.get("email", "")
    student["Secondary Email"] = student_info.get("secondary_email", "")
    student["Phone"] = student_info.get("phone", "")
    student["Report Card Cadency Months"] = student_info.get("report_card_cadency_months", "")
    student["Status"] = student_info.get("status", "")
    student["Quizlet"] = student_info.get("quizlet", "")
    student["Drive"] = student_info.get("drive", "")
    student["Homework"] = student_info.get("homework", "")
    student["Lesson Plan"] = student_info.get("lesson_plan", "")


async def get_student_info(student_id: str, db: DynamoDBServiceResource) -> Optional[Dict[str, Any]]:
    """Recupera info base studente (USERS Table)."""
    try:
        table = await get_table(db, settings.USERS_TABLE)
        response_info = await table.get_item(Key={"id": student_id})
        student_info = response_info["Item"]
        return create_student_response(student_info)
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_student_info (USERS table): {e}")
        return None


async def get_lesson_plan_content_db(db, student_id: str) -> Optional[str]:
    """Ottiene il contenuto del Lesson Plan (USERS Table)."""
    try:
        response = db.get_item(Key={"id": student_id})
        return response.get("Item", {}).get("LessonPlanContent")
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_lesson_plan_content_db (USERS table): {e}")
        return None


async def save_lesson_plan_content_db(db, student_id: str, content: str) -> Dict[str, Any]:
    """Salva il contenuto del Lesson Plan (USERS Table)."""
    try:
        db.update_item(
            Key={"id": student_id},
            UpdateExpression="SET LessonPlanContent = :c",
            ExpressionAttributeValues={":c": content or ""},
        )
        return {"success": True, "message": "Lesson Plan salvato correttamente."}
    except ClientError as e:
        logger.error(f"DynamoDB Error in save_lesson_plan_content_db (USERS table): {e}")
        return {"success": False, "error": str(e)}


async def log_call_to_db(
    group_call: dict,
    db: DynamoDBServiceResource,
) -> Dict[str, Any]:
    """
    Registra una riga di chiamata (TRACKER Table).
    Aggiorna a catena documenti correlati:
        - contract (left_calls, used_calls, status)
        - report card (crea se non esiste una nuova draft per coach e elimina se esiste la no show oppure aggiorna status della no show a draft)

    """
    try:
        for individual_call in group_call:
            call = individual_call["call"]
            contract = individual_call["contract"]

            # data for checking
            unlimited = contract.get("unlimited", False)
            max_end_date = contract.get("max_end_date")
            start_date = contract.get("start_date")
            status = contract.get("status")
            left_calls = contract.get("left_calls")
            call_units = call["units"]
            call_date = call["date"]
            calls_per_week = call["calls_per_week"]
            total_calls = call["total_calls"]
            report_card_generator_id = contract.get("report_card_generator_id")

            # 0) A priori check
            if status != "Active":
                return {"error": f"contract {contract['contract_id']} not active"}
            if not unlimited:
                if max_end_date is not None and call_date > max_end_date:
                    return {"error": f"contract {contract['contract_id']} is expired"}
                if call_units > left_calls:
                    return {"error": f"contract {contract['contract_id']} has less left calls"}

        for individual_call in group_call:
            call = individual_call["call"]
            contract = individual_call["contract"]
            checks: List[Dict] = []
            puts: List[Dict] = []
            updates: List[Dict] = []
            deletes: List[Dict] = []

            # 1) CONTRACT: Check if contract has been initialized and its real status

            # status
            checks.append(
                {
                    "TableName": settings.CONTRACTS_TABLE,
                    "Key": to_low_level_item({"contract_id": call["contract_id"]}),
                    "ConditionExpression": "#st = :active",
                    "ExpressionAttributeNames": {
                        "#st": "status",
                    },
                    "ExpressionAttributeValues": {
                        ":active": {"S": "Active"},
                    },
                }
            )
            if not unlimited:
                if start_date is None:
                    delta_days = int(ceil(7 * 1.7 * total_calls / calls_per_week**0.5))
                    calculated_max_end_date = (
                        datetime.fromisoformat(call_date).date() + timedelta(days=delta_days)
                    ).isoformat()

                    # set start_date and max_end_date
                    updates.append(
                        {
                            "TableName": settings.CONTRACTS_TABLE,
                            "Key": to_low_level_item({"contract_id": call["contract_id"]}),
                            "ConditionExpression": "attribute_exists(contract_id) AND attribute_not_exists(start_date)",
                            "UpdateExpression": "SET start_date = :call_date, max_end_date = :max_end",
                            "ExpressionAttributeValues": {
                                ":call_date": {"S": call_date},
                                ":max_end": {"S": calculated_max_end_date},
                            },
                        }
                    )
                if max_end_date is not None:
                    # call_date <= max_end_date
                    checks.append(
                        {
                            "TableName": settings.CONTRACTS_TABLE,
                            "Key": to_low_level_item({"contract_id": call["contract_id"]}),
                            "ConditionExpression": ":call_date <= #max_end",
                            "ExpressionAttributeNames": {
                                "#max_end": "max_end_date",
                            },
                            "ExpressionAttributeValues": {
                                ":call_date": {"S": call["date"]},
                            },
                        }
                    )

                # call_units <= left_calls
                checks.append(
                    {
                        "TableName": settings.CONTRACTS_TABLE,
                        "Key": to_low_level_item({"contract_id": call["contract_id"]}),
                        "ConditionExpression": ":units <= #left",
                        "ExpressionAttributeNames": {
                            "#left": "left_calls",
                        },
                        "ExpressionAttributeValues": {
                            ":units": {"N": str(call_units)},
                        },
                    }
                )

            # 2) TRACKER: Put con 'attribute_not_exists(session_id)'
            puts.append(
                {
                    "TableName": settings.TRACKER_TABLE,
                    "Item": to_low_level_item(call),
                    "ConditionExpression": "attribute_not_exists(#pk_attr) AND attribute_not_exists(#sk_attr)",
                    "ExpressionAttributeNames": {
                        "#pk_attr": "contract_id",
                        "#sk_attr": "session_id",
                    },
                }
            )

            # 3) CONTRACT: se NON unlimited, aggiorna conteggi
            if not unlimited:
                # Unico Update per conteggi
                updates.append(
                    {
                        "TableName": settings.CONTRACTS_TABLE,
                        "Key": to_low_level_item({"contract_id": call["contract_id"]}),
                        "ConditionExpression": "attribute_exists(contract_id) AND attribute_exists(left_calls) AND attribute_exists(used_calls)",
                        "UpdateExpression": "SET left_calls = left_calls - :units, used_calls = used_calls + :units",
                        "ExpressionAttributeValues": {
                            ":units": {"N": str(call_units)},
                        },
                    }
                )

                # Secondo Update condizionale **sullo stato pre-transazione**:
                # Se left_calls == call_units → setta status = 'Inactive'
                updates.append(
                    {
                        "TableName": settings.CONTRACTS_TABLE,
                        "Key": to_low_level_item({"contract_id": call["contract_id"]}),
                        "UpdateExpression": "SET #st = :inactive",
                        "ConditionExpression": "attribute_exists(contract_id) AND attribute_exists(left_calls) AND left_calls = :units",
                        "ExpressionAttributeNames": {"#st": "status"},
                        "ExpressionAttributeValues": {
                            ":units": {"N": str(call_units)},
                            ":inactive": {"S": "Inactive"},
                        },
                    }
                )

            # 4) REPORT CARD

            if report_card_generator_id is not None:
                report_card_id = f"{call['coach_id']}#{report_card_generator_id}"
                report_cards_table = await get_table(db, settings.REPORT_CARDS_TABLE)

                report_cards_response = await report_cards_table.query(
                    KeyConditionExpression=Key("report_card_id").eq(report_card_id) & Key("start_month").lte(call_date),
                    FilterExpression=Attr("end_month").gt(call_date),
                    ProjectionExpression="#report_card_id, #start_month, #status",
                    ExpressionAttributeNames={
                        "#report_card_id": "report_card_id",
                        "#start_month": "start_month",
                        "#status": "status",
                    },
                )
                report_cards = report_cards_response.get("Items", [])
                report_card = report_cards[0] if report_cards else {}

                # 4a) CREAZIONE se non esiste e rimozione di eventuale no show
                if not report_card:
                    report_card_generators_table = await get_table(db, settings.REPORT_CARD_GENERATORS_TABLE)
                    report_card_generator_response = await report_card_generators_table.get_item(
                        Key={"report_card_generator_id": report_card_generator_id}
                    )
                    report_card_generator = report_card_generator_response.get("Item")
                    assert (
                        report_card_generator["current_start_month"] <= call_date
                        and call_date < report_card_generator["next_start_month"]
                        or report_card_generator["next_start_month"] <= call_date
                    ), "Report card generator non aggiornato"

                    # new report card
                    report_card["report_card_id"] = report_card_id
                    if (
                        report_card_generator["current_start_month"] <= call_date
                        and call_date < report_card_generator["next_start_month"]
                    ):
                        report_card["start_month"] = report_card_generator["current_start_month"]
                        report_card["end_month"] = report_card_generator["next_start_month"]
                    if report_card_generator["next_start_month"] <= call_date:
                        report_card["start_month"] = report_card_generator["next_start_month"]
                        report_card["end_month"] = (
                            datetime.fromisoformat(report_card_generator["next_start_month"] + "-01").date()
                            + relativedelta(months=contract["report_card_cadency"])
                        ).strftime("%Y-%m")
                    report_card["coach_id"] = call["coach_id"]
                    report_card["student_id"] = call["student_id"]
                    report_card["status"] = "draft"
                    report_card["report_card_generator_id"] = report_card_generator_id
                    report_card["report_card_email_recipients"] = contract["report_card_email_recipients"]
                    report_card["report_card_cadency"] = contract["report_card_cadency"]
                    report_card["client_id"] = contract["client_id"]

                    puts.append(
                        {
                            "TableName": settings.REPORT_CARDS_TABLE,
                            "Item": to_low_level_item(report_card),
                            "ConditionExpression": "attribute_not_exists(#pk_attr) AND attribute_not_exists(#sk_attr)",
                            "ExpressionAttributeNames": {
                                "#pk_attr": "report_card_id",
                                "#sk_attr": "start_month",
                            },
                        }
                    )
                    # delete no show rc di head coach JJ
                    deletes.append(
                        {
                            "TableName": settings.REPORT_CARDS_TABLE,
                            "Key": to_low_level_item(
                                {
                                    "report_card_id": "#".join(["JJ"] + report_card["report_card_id"].split("#")[1:]),
                                    "start_month": report_card["start_month"],
                                }
                            ),
                            "ConditionExpression": "attribute_not_exists(report_card_id) OR #status = :no_show",
                            "ExpressionAttributeNames": {
                                "#status": "status",
                            },
                            "ExpressionAttributeValues": {
                                ":no_show": {"S": "no_show"},
                            },
                        }
                    )
                else:
                    # 4b) PROMOZIONE NO_SHOW -> DRAFT (se esiste)
                    if report_card["status"] == "no_show":
                        updates.append(
                            {
                                "TableName": settings.REPORT_CARDS_TABLE,
                                "Key": to_low_level_item(
                                    {
                                        "report_card_id": report_card["report_card_id"],
                                        "start_month": report_card["start_month"],
                                    }
                                ),
                                "UpdateExpression": "SET #status = :draft",
                                "ConditionExpression": "attribute_exists(report_card_id) AND attribute_exists(start_month) AND #status = :no_show",
                                "ExpressionAttributeNames": {"#status": "status"},
                                "ExpressionAttributeValues": to_low_level_item(
                                    {":no_show": "no_show", ":draft": "draft"}
                                ),
                            }
                        )

            # 5) Debrief
            debrief = {
                "student_id": call["student_id"],
                "date": call["date"],
                "coach_id": call["coach_id"],
                "draft": True,
            }
            puts.append(
                {
                    "TableName": settings.DEBRIEFS_TABLE,
                    "Item": to_low_level_item(debrief),
                    "ConditionExpression": "attribute_not_exists(#pk_attr) AND attribute_not_exists(#sk_attr)",
                    "ExpressionAttributeNames": {
                        "#pk_attr": "student_id",
                        "#sk_attr": "date",
                    },
                }
            )

            await make_atomic_transaction(db, checks=checks, puts=puts, updates=updates, deletes=deletes)

        return {"success": True, "message": "Chiamata registrata correttamente."}
    except ClientError as e:
        logger.error(f"DynamoDB Error in log_call_to_db (TRACKER | CONTRACT | REPORT_CARD table): {e}")
        return {"success": False, "error": str(e)}


async def get_monthly_earnings(coach_id: str, db: DynamoDBServiceResource) -> float:
    """Calcola il guadagno (TRACKER Table, coach-id-date-index)."""
    today = get_today_string()

    try:
        # GSI: coach-id-date-index (HASH: coach_id, RANGE: date)
        table = await get_table(db, settings.TRACKER_TABLE)
        response = await table.query(
            IndexName="coach-id-date-index",
            KeyConditionExpression=Key("coach_id").eq(coach_id) & Key("date").begins_with(today[:7]),
            ProjectionExpression="coach_rate",
        )
        total_earnings = sum(item.get("coach_rate", Decimal(0)) for item in response.get("Items", []))
        return float(round(total_earnings, 2))
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_monthly_earnings (TRACKER table): {e}")
        return 0.0


async def get_calls_by_coach(db, coach_id: str) -> List[Dict[str, Any]]:
    """Recupera tutte le chiamate (TRACKER Table, coach-id-date-index)."""
    try:
        tracker_table = await get_table(db, settings.TRACKER_TABLE)
        lessons = await tracker_table.query(
            IndexName="coach-id-date-index",
            KeyConditionExpression=Key("coach_id").eq(coach_id),
            ScanIndexForward=False,
            ProjectionExpression=", ".join(["date", "student_id", "product_id", "coach_rate"]),
        )
        products_table = await get_table(db, settings.PRODUCTS_TABLE)
        history = []
        for item in lessons.get("Items", []):
            product_response = await products_table.get_item(Key={"product_id": item.get("product_id")})
            history.append(
                {
                    "date": item.get("date"),
                    "studentId": item.get("student_id"),
                    "productName": product_response["Item"]["product_name"],
                    "earnings": float(item.get("coach_rate", 0)),
                }
            )

        return history
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_calls_by_coach (TRACKER table): {e}")
        return []


async def get_calls_by_student(student_id: str, db: DynamoDBServiceResource) -> List[Dict[str, Any]]:
    """Recupera tutte le chiamate (TRACKER Table, student-id-date-index)."""
    try:
        tracker_table = await get_table(db, settings.TRACKER_TABLE)
        lessons = await tracker_table.query(
            IndexName="student-id-date-index",
            KeyConditionExpression=Key("student_id").eq(student_id),
            ScanIndexForward=False,
            ProjectionExpression=", ".join(["date", "product_id", "coach_id", "duration", "attendance", "notes"]),
        )

        products_table = await get_table(db, settings.PRODUCTS_TABLE)

        history = []
        for item in lessons.get("Items", []):
            product_response = await products_table.get_item(Key={"product_id": item.get("product_id")})
            history.append(
                {
                    "date": item.get("date"),
                    "productName": product_response["Item"]["product_name"],
                    "coachId": item.get("coach_id"),
                    "duration": item.get("duration"),
                    "attendance": item.get("attendance"),
                    "notes": item.get("notes"),
                }
            )

        return history
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_calls_by_student (TRACKER table): {e}")
        return []


async def get_student_contracts(student_id: str, db: DynamoDBServiceResource) -> List[Dict[str, Any]]:
    contracts_table = await get_table(db, settings.CONTRACTS_TABLE)
    contracts_response = await contracts_table.query(
        IndexName="student-id-status-index",
        KeyConditionExpression=Key("student_id").eq(student_id),
        ScanIndexForward=False,
        ProjectionExpression=", ".join(["left_calls", "used_calls", "max_end_date", "product_id"]),
    )
    products_table = await get_table(db, settings.PRODUCTS_TABLE)

    contracts = []
    for item in contracts_response.get("Items", []):
        product_response = await products_table.get_item(Key={"product_id": item.get("product_id")})
        contracts.append(
            {
                "product": {
                    "productName": product_response["Item"]["product_name"],
                    "duration": product_response["Item"]["duration"],
                },
                "status": item.get("status"),
                "left_calls": item.get("left_calls"),
                "used_calls": item.get("used_calls"),
                "max_end_date": item.get("max_end_date"),
            }
        )

    return contracts


def get_today_date():
    return datetime.now(timezone.utc).date()


def get_today_string(today: date = None):
    if today is None:
        return datetime.now(timezone.utc).date().isoformat()
    else:
        return today.isoformat()


def month_divisors(today_string: str) -> list[int]:
    month_number = int(today_string.split("-")[1])
    return [i for i in range(1, 7) if month_number % i == 0]


def next_month_prefix(today_date: date) -> str:
    next_month = today_date + relativedelta(months=1)
    return next_month.strftime("%Y-%m")


# Funzioni per Tabella REPORT_CARDS
async def get_report_card_tasks_db(coach: dict, db: DynamoDBServiceResource) -> Dict[str, List[Dict[str, Any]]]:
    """Trova i task di Report Card in sospeso."""
    tasks = []
    no_shows = []
    seen_students = []
    today_date = get_today_date()
    today_string = get_today_string(today_date)
    users_table = await get_table(db, settings.USERS_TABLE)
    contracts_table = await get_table(db, settings.CONTRACTS_TABLE)
    tracker_table = await get_table(db, settings.TRACKER_TABLE)
    report_cards_table = await get_table(db, settings.REPORT_CARDS_TABLE)

    # contracts[report_card_start_month <= month(today) and ]
    cadencies = month_divisors(today_string)
    next_month = next_month_prefix(today_date)
    contracts = []
    for cadency in cadencies:
        contracts_by_cadency = await contracts_table.query(
            IndexName="report-card-cadency-report-card-start-month-index",
            KeyConditionExpression=(
                Key("report_card_cadency").eq(cadency) & Key("report_card_start_month").lt(next_month)
            ),
        )
        contracts += contracts_by_cadency.get("Items", [])

    #

    for contract in contracts:
        student_id = contract["student_id"]
        if student_id in seen_students:
            continue
        student_response = await users_table.get_item(Key={"id": student_id})
        student = student_response["Item"]
        calls_response = await tracker_table.query(
            # SBAGLIATO
            KeyConditionExpression=Key("session_id").begins_with(f"{coach['id']}#{student_id}#")
        )
        calls = calls_response.get("Items", [])
        seen_students.append(student_id)

    # tasks = [{"studentId": "S001", "contractId": "C001", "name": "Mario", "surname": "Rossi", "calls": 4, "alreadyDrafted": False}]
    # no_shows = [{"studentId": "S002", "contractId": "C002", "name": "Luca", "surname": "Verdi", "alreadySubmitted": False, "period": "current"}]
    return {"tasks": tasks, "noShows": no_shows}


async def handle_report_card_submission(db, data: Dict[str, Any]) -> Dict[str, Any]:
    """Salva o aggiorna un Report Card (REPORT_CARDS Table)."""
    coach_id = data.get("coachId")
    contract_id = data.get("contractId")
    student_id = data.get("studentId")
    current_date_iso = get_today_string()

    # PK: student_id, SK: report_card_id (coach_id#contract_id#date)
    report_card_id = f"{coach_id}#{contract_id}#{current_date_iso}"

    try:
        db.put_item(
            Item={
                "student_id": student_id,
                "report_card_id": report_card_id,
                "coach_id": coach_id,
                "contract_id": contract_id,
                "date": current_date_iso,
                "Report": data.get("report"),
                "Sent": "NO",
            }
        )
        return {"success": True, "message": "Report Card salvata in bozza."}
    except ClientError as e:
        logger.error(f"DynamoDB Error in handle_report_card_submission (REPORT_CARDS table): {e}")
        return {"success": False, "error": str(e)}


# Funzioni per Tabella DEBRIEFS
async def handle_debrief_submission_db(db, data: Dict[str, Any]) -> Dict[str, Any]:
    """Salva una bozza di Debrief (DEBRIEFS Table)."""
    student_id = data.get("studentId")
    coach_id = data.get("coachId")
    current_date_iso = datetime.now(timezone.utc).date().isoformat()

    # PK: student_id, SK: date (ISO_TIMESTAMP)
    try:
        db.put_item(
            Item={
                "student_id": student_id,
                "date": current_date_iso,
                "coach_id": coach_id,
                "Goals": data.get("goals", ""),
                "Topics": data.get("topics", ""),
                "Draft": "YES" if data.get("draft") else "NO",
            }
        )
        return {"success": True, "message": "Debrief salvato correttamente."}
    except ClientError as e:
        logger.error(f"DynamoDB Error in handle_debrief_submission_db (DEBRIEFS table): {e}")
        return {"success": False, "error": str(e)}


# Funzioni per Tabella FLASHCARDS (Non definita, ma ne assumiamo la struttura)
async def get_flashcards(db, student_id: str) -> List[Dict[str, Any]]:
    """Recupera le flashcard di uno studente (Flashcards Table)."""
    # Assumo che db sia la Tabella Flashcards
    try:
        # table = get_table(db, settings.FLASHCARDS_TABLE)
        response = db.query(
            KeyConditionExpression=Key("student_id").eq(student_id)
            & Key("term").begins_with("#")  # Assumo PK: student_id, SK: term
        )
        cards = [
            {
                "en": item.get("EN"),
                "it": item.get("IT"),
                "status": item.get("Status", "unknown"),
            }
            for item in response.get("Items", [])
        ]
        return cards
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_flashcards (FLASHCARDS table): {e}")
        return []


# async def update_flashcard_status(db, data: Dict[str, Any]) -> Dict[str, Any]:
#     """Aggiorna lo stato di una flashcard (Flashcards Table)."""
#     student_id = data.get("studentId")
#     cards = data.get("cards", [])

#     updated_count = 0
#     try:
#         with db.batch_writer() as batch:
#             for card in cards:
#                 en_term = card.get("en")
#                 if not en_term:
#                     continue

#                 # PK: student_id, SK: term
#                 batch.update_item(
#                     Key={"student_id": student_id, "term": en_term},
#                     UpdateExpression="SET #s = :s ADD Attempts :incA, Correct :incC",
#                     ExpressionAttributeNames={"#s": "Status"},
#                     ExpressionAttributeValues={
#                         ":s": card.get("status"),
#                         ":incA": to_decimal(1),
#                         ":incC": to_decimal(1) if card.get("status").lower() == "known" else to_decimal(0),
#                     },
#                 )
#                 updated_count += 1

#         return {"success": True, "updated": updated_count}
#     except ClientError as e:
#         logger.error(f"DynamoDB Error in update_flashcard_status (FLASHCARDS table): {e}")
#         return {"success": False, "error": str(e)}
