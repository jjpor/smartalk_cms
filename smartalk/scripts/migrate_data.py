import logging
import os

# Permette allo script di trovare i moduli del progetto
import sys
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
from boto3.dynamodb.conditions import Attr, Key
from dateutil import relativedelta
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator

from smartalk.db_usage.dynamodb_coach import get_today_string

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartalk.core.dynamodb import get_table
from smartalk.core.settings import settings
from smartalk.db_usage.dynamodb_auth import hash_password

# --- CONFIGURAZIONE logging.basicConfig(
logger = logging.getLogger("data_migration")
APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/AKfycbxkMQHNbDYt3LesAzEDbeii9aqgJ7xsww31yWcK9fLBs9l-tvKgR1WsVcAXJ3CNcm8/exec"
)

# ---
# SEZIONE 1: MODELLI DI VALIDAZIONE Pydantic (V2, Completi e Corretti)
# ---


# Funzione helper per validatori di date
def parse_date_field(value: Any) -> Optional[date]:
    if isinstance(value, str) and value.strip():
        # Gestisce formati come 'YYYY-MM-DD' o 'DD/MM/YYYY'
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S.%fZ"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
        raise ValueError(f"Impossibile parsare la data dalla stringa: {value}")
    return None


class CoachUser(BaseModel):
    id: str = Field(..., alias="Coach ID")
    name: str = Field(..., alias="Name")
    surname: str = Field(..., alias="Surname")
    status: str = Field(..., alias="Status")
    email: EmailStr = Field(..., alias="Email")
    phone: Optional[str] = Field(None, alias="Phone")
    role: str = Field(None, alias="Role")
    wise_payment_info: Optional[str] = Field(None, alias="Wise Payment Info")
    password: int = Field(..., alias="Password")
    agreement: Optional[str] = Field(None, alias="Agreement")
    payment_folder: Optional[str] = Field(None, alias="Payment Folder")
    middle_name: Optional[str] = Field(None, alias="Middle Name")
    address: Optional[str] = Field(None, alias="Address")
    citizenship: Optional[str] = Field(None, alias="Citizenship")


class StudentUser(BaseModel):
    id: str = Field(..., alias="Student ID")
    name: str = Field(..., alias="Name")
    surname: str = Field(..., alias="Surname")
    # La password e l'email possono essere vuote per le righe "segnaposto"
    password: Optional[str] = Field(None, alias="Password")
    email: Optional[EmailStr] = Field(None, alias="Email")
    secondary_email: Optional[EmailStr] = Field(None, alias="Secondary Email")
    phone: Optional[str] = Field(None, alias="Phone")
    status: str = Field(..., alias="Status")
    onboarded: bool = Field(False, alias="Onboarded (dashboard)")
    quizlet: Optional[str] = Field(None, alias="Quizlet")
    drive: Optional[str] = Field(None, alias="Drive")
    homework: Optional[str] = Field(None, alias="Homework")
    lesson_plan: Optional[str] = Field(None, alias="Lesson Plan")

    @field_validator("onboarded", mode="before")
    def standardize_onboarded(cls, value):
        return str(value).strip().upper() in ["Y", "YES", "TRUE"]


class ClientUser(BaseModel):
    name: str = Field(..., alias="Company Name")
    id: str = Field(..., alias="Company ID")
    password: int = Field(..., alias="Company Password")


class Product(BaseModel):
    product_id: str = Field(..., alias="Product ID")
    product_name: str = Field(..., alias="Product Name")
    duration: int = Field(..., alias="Duration")
    participants: int = Field(..., alias="Participants")
    head_coach_rate: Optional[Decimal | str] = Field(None, alias="Head Coach")
    senior_coach_rate: Optional[Decimal | str] = Field(None, alias="Senior Coach")
    junior_coach_rate: Optional[Decimal | str] = Field(None, alias="Junior Coach")
    net_after_taxes: Optional[Decimal | str] = Field(None, alias="Net after taxes (€)")
    margin: Optional[Decimal | str] = Field(None, alias="Margin (€)")
    # Questi campi possono essere numerici o stringhe vuote
    sprint_path: Optional[str] = Field(None, alias="Sprint Path")
    smart_path: Optional[str] = Field(None, alias="Smart Path")
    impact_path: Optional[str] = Field(None, alias="Impact Path")

    @field_validator("sprint_path", "smart_path", "impact_path", mode="before")
    def stringify_paths(cls, value):
        return str(value) if value is not None else None


