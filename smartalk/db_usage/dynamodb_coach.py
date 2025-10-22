# smartalk/db_usage/dynamodb_coach.py

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from aioboto3.session import ResourceCreatorContext
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from pydantic import BaseModel, EmailStr, Field

from smartalk.core.settings import settings

logger = logging.getLogger(__name__)

# --- UTILITY E STUB ---

def to_decimal(value):
    """Converte float/int in Decimal per DynamoDB."""
    try:
        if value is None:
            return Decimal(0)
        return Decimal(str(value))
    except Exception:
        return Decimal(0)

def get_product_rates(product_id: str) -> Dict[str, Any]:
    """STUB: Recupera i tassi di un prodotto (simulazione)."""
    return {
        "duration_minutes": 60,
        "participants": 1,
        "rates": {
            "Head Coach": 50.00,
            "Senior Coach": 40.00,
            "Junior Coach": 30.00
        }
    }

def generate_debrief_text_ai(payload: Dict[str, Any]) -> Dict[str, Any]:
    """STUB: Chiama Gemini/AI per la generazione di testo (Debrief)."""
    field = payload.get('fieldType', 'goals')
    text = payload.get('currentText', 'Nessun testo fornito')
    return {
        "success": True, 
        "suggestion": f"[AI SUGGESTION per {field.upper()}]: Revisione basata su: '{text}'."
    }

# ====================================================================
# FUNZIONI PER LA DASHBOARD COACH (Ora richiedono 'db' - l'oggetto Table)
# ====================================================================

# Funzioni per Tabella USERS
async def get_active_students(coach_id: str, db: ResourceCreatorContext) -> List[str]:
    """Recupera gli ID degli studenti attivi assegnati a un coach (USERS Table)."""
    try:
        # HASH: user_type (index: user-type-index)
        table = await db.Table(settings.USERS_TABLE)
        response = await table.query(
            IndexName='user-type-index', 
            KeyConditionExpression=Key('user_type').eq('student'),
            FilterExpression=Attr('coach_id').eq(coach_id) & Attr('status').eq('active'),
            ProjectionExpression="#id",
            ExpressionAttributeNames={"#id": "id"}
        )
        return [item.get("id") for item in response.get('Items', [])]
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

    
async def get_student_info(student_id: str, db: dict) -> Optional[Dict[str, Any]]:
    """Recupera info base studente (USERS Table)."""
    try:
        table = await db.Table(settings.USERS_TABLE)
        response_info = await table.get_item(Key={'id': student_id})
        student_info = response_info.get('Item')
        return create_student_response(student_info)
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_student_info (USERS table): {e}")
        return None

async def get_lesson_plan_content_db(db, student_id: str) -> Optional[str]:
    """Ottiene il contenuto del Lesson Plan (USERS Table)."""
    try:
        response = db.get_item(Key={'id': student_id})
        return response.get('Item', {}).get('LessonPlanContent')
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_lesson_plan_content_db (USERS table): {e}")
        return None

async def save_lesson_plan_content_db(db, student_id: str, content: str) -> Dict[str, Any]:
    """Salva il contenuto del Lesson Plan (USERS Table)."""
    try:
        db.update_item(
            Key={'id': student_id},
            UpdateExpression="SET LessonPlanContent = :c",
            ExpressionAttributeValues={':c': content or ""}
        )
        return {"success": True, "message": "Lesson Plan salvato correttamente."}
    except ClientError as e:
        logger.error(f"DynamoDB Error in save_lesson_plan_content_db (USERS table): {e}")
        return {"success": False, "error": str(e)}

