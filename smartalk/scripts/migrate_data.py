import asyncio
import logging
import os

# Permette allo script di trovare i moduli del progetto
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartalk.core.settings import settings
from smartalk.db_usage.dynamodb_auth import hash_password

# --- CONFIGURAZIONE logging.basicConfig(
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("migration_test.log", mode='w'), # Scrive su file, 'w' = sovrascrivi ogni volta
        logging.StreamHandler()  # Mantiene i log anche sul terminale
    ]
)
logger = logging.getLogger("data_migration")
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxkMQHNbDYt3LesAzEDbeii9aqgJ7xsww31yWcK9fLBs9l-tvKgR1WsVcAXJ3CNcm8/exec"

# ---
# SEZIONE 1: MODELLI DI VALIDAZIONE Pydantic (V2, Completi e Corretti)
# ---

# Funzione helper per validatori di date
def parse_date_field(value: Any) -> Optional[date]:
    if isinstance(value, str) and value.strip():
        # Gestisce formati come 'YYYY-MM-DD' o 'DD/MM/YYYY'
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S.%fZ'):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
        raise ValueError(f"Impossibile parsare la data dalla stringa: {value}")
    return None

class CoachUser(BaseModel):
    id: str = Field(..., alias='Coach ID')
    name: str = Field(..., alias='Name')
    surname: str = Field(..., alias='Surname')
    status: str = Field(..., alias='Status')
    email: EmailStr = Field(..., alias='Email')
    phone: Optional[str] = Field(None, alias='Phone')
    role: Optional[str] = Field(None, alias='Role')
    wise_payment_info: Optional[str] = Field(None, alias='Wise Payment Info')
    password: int = Field(..., alias='Password')
    agreement: Optional[str] = Field(None, alias='Agreement')
    payment_folder: Optional[str] = Field(None, alias='Payment Folder')
    middle_name: Optional[str] = Field(None, alias='Middle Name')
    address: Optional[str] = Field(None, alias='Address')
    citizenship: Optional[str] = Field(None, alias='Citizenship')

class StudentUser(BaseModel):
    id: str = Field(..., alias='Student ID')
    name: str = Field(..., alias='Name')
    surname: str = Field(..., alias='Surname')
    # La password e l'email possono essere vuote per le righe "segnaposto"
    password: Optional[str] = Field(None, alias='Password')
    email: Optional[EmailStr] = Field(None, alias='Email')
    secondary_email: Optional[EmailStr] = Field(None, alias='Secondary Email')
    phone: Optional[str] = Field(None, alias='Phone')
    status: str = Field(..., alias='Status')
    onboarded: bool = Field(False, alias='Onboarded (dashboard)')
    report_card_cadency_months: Optional[int|str] = Field(None, alias='Report Card Cadency Months')
    quizlet: Optional[str] = Field(None, alias='Quizlet')
    drive: Optional[str] = Field(None, alias='Drive')
    homework: Optional[str] = Field(None, alias='Homework')
    lesson_plan: Optional[str] = Field(None, alias='Lesson Plan')
    
    @field_validator('onboarded', mode='before')
    def standardize_onboarded(cls, value):
        return str(value).strip().upper() in ['Y', 'YES', 'TRUE']

class ClientUser(BaseModel):
    name: str = Field(..., alias='Company Name')
    id: str = Field(..., alias='Company ID')
    password: int = Field(..., alias='Company Password')

class Product(BaseModel):
    product_id: str = Field(..., alias='Product ID')
    product_name: str = Field(..., alias='Product Name')
    duration: int = Field(..., alias='Duration')
    participants: int = Field(..., alias='Participants')
    head_coach_rate: Optional[Decimal] = Field(None, alias='Head Coach')
    senior_coach_rate: Optional[Decimal] = Field(None, alias='Senior Coach')
    junior_coach_rate: Optional[Decimal] = Field(None, alias='Junior Coach')
    net_after_taxes: Optional[Decimal] = Field(None, alias='Net after taxes (€)')
    margin: Optional[Decimal] = Field(None, alias='Margin (€)')
    # Questi campi possono essere numerici o stringhe vuote
    sprint_path: Optional[str] = Field(None, alias='Sprint Path')
    smart_path: Optional[str] = Field(None, alias='Smart Path')
    impact_path: Optional[str] = Field(None, alias='Impact Path')

    @field_validator('sprint_path', 'smart_path', 'impact_path', mode='before')
    def stringify_paths(cls, value):
        return str(value) if value is not None else None

