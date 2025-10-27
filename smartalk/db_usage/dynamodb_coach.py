# smartalk/db_usage/dynamodb_coach.py

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from dateutil import relativedelta
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from smartalk.core.dynamodb import get_client, get_table
from smartalk.core.settings import settings

logger = logging.getLogger(__name__)

# --- UTILITY ---


def to_decimal(value):
    """Converte float/int in Decimal per DynamoDB."""
    try:
        if value is None:
            return Decimal(0)
        return Decimal(str(value))
    except Exception:
        return Decimal(0)


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


# Funzioni per Tabella TRACKER
async def log_call_to_db(data: Dict[str, Any], coach: Dict[str, Any], db: DynamoDBServiceResource) -> Dict[str, Any]:
    """
    Registra una riga di chiamata (TRACKER Table).
    Se il contract della call ha una report_card_cadency,
    verifica e abilita la coach al report card relativo (CONTRACTS, REPORT_CARD_GENERATORS e REPORT_CARDS Table)
    """

    product_table = await get_table(db, settings.PRODUCTS_TABLE)
    product_response = product_table.get_item(data.get("productId"))
    product = product_response["Item"]

    standard_duration = product["duration"]
    effective_duration = data.get("callDuration", standard_duration)
    units = to_decimal(effective_duration / standard_duration if standard_duration else 1)
    standard_rate = to_decimal(product[f"{coach['role'].split(' ')[0].lower()}_coach_rate"])

    student_list = data.get("studentIds", [data.get("studentId")])
    assert product["participants"] == len(student_list), "Number of product participants not matching with students"
    attendees = len(student_list)
    coach_rate_per_student = to_decimal((standard_rate * units) / attendees) if attendees else to_decimal(0)

    # TODO: attendees mal gestita da client, e anche contractId
    # se ci possono essere contratti uguali con studenti diversi per i gruppi,
    # allora mettere anche student_id nelle chiavi di contract

    # le notes ?? dovrebbero essere una lista ognuna per ogni studente

    # create if not exists dalla table settings.REPORT_CARD_GENERATORS_TABLE
    # create if not exists dalla table settings.REPORT_CARDS_TABLE

    # fare transaction da get_client(db)

    try:
        with db.batch_writer() as batch:
            for sid in student_list:
                call_date_iso = datetime.fromisoformat(data["callDate"]).date().isoformat()
                contract_id = data.get("contractId", "UNKNOWN")
                coach_id = coach["id"]

                # PK: contract_id, SK: session_id (coach_id#student_id#ISO_DATE)
                session_id = f"{coach_id}#{sid}#{call_date_iso}"

                item = {
                    "contract_id": contract_id,
                    "session_id": session_id,
                    "coach_id": coach["id"],
                    "student_id": sid,
                    "date": call_date_iso,
                    "coach_rate": coach_rate_per_student,
                    "attendance": data.get("attendance", "YES"),
                }
                batch.put_item(Item=item)

        return {"success": True, "message": "Chiamata registrata correttamente."}
    except ClientError as e:
        logger.error(f"DynamoDB Error in log_call_to_db (TRACKER table): {e}")
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
        IndexName="student-id-index",
        KeyConditionExpression=Key("student_id").eq(student_id),
        ScanIndexForward=False,
        ProjectionExpression=", ".join(["status", "left_calls", "used_calls", "max_end_date", "product_id"]),
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
    return next_month.isoformat()[:7]


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


async def update_flashcard_status(db, data: Dict[str, Any]) -> Dict[str, Any]:
    """Aggiorna lo stato di una flashcard (Flashcards Table)."""
    student_id = data.get("studentId")
    cards = data.get("cards", [])

    updated_count = 0
    try:
        with db.batch_writer() as batch:
            for card in cards:
                en_term = card.get("en")
                if not en_term:
                    continue

                # PK: student_id, SK: term
                batch.update_item(
                    Key={"student_id": student_id, "term": en_term},
                    UpdateExpression="SET #s = :s ADD Attempts :incA, Correct :incC",
                    ExpressionAttributeNames={"#s": "Status"},
                    ExpressionAttributeValues={
                        ":s": card.get("status"),
                        ":incA": to_decimal(1),
                        ":incC": to_decimal(1) if card.get("status").lower() == "known" else to_decimal(0),
                    },
                )
                updated_count += 1

        return {"success": True, "updated": updated_count}
    except ClientError as e:
        logger.error(f"DynamoDB Error in update_flashcard_status (FLASHCARDS table): {e}")
        return {"success": False, "error": str(e)}