# Funzioni per Tabella TRACKER
async def log_call_to_db(db, data: Dict[str, Any]) -> Dict[str, Any]:
    """Registra una riga di chiamata (TRACKER Table)."""
    
    product_details = get_product_rates(data.get("productId"))
    role = data.get("role", "Senior Coach")
    
    native_minutes = product_details.get('duration_minutes', 60)
    minutes = data.get("callDuration", native_minutes)
    units = to_decimal(minutes / native_minutes if native_minutes else 1)
    base_rate = to_decimal(product_details['rates'].get(role, 0))
    student_list = data.get('studentIds', [data.get('studentId')])
    attendees = len(student_list)
    coach_rate_per_student = to_decimal((base_rate * units) / attendees) if attendees else to_decimal(0)
    
    try:
        with db.batch_writer() as batch:
            for sid in student_list:
                call_date_iso = datetime.fromisoformat(data["callDate"]).strftime('%Y-%m-%dT%H:%M:%S')
                contract_id = data.get("contractId", "UNKNOWN") 
                
                # PK: contract_id, SK: session_id (coach_id#student_id#ISO_DATE)
                session_id = f'{data["coachId"]}#{sid}#{call_date_iso}'

                item = {
                    'contract_id': contract_id,
                    'session_id': session_id,
                    'coach_id': data["coachId"], 
                    'student_id': sid,           
                    'date': call_date_iso,       
                    'CoachRate': coach_rate_per_student,
                    'Attendance': data.get("attendance", "YES"),
                }
                batch.put_item(Item=item)
        
        return {"success": True, "message": "Chiamata registrata correttamente."}
    except ClientError as e:
        logger.error(f"DynamoDB Error in log_call_to_db (TRACKER table): {e}")
        return {"success": False, "error": str(e)}

async def get_monthly_earnings(coach_id: str, db: dict) -> float:
    """Calcola il guadagno (TRACKER Table, coach-id-date-index)."""
    today = datetime.now(timezone.utc)
    start_of_month_prefix = today.strftime('%Y-%m-%d')
    
    try:
        # GSI: coach-id-date-index (HASH: coach_id, RANGE: date)
        table = await db.Table(settings.TRACKER_TABLE)
        response = await table.query(
            IndexName='coach-id-date-index', 
            KeyConditionExpression=Key('coach_id').eq(coach_id) & Key('date').begins_with(start_of_month_prefix[:7]),
            ProjectionExpression="coach_rate"
        )
        total_earnings = sum(item.get('coach_rate', Decimal(0)) for item in response.get('Items', []))
        return float(round(total_earnings, 2))
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_monthly_earnings (TRACKER table): {e}")
        return 0.0

async def get_calls_by_coach(db, coach_id: str) -> List[Dict[str, Any]]:
    """Recupera tutte le chiamate (TRACKER Table, coach-id-date-index)."""
    try:
        tracker_table = await db.Table(settings.TRACKER_TABLE)
        response = tracker_table.query(
            IndexName='coach-id-date-index', 
            KeyConditionExpression=Key('coach_id').eq(coach_id),
            ScanIndexForward=False 
        )
        products_table = await db.Table(settings.PRODUCTS_TABLE)
        history = [{
            "date": item.get('date'),
            "studentId": item.get('student_id'),
            "productName": await products_table.get_item(Key={"product_id": item.get('product_id')})["Item"]["product_name"],
            "earnings": float(item.get('coach_rate', 0))
        } for item in response.get('Items', [])]
        
        return history
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_call_history (TRACKER table): {e}")
        return []

async def get_calls_by_student(student_id: str, db: dict) -> List[Dict[str, Any]]:
    """Recupera tutte le chiamate (TRACKER Table, student-id-date-index)."""
    try:
        tracker_table = db.Table(settings.TRACKER_TABLE)
        response = tracker_table.query(
            IndexName='student-id-date-index', 
            KeyConditionExpression=Key('student_id').eq(student_id),
            ScanIndexForward=False 
        )

        products_table = await db.Table(settings.PRODUCTS_TABLE)
        history = [{
            "date": item.get('date'),
            "productName": await products_table.get_item(Key={"product_id": item.get('product_id')})["Item"]["product_name"],
            "coachId": item.get('coach_id'),
            "duration": item.get('duration'),
            "attendance": item.get('attendance'),
            "notes": item.get('notes'),
        } for item in response.get('Items', [])]
        
        return history
    except ClientError as e:
        logger.error(f"DynamoDB Error in get_call_history (TRACKER table): {e}")
        return []