class Contract(BaseModel):
    contract_id: str = Field(..., alias='Contract ID')
    student_id: str = Field(..., alias='Student ID')
    product_id: str = Field(..., alias='Product ID')
    status: str = Field(..., alias='Status')
    invoice_id: Optional[str] = Field(None, alias='Invoice ID')
    client_id: Optional[str] = Field(None, alias='Client ID')
    package: Optional[str] = Field(None, alias='Package')
    # Questi campi numerici possono essere vuoti
    manual_total_calls: Optional[int|str] = Field(None, alias='Manual Total Calls')
    total_calls: Optional[int|str] = Field(None, alias='Total Calls')
    calls_per_week: Optional[float] = Field(None, alias='Calls/week')
    used_calls: Optional[float] = Field(None, alias='Used Calls')
    left_calls: Optional[float] = Field(None, alias='Left Calls')
    report_card_cadency: Optional[int|str] = Field(None, alias='Report Card Cadency')
    # ------------------
    unlimited: bool = Field(False, alias='Unlimited')
    start_date: Optional[date] = Field(None, alias='Start Date')
    max_end_date: Optional[date] = Field(None, alias='Max End Date')
    report_card_start_date: Optional[date] = Field(None, alias='Report Card Start Date')
    report_card_email_recipients: Optional[str] = Field(None, alias='Report Card Email Recipient(s)')

    @field_validator('unlimited', mode='before')
    def standardize_unlimited(cls, value):
        return str(value).strip().upper() in ['Y', 'YES', 'TRUE']
    
    @field_validator('start_date', 'max_end_date', 'report_card_start_date', mode='before')
    def _parse_date_fields(cls, value):
        return parse_date_field(value)

class Tracker(BaseModel):
    session_date: date = Field(..., alias='Date')
    student_id: str = Field(..., alias='Student ID')
    contract_id: str = Field(..., alias='Contract ID')
    coach_id: str = Field(..., alias='Coach ID')
    product_id: str = Field(..., alias='Product ID')
    units: Optional[Decimal] = Field(None, alias='Units')
    duration: Optional[int|str] = Field(None, alias='Duration')
    coach_rate: Optional[Decimal] = Field(None, alias='Coach Rate')
    prod_cost: Optional[Decimal] = Field(None, alias='Prod cost')
    attendance: Optional[str] = Field(None, alias='Attendance')
    notes: Optional[str] = Field(None, alias='Notes')

    @field_validator('session_date', mode='before')
    def _parse_date(cls, value):
        return parse_date_field(value)

class Invoice(BaseModel):
    invoice_id: str = Field(..., alias='Invoice ID')
    client_id: str = Field(..., alias='Client ID')
    buyer: Optional[str] = Field(None, alias='Buyer')
    invoice_date: date = Field(..., alias='Date')
    due_date: date = Field(..., alias='Due')
    amount: Decimal = Field(..., alias='Amount')
    paid: bool = Field(..., alias='Paid')
    installments: Optional[int|str] = Field(None, alias='Installments')
    email_reminder: Optional[EmailStr] = Field(None, alias='Email Reminder Expired Invoice')

    @field_validator('paid', mode='before')
    def standardize_paid(cls, value):
        return str(value).strip().upper() in ['Y', 'YES', 'TRUE']
        
    @field_validator('invoice_date', 'due_date', mode='before')
    def _parse_date_fields(cls, value):
        return parse_date_field(value)

class Debrief(BaseModel):
    debrief_date: date = Field(..., alias='Date')
    coach_id: str = Field(..., alias='Coach ID')
    student_id: str = Field(..., alias='Student ID')
    goals: Optional[str] = Field(None, alias='Goals')
    topics: Optional[str] = Field(None, alias='Topics')
    grammar: Optional[str] = Field(None, alias='Grammar')
    vocabulary: Optional[str] = Field(None, alias='Vocabulary')
    pronunciation: Optional[str] = Field(None, alias='Pronunciation')
    other: Optional[str] = Field(None, alias='Other')
    homework: Optional[str] = Field(None, alias='Homework')
    draft: bool = Field(False, alias='Draft')
    sent: bool = Field(False, alias='Sent')
    sent_date: Optional[date] = Field(None, alias='Sent Date')

    @field_validator('draft', 'sent', mode='before')
    def standardize_boolean(cls, value):
        return str(value).strip().upper() in ['Y', 'YES', 'TRUE']
        
    @field_validator('debrief_date', 'sent_date', mode='before')
    def _parse_datetime_fields(cls, value):
        return parse_date_field(value)

class ReportCard(BaseModel):
    report_date: date = Field(..., alias='Date')
    student_id: str = Field(..., alias='Student ID')
    contract_id: str = Field(..., alias='Contract ID')
    coach_id: str = Field(..., alias='Coach ID')
    attendance: Optional[str] = Field(None, alias='Attendance')
    report: Optional[str] = Field(None, alias='Report')
    status: Optional[str] = Field(None, alias='Status')
    sent: bool = Field(False, alias='Sent')

    @field_validator('sent', mode='before')
    def standardize_sent(cls, value):
        return str(value).strip().upper() in ['Y', 'YES', 'TRUE']
        
    @field_validator('report_date', mode='before')
    def _parse_date(cls, value):
        return parse_date_field(value)

# ---
# SEZIONE 2: LOGICA DI MIGRAZIONE
# ---

