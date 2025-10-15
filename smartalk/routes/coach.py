import datetime
import logging
from decimal import Decimal
from typing import Any, List, Optional

from boto3.dynamodb.conditions import Attr, Key
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from smartalk.core.dynamodb import get_dynamodb_connection
from smartalk.core.settings import settings

# --- IMPOSTAZIONI INIZIALI ---
router = APIRouter(prefix="/coach", tags=["coach"])
DBDependency = Depends(get_dynamodb_connection)
logger = logging.getLogger("coach_routes")


# -------------------------------------------------
# 1. MODELLI PYDANTIC (Data Shapes)
# -------------------------------------------------
class Student(BaseModel):
    id: str
    name: str
    surname: str

class ProductRate(BaseModel):
    head_coach: Decimal = Field(..., alias="Head Coach")
    senior_coach: Decimal = Field(..., alias="Senior Coach")
    junior_coach: Decimal = Field(..., alias="Junior Coach")

class Product(BaseModel):
    product_id: str
    product_name: str
    duration: int
    participants: int
    rates: ProductRate

class Contract(BaseModel):
    contract_id: str
    product_id: str
    left_calls: Optional[int] = None
    unlimited: bool = False
    product: Product

class CallLogRequest(BaseModel):
    coach_id: str
    product_id: str
    contract_id: Optional[str] = None
    student_ids: List[str]
    call_date: datetime.date
    call_duration: int
    attendance: str = "YES"
    notes: Optional[str] = ""

class DebriefSubmitRequest(BaseModel):
    coach_id: str
    student_id: str
    date: Optional[datetime.datetime] = None
    goals: str = ""
    topics: str = ""
    grammar: str = ""
    vocabulary: str = ""
    pronunciation: str = ""
    other: str = ""
    homework: str = ""
    draft: bool = True

class ReportCardSubmitRequest(BaseModel):
    student_id: str
    contract_id: str
    coach_id: str
    attendance: str
    report: str

# -------------------------------------------------
# 2. FUNZIONI DI SERVIZIO (Interazione con DB)
# -------------------------------------------------

async def get_active_students_from_db(db) -> List[Student]:
    table = await db.Table(settings.USERS_TABLE)
    response = await table.query(
        IndexName='user-type-index',
        KeyConditionExpression=Key('user_type').eq('student'),
        FilterExpression=Attr('status').eq('Active')
    )
    students = response.get("Items", [])
    # Filtra per assicurarsi che gli studenti abbiano un ID
    return [Student(id=s['id'], name=s.get('name', ''), surname=s.get('surname', '')) for s in students if 'id' in s]


async def get_student_contracts_from_db(student_id: str, db) -> List[Contract]:
    contracts_table = await db.Table(settings.CONTRACTS_TABLE)
    products_table = await db.Table(settings.PRODUCTS_TABLE)

    response = await contracts_table.query(
        IndexName='student-id-index',
        KeyConditionExpression=Key('student_id').eq(student_id),
        FilterExpression=Attr('status').eq('Active')
    )
    contracts_data = response.get("Items", [])
    if not contracts_data:
        return []

    product_ids = list(set([c['product_id'] for c in contracts_data]))
    products_response = await products_table.scan(
        FilterExpression=Attr('product_id').is_in(product_ids)
    )
    products_map = {p['product_id']: p for p in products_response.get("Items", [])}

    result = []
    for c in contracts_data:
        prod_id = c['product_id']
        product_details = products_map.get(prod_id)
        if product_details:
            product = Product(
                product_id=prod_id,
                product_name=product_details.get('product_name', prod_id),
                duration=int(product_details.get('duration', 60)),
                participants=int(product_details.get('participants', 1)),
                rates=product_details.get('rates', {})
            )
            contract = Contract(
                contract_id=c['contract_id'],
                product_id=prod_id,
                left_calls=c.get('left_calls'),
                unlimited=c.get('unlimited', False),
                product=product
            )
            result.append(contract)
    return result

# -------------------------------------------------
# 3. ROTTE API (Endpoints)
# -------------------------------------------------

@router.get("/students", response_model=List[Student])
async def get_students(db: Any = DBDependency):
    """Restituisce una lista di tutti gli studenti attivi."""
    try:
        return await get_active_students_from_db(db)
    except Exception as e:
        logger.error(f"Error in get_students: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/student/{student_id}/contracts", response_model=List[Contract])
async def get_student_contracts(student_id: str, db: Any = DBDependency):
    """Restituisce i contratti attivi per un singolo studente."""
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")
    try:
        return await get_student_contracts_from_db(student_id, db)
    except Exception as e:
        logger.error(f"Error in get_student_contracts: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/log-call")
async def log_call(data: CallLogRequest, db: Any = DBDependency):
    """Registra una nuova chiamata nel tracker."""
    tracker_table = await db.Table(settings.TRACKER_TABLE)
    try:
        for student_id in data.student_ids:
            session_id = f"{student_id}#{data.call_date.isoformat()}"
            item = {
                'contract_id': data.contract_id,
                'session_id': session_id,
                'student_id': student_id,
                'coach_id': data.coach_id,
                'product_id': data.product_id,
                'date': data.call_date.isoformat(),
                'duration': data.call_duration,
                'attendance': data.attendance,
                'notes': data.notes,
            }
            await tracker_table.put_item(Item=item)
        return {"success": True, "message": "Call logged successfully."}
    except Exception as e:
        logger.error(f"Error in log_call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{coach_id}/monthly-earnings")
async def get_monthly_earnings(coach_id: str, db: Any = DBDependency):
    """Calcola i guadagni del coach nel mese corrente."""
    today = datetime.date.today()
    start_of_month = today.replace(day=1).isoformat()
    
    table = await db.Table(settings.TRACKER_TABLE)
    response = await table.query(
        IndexName='coach-id-date-index',
        KeyConditionExpression=Key('coach_id').eq(coach_id) & Key('date').gte(start_of_month)
    )
    items = response.get("Items", [])
    total_earnings = sum(item.get('coach_rate', Decimal(0)) for item in items)
    return {"success": True, "earnings": total_earnings}

@router.post("/submit-debrief")
async def submit_debrief(data: DebriefSubmitRequest, db: Any = DBDependency):
    """Salva un debrief."""
    table = await db.Table(settings.DEBRIEFS_TABLE)
    item_date = data.date or datetime.datetime.now()
    item = data.dict()
    item['date'] = item_date.isoformat()
    
    try:
        await table.put_item(Item=item)
        return {"success": True, "message": "Debrief saved."}
    except Exception as e:
        logger.error(f"Error in submit_debrief: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit-report-card")
async def submit_report_card(data: ReportCardSubmitRequest, db: Any = DBDependency):
    """Salva una report card."""
    table = await db.Table(settings.REPORT_CARDS_TABLE)
    date_key = datetime.date.today().isoformat()
    item = data.dict()
    item['date'] = date_key
    item['sent'] = False
    
    try:
        await table.put_item(Item=item)
        return {"success": True, "message": "Report card saved."}
    except Exception as e:
        logger.error(f"Error in submit_report_card: {e}")
        raise HTTPException(status_code=500, detail=str(e))