async def get_student_contracts(student_id: str, db: dict) -> List[Dict[str, Any]]:
    contracts_table = db.Table(settings.CONTRACTS_TABLE)
    response = contracts_table.query(
        IndexName='student-id-index', 
        KeyConditionExpression=Key('student_id').eq(student_id),
        ScanIndexForward=False 
    )

    """
                      const total = c.product?.totalCalls || (c.leftCalls && c.leftCalls > 0 ? c.leftCalls : 0);
                  const used = (c.product?.totalCalls && c.leftCalls !== undefined)
                    ? Math.max(0, c.product.totalCalls - c.leftCalls)
                    : (c.leftCalls === 0 ? "All" : "-");
                  const expiration = c.maxEndDate || c.endDate || "-";
                  const status = c.leftCalls === 0 ? "Ended" : "Active";
                  return `
                    <tr class="${c.leftCalls === 0 ? 'text-gray-400' : ''}">
                      <td class="py-2 px-4">${c.product?.productName || c.productId}</td>
                      <td class="py-2 px-4 text-center">${c.product?.duration || '-'}</td>
                      <td class="py-2 px-4 text-center">${used}</td>
                      <td class="py-2 px-4 text-center">${c.leftCalls ?? '∞'}</td>
                      <td class="py-2 px-4 text-center">${expiration}</td>
                      <td class="py-2 px-4 text-center">${status}</td>
    """
    products_table = await db.Table(settings.PRODUCTS_TABLE)
    return [{
        "date": item.get('date'),
        "product": await products_table.get_item(Key={"product_id": item.get('product_id')})["Item"], # ????? c.product?.totalCalls
        "coachId": item.get('coach_id'),
        "duration": item.get('duration'),
        "attendance": item.get('attendance'),
        "notes": item.get('notes'),
    } for item in response.get('Items', [])]
        

# Funzioni per Tabella REPORT_CARDS
async def get_report_card_tasks_db(db, coach_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Trova i task di Report Card in sospeso (Simulato)."""
    # Simulazione: Dati necessari per il frontend
    tasks = [{"studentId": "S001", "contractId": "C001", "name": "Mario", "surname": "Rossi", "calls": 4, "alreadyDrafted": False}]
    no_shows = [{"studentId": "S002", "contractId": "C002", "name": "Luca", "surname": "Verdi", "alreadySubmitted": False, "period": "current"}]
    return {"tasks": tasks, "noShows": no_shows}


async def handle_report_card_submission(db, data: Dict[str, Any]) -> Dict[str, Any]:
    """Salva o aggiorna un Report Card (REPORT_CARDS Table)."""
    coach_id = data.get("coachId")
    contract_id = data.get("contractId")
    student_id = data.get("studentId")
    current_date_iso = datetime.now(timezone.utc).isoformat()

    # PK: student_id, SK: report_id (coach_id#contract_id#date)
    report_id = f"{coach_id}#{contract_id}#{current_date_iso}"

    try:
        db.put_item(
            Item={
                'student_id': student_id,
                'report_id': report_id,
                'coach_id': coach_id, 
                'contract_id': contract_id,
                'date': current_date_iso, 
                'Report': data.get("report"),
                'Sent': 'NO'
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
    current_date_iso = datetime.now(timezone.utc).isoformat()
    
    # PK: student_id, SK: date (ISO_TIMESTAMP)
    try:
        db.put_item(
            Item={
                'student_id': student_id,
                'date': current_date_iso,
                'coach_id': coach_id,
                'Goals': data.get("goals", ""),
                'Topics': data.get("topics", ""),
                'Draft': 'YES' if data.get("draft") else 'NO',
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
            KeyConditionExpression=Key('student_id').eq(student_id) & Key('term').begins_with('#') # Assumo PK: student_id, SK: term
        )
        cards = [{
            "en": item.get('EN'), "it": item.get('IT'), "status": item.get('Status', 'unknown'),
        } for item in response.get('Items', [])]
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
                en_term = card.get('en')
                if not en_term: continue
                
                # PK: student_id, SK: term
                batch.update_item(
                    Key={'student_id': student_id, 'term': en_term},
                    UpdateExpression="SET #s = :s ADD Attempts :incA, Correct :incC",
                    ExpressionAttributeNames={'#s': 'Status'},
                    ExpressionAttributeValues={
                        ':s': card.get('status'),
                        ':incA': to_decimal(1),
                        ':incC': to_decimal(1) if card.get('status').lower() == 'known' else to_decimal(0)
                    }
                )
                updated_count += 1

        return {"success": True, "updated": updated_count}
    except ClientError as e:
        logger.error(f"DynamoDB Error in update_flashcard_status (FLASHCARDS table): {e}")
        return {"success": False, "error": str(e)}