class Contract(BaseModel):
    contract_id: str = Field(..., alias="Contract ID")
    student_id: str = Field(..., alias="Student ID")
    product_id: str = Field(..., alias="Product ID")
    status: str = Field(..., alias="Status")
    unlimited: bool = Field(False, alias="Unlimited")
    invoice_id: str = Field(None, alias="Invoice ID")
    client_id: str = Field(None, alias="Client ID")
    # Questi campi numerici possono essere vuoti
    package: Optional[str] = Field(None, alias="Package")
    total_calls: Optional[int | str] = Field(None, alias="Total Calls")
    calls_per_week: Optional[float | str] = Field(None, alias="Calls/week")
    used_calls: Optional[float | str] = Field(None, alias="Used Calls")
    left_calls: Optional[float | str] = Field(None, alias="Left Calls")
    report_card_cadency: Optional[int | str] = Field(None, alias="Report Card Cadency")
    start_date: Optional[date] = Field(None, alias="Start Date")
    max_end_date: Optional[date] = Field(None, alias="Max End Date")
    report_card_start_month: Optional[date] = Field(None, alias="Report Card Start Date")
    report_card_email_recipients: Optional[str] = Field(None, alias="Report Card Email Recipient(s)")
    report_card_generator_id: Optional[str] = Field(None, alias="report_card_generator_id")

    @field_validator("unlimited", mode="before")
    def standardize_unlimited(cls, value):
        return str(value).strip().upper() in ["Y", "YES", "TRUE"]

    @field_validator("start_date", "max_end_date", mode="before")
    def _parse_date_fields(cls, value):
        return parse_date_field(value)

    @field_validator("report_card_start_month", mode="before")
    def _parse_month_field(cls, value):
        return parse_date_field(value)[:7]


class Tracker(BaseModel):
    session_date: date = Field(..., alias="Date")
    student_id: str = Field(..., alias="Student ID")
    contract_id: str = Field(..., alias="Contract ID")
    coach_id: str = Field(..., alias="Coach ID")
    product_id: str = Field(..., alias="Product ID")
    units: Optional[Decimal | str] = Field(None, alias="Units")
    duration: Optional[int | str] = Field(None, alias="Duration")
    coach_rate: Optional[Decimal | str] = Field(None, alias="Coach Rate")
    prod_cost: Optional[Decimal | str] = Field(None, alias="Prod cost")
    attendance: bool = Field(None, alias="Attendance")
    notes: Optional[str] = Field(None, alias="Notes")

    @field_validator("session_date", mode="before")
    def _parse_date(cls, value):
        return parse_date_field(value)

    @field_validator("attendance", mode="before")
    def standardize_unlimited(cls, value):
        return str(value).strip().upper() in ["YES"]


class Invoice(BaseModel):
    invoice_id: str = Field(..., alias="Invoice ID")
    client_id: str = Field(..., alias="Client ID")
    buyer: Optional[str] = Field(None, alias="Buyer")
    invoice_date: Optional[date | str] = Field(..., alias="Date")
    due_date: Optional[date | str] = Field(..., alias="Due")
    amount: Decimal = Field(..., alias="Amount")
    paid: bool = Field(..., alias="Paid")
    installments: Optional[int | str] = Field(None, alias="Installments")
    email_reminder: Optional[EmailStr] = Field(None, alias="Email Reminder Expired Invoice")

    @field_validator("paid", mode="before")
    def standardize_paid(cls, value):
        return str(value).strip().upper() in ["Y", "YES", "TRUE"]

    @field_validator("invoice_date", "due_date", mode="before")
    def _parse_date_fields(cls, value):
        return parse_date_field(value)


class Debrief(BaseModel):
    debrief_date: date = Field(..., alias="Date")
    coach_id: str = Field(..., alias="Coach ID")
    student_id: str = Field(..., alias="Student ID")
    goals: Optional[str] = Field(None, alias="Goals")
    topics: Optional[str] = Field(None, alias="Topics")
    grammar: Optional[str] = Field(None, alias="Grammar")
    vocabulary: Optional[str] = Field(None, alias="Vocabulary")
    pronunciation: Optional[str] = Field(None, alias="Pronunciation")
    other: Optional[str] = Field(None, alias="Other")
    homework: Optional[str] = Field(None, alias="Homework")
    draft: bool = Field(False, alias="Draft")
    sent: bool = Field(False, alias="Sent")
    sent_date: Optional[date] = Field(None, alias="Sent Date")

    @field_validator("draft", "sent", mode="before")
    def standardize_boolean(cls, value):
        return str(value).strip().upper() in ["Y", "YES", "TRUE"]

    @field_validator("debrief_date", "sent_date", mode="before")
    def _parse_datetime_fields(cls, value):
        return parse_date_field(value)