async def fetch_sheet_data(sheet_name: str) -> List[Dict[str, Any]]:
    """Chiama l'API di Apps Script e restituisce i dati, seguendo i reindirizzamenti."""
    logger.info(f"Fetching data for sheet: {sheet_name}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(f"{APPS_SCRIPT_URL}?sheet={sheet_name}", timeout=120.0, headers=headers)
            response.raise_for_status()
            json_data = response.json()
            if isinstance(json_data, dict) and json_data.get("success"):
                data = json_data.get("data", [])
                logger.info(f"  -> Fetched {len(data)} rows from {sheet_name}.")
                return data
            return []
        except Exception as e:
            logger.error(f"  -> An error occurred while fetching {sheet_name}: {e}", exc_info=True)
            return []

def to_dynamodb_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Converts a dictionary to a clean format for DynamoDB."""
    final_item = {}
    for key, value in item.items():
        if isinstance(value, date):
            final_item[key] = value.isoformat()
        elif isinstance(value, datetime):
            final_item[key] = value.isoformat()
        # --- FIX IS HERE ---
        # Convert any float to a Decimal before sending to DynamoDB
        elif isinstance(value, float):
            final_item[key] = Decimal(str(value))
        elif value is not None and value != "":
            final_item[key] = value
    return final_item

async def migrate_users(db: Any):
    table = await db.Table(settings.USERS_TABLE)
    # Coaches
    for row in await fetch_sheet_data("Coaches"):
        try:
            data = CoachUser.model_validate(row)
            item = data.model_dump(by_alias=False, exclude={"password"})
            item["user_type"] = "coach"
            item["password_hash"] = hash_password(str(data.password))
            await table.put_item(Item=to_dynamodb_item(item_to_use=item))
        except ValidationError as e:
            logger.warning(f"  -> Skipping invalid Coach row: {e} | Data: {row}")
    # Students
    for row in await fetch_sheet_data("Students"):
        try:
            data = StudentUser.model_validate(row)
            item = data.model_dump(by_alias=False, exclude={"password"})
            item["user_type"] = "student"
            item["password_hash"] = hash_password(str(data.password))
            await table.put_item(Item=to_dynamodb_item(item_to_use=item))
        except ValidationError as e:
            # not real error
            if row.get('password') == '' and row.get('Email') == '':
                continue
            logger.warning(f"  -> Skipping invalid Student row: {e} | Data: {row}")
    # Clients (Companies only)
    for row in await fetch_sheet_data("Clients"):
        try:
            data = ClientUser.model_validate(row)
            item = {
                "id": data.id,
                "name": data.name,
                "user_type": "company",
                "password_hash": hash_password(str(data.password))
            }
            await table.put_item(Item=to_dynamodb_item(item_to_use=item))
        except ValidationError:
            # Salta silenziosamente le righe che non sono "Company" (es. clienti individuali)
            continue

async def migrate_generic(db: Any, table_name: str, sheet_name: str, model_cls: BaseModel, special_logic=None):
    table = await db.Table(table_name)
    for row in await fetch_sheet_data(sheet_name):
        try:
            data = model_cls.model_validate(row)
            item = to_dynamodb_item(data)
            if special_logic:
                item = special_logic(item)
            await table.put_item(Item=item)
        except (ValidationError, InvalidOperation, ValueError) as e:
            logger.warning(f"  -> Skipping invalid {sheet_name} row: {e} | Data: {row}")

# ---
# SEZIONE 3: FUNZIONE PRINCIPALE DI MIGRAZIONE
# ---

async def migrate_all_data(db: Any):
    """Orchestra l'intera migrazione dei dati."""
    logger.info("STARTING DATA MIGRATION FROM GOOGLE SHEETS API...")
    
    logger.info("\n--- Migrating Users ---")
    await migrate_users(db)
    
    logger.info("\n--- Migrating Products ---")
    await migrate_generic(db, settings.PRODUCTS_TABLE, "Products", Product)
    
    def contract_logic(item):
        if item["unlimited"]:
            item.pop("used_calls")
            item.pop("left_calls")
        return item
    logger.info("\n--- Migrating Contracts ---")
    await migrate_generic(db, settings.CONTRACTS_TABLE, "Contracts", Contract, special_logic=contract_logic)
    
    def tracker_logic(item):
        item["date"] = item.pop("session_date")
        item["session_id"] = f"{item['student_id']}#{item['date']}"
        return item
    logger.info("\n--- Migrating Tracker ---")
    await migrate_generic(db, settings.TRACKER_TABLE, "Tracker", Tracker, special_logic=tracker_logic)
    
    def invoice_logic(item):
        item["date"] = item.pop("invoice_date")
        item["due"] = item.pop("due_date")
        return item
    logger.info("\n--- Migrating Invoices ---")
    await migrate_generic(db, settings.INVOICES_TABLE, "Invoices", Invoice, special_logic=invoice_logic)
    
    def debrief_logic(item):
        item["date"] = item.pop("debrief_date")
        return item
    logger.info("\n--- Migrating Debriefs ---")
    await migrate_generic(db, settings.DEBRIEFS_TABLE, "Debriefs", Debrief, special_logic=debrief_logic)

    def report_card_logic(item):
        item["date"] = item.pop("report_date")
        return item
    logger.info("\n--- Migrating Report Cards ---")
    await migrate_generic(db, settings.REPORT_CARDS_TABLE, "Report Cards", ReportCard, special_logic=report_card_logic)
    
    logger.info("DATA MIGRATION COMPLETED.")