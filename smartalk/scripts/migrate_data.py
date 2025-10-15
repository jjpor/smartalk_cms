import logging
import os
import sys
from decimal import Decimal
from typing import Any, Dict, List

import httpx

# Permette allo script di trovare i moduli del progetto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartalk.core.settings import settings
from smartalk.db_usage.dynamodb_auth import hash_password

# --- CONFIGURAZIONE ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")
logger = logging.getLogger("data_migration")

# URL del tuo Apps Script
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbw-AkO87R7aTse1Ph-Glrzd6DGg_Gak-3dFjqHuXb4ecjUBp5CU5SfCI66eaPwUkumN/exec"

# --- FUNZIONI HELPER ---

def clean_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pulisce un item prima di inserirlo in DynamoDB:
    - Rimuove chiavi con valori vuoti (es. '' o None).
    - Converte i numeri in formato Decimal, che è richiesto da DynamoDB.
    """
    cleaned = {}
    for k, v in item.items():
        if v is not None and v != "":
            try:
                # Prova a convertire stringhe che rappresentano numeri
                cleaned[k] = Decimal(str(v))
            except (ValueError, TypeError):
                # Altrimenti, tieni il valore originale (stringa, booleano, etc.)
                cleaned[k] = v
    return cleaned

async def fetch_sheet_data(sheet_name: str) -> List[Dict[str, Any]]:
    """Chiama l'API di Apps Script e restituisce i dati."""
    logger.info(f"Fetching data for sheet: {sheet_name}...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{APPS_SCRIPT_URL}?sheet={sheet_name}", timeout=120.0)
            response.raise_for_status()
            json_data = response.json()
            if json_data.get("success"):
                data = json_data.get("data", [])
                logger.info(f"  -> Fetched {len(data)} rows from {sheet_name}.")
                return data
            else:
                logger.error(f"  -> API Error from Apps Script for {sheet_name}: {json_data.get('error')}")
                return []
        except httpx.RequestError as e:
            logger.error(f"  -> Network error calling API for {sheet_name}: {e}")
            return []

# --- FUNZIONI DI MIGRAZIONE ---

async def migrate_users(db: Any):
    """Migra Coaches, Students e Clients nella tabella USERS."""
    table = await db.Table(settings.USERS_TABLE)
    logger.info(f"\n--- Migrating Users to {settings.USERS_TABLE} ---")

    # Migrazione Coaches
    for row in await fetch_sheet_data("Coaches"):
        item = {
            "id": row.get("Coach ID"), "user_type": "coach", "name": row.get("Name"),
            "surname": row.get("Surname"), "email": (row.get("Email") or "").lower(),
            "status": row.get("Status"), "password_hash": hash_password(row.get("Password", "")),
            "role": row.get("Role")
        }
        await table.put_item(Item=clean_item(item))
        logger.info(f"  -> Migrated coach: {item['id']}")

    # Migrazione Students
    for row in await fetch_sheet_data("Students"):
        item = {
            "id": row.get("Student ID"), "user_type": "student", "name": row.get("Name"),
            "surname": row.get("Surname"), "email": (row.get("Email") or "").lower(),
            "status": row.get("Status"), "password_hash": hash_password(row.get("Password", "")),
        }
        await table.put_item(Item=clean_item(item))
        logger.info(f"  -> Migrated student: {item['id']}")

    # Migrazione Clients
    for row in await fetch_sheet_data("Clients"):
        item = {
            "id": row.get("Client ID"), "user_type": "client",
            "name": row.get("Company Name"), # Per i clienti, 'name' è il nome dell'azienda
            "password_hash": hash_password(row.get("Password", ""))
        }
        await table.put_item(Item=clean_item(item))
        logger.info(f"  -> Migrated client: {item['id']}")

async def migrate_products(db: Any):
    """Migra i Prodotti."""
    table = await db.Table(settings.PRODUCTS_TABLE)
    logger.info(f"\n--- Migrating Products to {settings.PRODUCTS_TABLE} ---")
    for row in await fetch_sheet_data("Products"):
        item = {
            "product_id": row.get("Product ID"), "product_name": row.get("Product Name"),
            "duration": row.get("Duration"), "participants": row.get("Participants"),
            "Head Coach": row.get("Head Coach"), "Senior Coach": row.get("Senior Coach"),
            "Junior Coach": row.get("Junior Coach"),
        }
        await table.put_item(Item=clean_item(item))
        logger.info(f"  -> Migrated product: {item['product_id']}")

async def migrate_contracts(db: Any):
    """Migra i Contratti."""
    table = await db.Table(settings.CONTRACTS_TABLE)
    logger.info(f"\n--- Migrating Contracts to {settings.CONTRACTS_TABLE} ---")
    for row in await fetch_sheet_data("Contracts"):
        item = row.copy() # Copia tutti i campi
        # Rinomina le chiavi per coerenza con DynamoDB (opzionale ma consigliato)
        item["contract_id"] = item.pop("Contract ID", None)
        item["student_id"] = item.pop("Student ID", None)
        item["client_id"] = item.pop("Client ID", None)
        item["product_id"] = item.pop("Product ID", None)
        item["status"] = item.pop("Status", None)
        item["unlimited"] = str(item.pop("Unlimited", "N")).upper() == "Y"

        await table.put_item(Item=clean_item(item))
        logger.info(f"  -> Migrated contract: {item['contract_id']}")

async def migrate_tracker(db: Any):
    """Migra il Tracker delle sessioni."""
    table = await db.Table(settings.TRACKER_TABLE)
    logger.info(f"\n--- Migrating Tracker to {settings.TRACKER_TABLE} ---")
    for row in await fetch_sheet_data("Tracker"):
        student_id = row.get("Student ID")
        date_str = row.get("Date") # Assumiamo formato YYYY-MM-DD
        if not student_id or not date_str:
            continue
            
        item = row.copy()
        item["contract_id"] = item.pop("Contract ID", None)
        item["student_id"] = student_id
        item["coach_id"] = item.pop("Coach ID", None)
        item["product_id"] = item.pop("Product ID", None)
        item["date"] = date_str
        # Crea la chiave composita per l'unicità
        item["session_id"] = f"{student_id}#{date_str}"

        await table.put_item(Item=clean_item(item))
        logger.info(f"  -> Migrated tracker entry: {item['session_id']}")


# --- FUNZIONE PRINCIPALE ---

async def migrate_all_data(db):
    """Esegue la migrazione completa dei dati da Google Sheets a DynamoDB."""
    logger.info("AVVIO MIGRAZIONE DATI DA GOOGLE SHEETS API...")
    await migrate_users(db)
    await migrate_products(db)
    await migrate_contracts(db)
    await migrate_tracker(db)
    # Aggiungi qui le chiamate per migrare le altre tabelle (Debriefs, Report Cards, etc.)
    # Esempio: await migrate_debriefs(db)
    logger.info("MIGRAZIONE COMPLETATA.")