class ReportCardGenerator(BaseModel):
    report_card_generator_id: str = Field(..., alias="report_card_generator_id")
    student_id: str = Field(..., alias="student_id")
    client_id: str = Field(..., alias="client_id")
    report_card_cadency: int = Field(..., alias="report_card_cadency")
    report_card_email_recipients: str = Field(..., alias="report_card_email_recipients")
    current_start_month: str = Field(..., alias="current_start_month")
    next_start_month: str = Field(..., alias="next_start_month")


class ReportCard(BaseModel):
    student_id: str = Field(..., alias="Student ID")
    coach_id: str = Field(..., alias="Coach ID")
    attendance: Optional[str] = Field(None, alias="Attendance")
    report: Optional[str] = Field(None, alias="Report")
    status: str = Field(..., alias="status")
    report_card_generator_id: str = Field(..., alias="report_card_generator_id")
    report_card_id: str = Field(..., alias="report_card_id")
    report_card_email_recipients: str = Field(..., alias="report_card_email_recipients")
    report_card_cadency: int = Field(..., alias="report_card_cadency")
    start_month: str = Field(..., alias="start_month")
    end_month: str = Field(..., alias="end_month")
    client_id: str = Field(..., alias="client_id")


# ---
# SEZIONE 2: LOGICA DI MIGRAZIONE
# ---


async def fetch_sheet_data(sheet_name: str) -> List[Dict[str, Any]]:
    """Chiama l'API di Apps Script e restituisce i dati, seguendo i reindirizzamenti."""
    logger.info(f"Fetching data for sheet: {sheet_name}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
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


key_map = {
    "Coaches": ["id"],
    "Students": ["id"],
    "Clients": ["id"],
    "Products": ["product_id"],
    "Contracts": ["contract_id"],
    "Tracker": ["contract_id", "session_id"],
    "Invoices": ["invoice_id"],
    "Debriefs": ["student_id", "date"],
    "Report Cards": ["report_card_id", "start_month"],
}

user_class_map = {"Coaches": CoachUser, "Students": StudentUser, "Clients": ClientUser}
user_type_map = {"Coaches": "coach", "Students": "student", "Clients": "company"}


async def migrate_users(db: Any):
    table = await get_table(db, settings.USERS_TABLE)

    for user_type in ["Coaches", "Students", "Clients"]:
        # user_type
        row_index = 2
        for row in await fetch_sheet_data(user_type):
            try:
                # not real error
                if user_type == "Students" and row.get("Password") == "" and row.get("Email") == "":
                    continue
                data = user_class_map[user_type].model_validate(row)
                item = data.model_dump(by_alias=False, exclude={"password"})
                item["user_type"] = user_type_map[user_type]
                item["password_hash"] = hash_password(str(data.password))
                key = None
                if user_type in key_map:
                    key = {k: item[k] for k in key_map[user_type]}
                if key:
                    previous_item_response = await table.get_item(Key=key)
                    previous_item = previous_item_response.get("Item", None)
                    if previous_item:
                        logger.info(f"{user_type}, row_index: {row_index}")
                        logger.info(f"Already inserted overwritten item {user_type}: {previous_item}")
                    await table.put_item(Item=to_dynamodb_item(item))
            except ValidationError as e:
                logger.warning(f"  -> Skipping invalid {user_type} row {row_index}: {e} | Data: {row}")
            row_index += 1


async def get_contract(db, student_id):
    contract_table = await get_table(db, settings.CONTRACTS_TABLE)
    response = await contract_table.query(
        IndexName="student-id-status-index",
        KeyConditionExpression=Key("student_id").eq(student_id),
        Limit=1,
    )
    if "Items" in response and len(response["Items"]) > 0:
        return response["Items"][0]
    else:
        return None


async def get_contract_by_id(db, contract_id):
    contract_table = await get_table(db, settings.CONTRACTS_TABLE)
    response = await contract_table.get_item(Key={"contract_id": contract_id})
    return response["Item"]


async def migrate_generic(db: Any, table_name: str, sheet_name: str, model_cls: BaseModel, special_logic=None):
    table = await get_table(db, table_name)
    row_index = 2
    for row in await fetch_sheet_data(sheet_name):
        try:
            if (
                table_name == settings.INVOICES_TABLE
                and row.get("Invoice ID") in ["", None]
                and row.get("Client ID") in ["", None]
            ):
                continue

            if table_name == settings.DEBRIEFS_TABLE and (
                row.get("Coach ID") in ["", None] or row.get("Student ID") in ["", None]
            ):
                continue

            if table_name == settings.CONTRACTS_TABLE:
                if row["report_card_cadency"] not in ["", None] and isinstance(row["report_card_cadency"], int):
                    row["report_card_generator_id"] = (
                        f"{row['student_id']}#{row['client_id']}#{row['report_card_cadency']}"
                    )
                else:
                    row["report_card_generator_id"] = ""

            if table_name == settings.REPORT_CARDS_TABLE:
                contract_id = row.get("Contract ID")
                contract = None
                if contract_id in ["", None]:
                    # prendere contract_id del primo contract in cui compare row['Student ID']
                    contract = await get_contract(db, row["Student ID"])
                else:
                    contract = await get_contract_by_id(db, contract_id)
                if contract is None:
                    # salta per la migrazione (dati troppo vecchi)
                    continue
                row["client_id"] = contract["client_id"]
                row["report_card_cadency"] = contract["report_card_cadency"]
                row["report_card_email_recipients"] = contract["report_card_email_recipients"]
                row["report_card_generator_id"] = (
                    f"{contract['student_id']}#{row['client_id']}#{row['report_card_cadency']}"
                )
                row["report_card_id"] = f"{row['Coach ID']}#{row['report_card_generator_id']}"
                report_card_start_month = contract["report_card_start_month"]
                row["start_month"] = report_card_start_month
                report_date = parse_date_field(row["Date"])
                while True:
                    if row["start_month"] <= report_date:
                        break
                    else:
                        row["start_month"] = parse_date_field(
                            datetime.fromisoformat(row["start_month"] + "-01").date()
                            + relativedelta(months=row["report_card_cadency"])
                        )[:7]
                row["end_month"] = parse_date_field(
                    datetime.fromisoformat(row["start_month"] + "-01").date()
                    + relativedelta(months=row["report_card_cadency"])
                )[:7]
                if row["Sent"]:
                    row["status"] = "sent"
                else:
                    if row["Status"]:
                        row["status"] = "completed"
                    else:
                        # nella migrazione non esistono no_show
                        row["status"] = "draft"

            data = model_cls.model_validate(row)
            item = to_dynamodb_item(data.model_dump())
            if special_logic:
                item = special_logic(item)
            key = None
            if sheet_name in key_map:
                key = {k: item[k] for k in key_map[sheet_name]}
            if key:
                previous_item_response = await table.get_item(Key=key)
                previous_item = previous_item_response.get("Item", None)
                if previous_item:
                    logger.info(f"{sheet_name}, row_index: {row_index}")
                    logger.info(f"Already inserted overwritten item {sheet_name}: {previous_item}")
            await table.put_item(Item=item)
        except Exception as e:
            logger.warning(f"  -> Skipping invalid {sheet_name} row {row_index}: {e} | Data: {row}")
        row_index += 1


# ---
# SEZIONE 3: FUNZIONE DI CREAZIONE DEI REPORT CARD GENERATOR
# ---
async def introduce_report_card_generators_and_report_cards(db: Any):
    # propagare dati mancanti relativi a report card in contract
    contracts_table = await get_table(db, settings.CONTRACTS_TABLE)

    # contracts with rc
    contracts_response = await contracts_table.query(
        IndexName="client_id-report_card_generator_id-index",
        KeyConditionExpression=Key("client_id").eq("M1A") & Key("report_card_generator_id").gt(""),
    )
    contracts_with_rc = contracts_response["Items"]

    # contracts without rc, active, unlimited or not expired
    contracts_response = await contracts_table.query(
        IndexName="client-id-status-index",
        KeyConditionExpression=Key("client_id").eq("M1A") & Key("status").eq("Active"),
        FilterExpression=(
            Attr("unlimited").eq(True)
            | Attr("max_end_date").not_exists()
            | Attr("max_end_date").gte(get_today_string())
        )
        & Attr("report_card_generator_id").not_exists(),
        ProjectionExpression="contract_id, client_id, student_id",
    )

    contracts_without_rc = contracts_response["Items"]

    contracts_without_rc_df = pd.DataFrame.from_dict(contracts_without_rc)

    for contract_with_rc in contracts_with_rc:
        update_expr = []
        expr_vals = {}
        fields_to_propagates = [
            "report_card_cadency",
            "report_card_start_month",
            "report_card_email_recipients",
            "report_card_generator_id",
        ]
        if not contract_with_rc["unlimited"]:
            fields_to_propagates += ["start_date", "max_end_date"]
        for k, v in contract_with_rc.items():
            if k in fields_to_propagates:
                update_expr.append(f"{k} = :{k}")
                expr_vals[f":{k}"] = v

        for contract_without_rc in contracts_without_rc_df[
            (contracts_without_rc_df["client_id"] == contract_with_rc["client_id"])
            & (contracts_without_rc_df["student_id"] == contract_with_rc["student_id"])
        ].to_dict("records"):
            await contracts_table.update_item(
                Key={"contract_id": contract_without_rc["contract_id"]},
                UpdateExpression="SET " + ", ".join(update_expr),
                ExpressionAttributeValues=expr_vals,
            )

    # creazione report card generators
    contracts_response = await contracts_table.query(
        IndexName="status-index",
        KeyConditionExpression=Key("status").eq("Active"),
        FilterExpression=(
            Attr("unlimited").eq(True)
            | Attr("max_end_date").not_exists()
            | Attr("max_end_date").gte(get_today_string())
        )
        & Attr("report_card_generator_id").exists(),
    )
    contracts = contracts_response["Items"]

    contracts_df = pd.DataFrame.from_dict(contracts)
    report_card_generators_df = (
        contracts_df.groupby("report_card_generator_id")[
            [
                "student_id",
                "client_id",
                "report_card_cadency",
                "report_card_start_month",
                "report_card_email_recipients",
            ]
        ]
        .first()
        .rename(columns={"report_card_start_month": "start_month"})
    )

    report_card_generators_table = await get_table(db, settings.REPORT_CARD_GENERATORS_TABLE)
    today_string = get_today_string()
    for rcg in report_card_generators_df.to_dict("records"):
        rcg["current_start_month"] = rcg["start_month"]
        rcg["next_start_month"] = parse_date_field(
            datetime.fromisoformat(rcg["current_start_month"] + "-01").date()
            + relativedelta(months=rcg["report_card_cadency"])
        )[:7]
        while rcg["next_start_month"] <= today_string:
            rcg["current_start_month"] = rcg["next_start_month"]
            rcg["next_start_month"] = parse_date_field(
                datetime.fromisoformat(rcg["current_start_month"] + "-01").date()
                + relativedelta(months=rcg["report_card_cadency"])
            )[:7]

        data = ReportCardGenerator.model_validate(rcg)
        report_card_generator = to_dynamodb_item(data.model_dump())
        await report_card_generators_table.put_item(Item=report_card_generator)

        # creazione dei report card draft e no show
        report_cards_table = await get_table(db, settings.REPORT_CARDS_TABLE)
        tracker_table = await get_table(db, settings.TRACKER_TABLE)

        # current period
        calls_response = await tracker_table.query(
            IndexName="student-id-date-index",
            KeyConditionExpression=Key("student_id").eq(report_card_generator["student_id"])
            & Key("date").between(
                low_value=report_card_generator["current_start_month"],
                high_value=report_card_generator["next_start_month"],
            ),
            ProjectionExpression="coach_id",
        )
        calls = calls_response.get("Items", [])

        if calls:
            # draft
            calls_df = pd.DataFrame.from_dict(calls)
            for coach_id in calls_df["coach_id"].unique():
                # new report card
                report_card = {}
                report_card["report_card_id"] = f"{coach_id}#{report_card_generator['report_card_generator_id']}"
                report_card["start_month"] = report_card_generator["current_start_month"]
                # report_card["start_month"] = report_card_generator["next_start_month"]
                report_card["end_month"] = (
                    datetime.fromisoformat(report_card["start_month"] + "-01").date()
                    + relativedelta(months=report_card_generator["report_card_cadency"])
                ).strftime("%Y-%m")
                report_card["coach_id"] = coach_id
                report_card["student_id"] = report_card_generator["student_id"]
                report_card["status"] = "draft"
                report_card["report_card_generator_id"] = report_card_generator["report_card_generator_id"]
                report_card["report_card_email_recipients"] = report_card_generator["report_card_email_recipients"]
                report_card["report_card_cadency"] = report_card_generator["report_card_cadency"]
                report_card["client_id"] = report_card_generator["client_id"]
                await report_cards_table.put_item(Item=report_card)
        else:
            # no_show
            # new report card
            report_card = {}
            report_card["report_card_id"] = f"JJ#{report_card_generator['report_card_generator_id']}"
            report_card["start_month"] = report_card_generator["current_start_month"]
            report_card["end_month"] = (
                datetime.fromisoformat(report_card["start_month"] + "-01").date()
                + relativedelta(months=report_card_generator["report_card_cadency"])
            ).strftime("%Y-%m")
            report_card["coach_id"] = "JJ"
            report_card["student_id"] = report_card_generator["student_id"]
            report_card["status"] = "no_show"
            report_card["report_card_generator_id"] = report_card_generator["report_card_generator_id"]
            report_card["report_card_email_recipients"] = report_card_generator["report_card_email_recipients"]
            report_card["report_card_cadency"] = report_card_generator["report_card_cadency"]
            report_card["client_id"] = report_card_generator["client_id"]
            await report_cards_table.put_item(Item=report_card)

        # next period
        calls_response = await tracker_table.query(
            IndexName="student-id-date-index",
            KeyConditionExpression=Key("student_id").eq(report_card_generator["student_id"])
            & Key("date").gt(report_card_generator["next_start_month"]),
            ProjectionExpression="coach_id",
        )
        calls = calls_response.get("Items", [])

        if calls:
            # draft
            calls_df = pd.DataFrame.from_dict(calls)
            for coach_id in calls_df["coach_id"].unique():
                # new report card
                report_card = {}
                report_card["report_card_id"] = f"{coach_id}#{report_card_generator['report_card_generator_id']}"
                report_card["start_month"] = report_card_generator["next_start_month"]
                report_card["end_month"] = (
                    datetime.fromisoformat(report_card["start_month"] + "-01").date()
                    + relativedelta(months=report_card_generator["report_card_cadency"])
                ).strftime("%Y-%m")
                report_card["coach_id"] = coach_id
                report_card["student_id"] = report_card_generator["student_id"]
                report_card["status"] = "draft"
                report_card["report_card_generator_id"] = report_card_generator["report_card_generator_id"]
                report_card["report_card_email_recipients"] = report_card_generator["report_card_email_recipients"]
                report_card["report_card_cadency"] = report_card_generator["report_card_cadency"]
                report_card["client_id"] = report_card_generator["client_id"]
                await report_cards_table.put_item(Item=report_card)


# ---
# SEZIONE 4: FUNZIONE PRINCIPALE DI MIGRAZIONE
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
        item["session_id"] = f"{item['coach_id']}#{item['student_id']}#{item['date']}"
        return item

    logger.info("\n--- Migrating Tracker ---")
    await migrate_generic(db, settings.TRACKER_TABLE, "Tracker", Tracker, special_logic=tracker_logic)

    def invoice_logic(item):
        if "invoice_date" in item:
            item["date"] = item.pop("invoice_date")
        if "due_date" in item:
            item["due"] = item.pop("due_date")
        return item

    logger.info("\n--- Migrating Invoices ---")
    await migrate_generic(db, settings.INVOICES_TABLE, "Invoices", Invoice, special_logic=invoice_logic)

    def debrief_logic(item):
        item["date"] = item.pop("debrief_date")
        item["debrief_id"] = f"{item['student_id']}#{item['coach_id']}"
        return item

    logger.info("\n--- Migrating Debriefs ---")
    await migrate_generic(db, settings.DEBRIEFS_TABLE, "Debriefs", Debrief, special_logic=debrief_logic)

    logger.info("\n--- Migrating Report Cards ---")
    await introduce_report_card_generators_and_report_cards(db)
    await migrate_generic(db, settings.REPORT_CARDS_TABLE, "Report Cards", ReportCard)

    logger.info("DATA MIGRATION COMPLETED.")


# TODO: aggiungere has_debrief alle call che hanno un debrief, fare uno script, che gira a fine migrazione, che prende i debrief e mappa le call corrispondenti
