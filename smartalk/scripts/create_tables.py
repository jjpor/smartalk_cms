import logging

from smartalk.core.settings import settings

logger = logging.getLogger("startup")

# -------------------------------------------------
# FUNZIONE HELPER
# -------------------------------------------------

async def create_if_not_exist(db, table_names, table_name, create_function):
    """Controlla se una tabella esiste e, in caso contrario, la crea."""
    logger.info(f"Check on table {table_name}")
    if table_name not in table_names:
        logger.info(f"Creating {table_name} ...")
        await create_function(db, table_name)
        logger.info(f"{table_name} created")
    else:
        logger.info(f"{table_name} already exists")

# -------------------------------------------------
# DEFINIZIONE DELLE TABELLE
# -------------------------------------------------

async def _create_users_table(db, table_name) -> None:
    """Tabella Utenti Unificata (Students, Coaches, Clients)."""
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "user_type", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            },
            {
                "IndexName": "user-type-index",
                "KeySchema": [{"AttributeName": "user_type", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            }
        ],
    )

async def _create_products_table(db, table_name) -> None:
    """Tabella Prodotti/Servizi."""
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "product_id", "AttributeType": "S"}
        ],
    )

async def _create_contracts_table(db, table_name) -> None:
    """Tabella Contratti."""
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "contract_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "contract_id", "AttributeType": "S"},
            {"AttributeName": "student_id", "AttributeType": "S"},
            {"AttributeName": "client_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "student-id-index",
                "KeySchema": [{"AttributeName": "student_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            },
            {
                "IndexName": "client-id-index",
                "KeySchema": [{"AttributeName": "client_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            },
            {
                "IndexName": "status-index",
                "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            },
        ],
    )

async def _create_invoices_table(db, table_name) -> None:
    """Tabella Fatture."""
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "invoice_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "invoice_id", "AttributeType": "S"},
            {"AttributeName": "client_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "client-id-index",
                "KeySchema": [{"AttributeName": "client_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            }
        ],
    )

async def _create_tracker_table(db, table_name) -> None:
    """
    Tabella Tracker (tracciamento sessioni).
    - PK (composita): contract_id (HASH) + session_id (RANGE)
    - La Sort Key 'session_id' è una chiave composita (es. "STUDENT_ID#ISO_DATE")
      per garantire l'unicità di ogni sessione, anche in lezioni di gruppo.
    - I GSI servono per access patterns alternativi (query per studente o per coach).
    """
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "contract_id", "KeyType": "HASH"},
            {"AttributeName": "session_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "contract_id", "AttributeType": "S"},
            {"AttributeName": "session_id", "AttributeType": "S"},
            {"AttributeName": "student_id", "AttributeType": "S"},
            {"AttributeName": "coach_id", "AttributeType": "S"},
            {"AttributeName": "date", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "student-id-date-index",
                "KeySchema": [
                    {"AttributeName": "student_id", "KeyType": "HASH"},
                    {"AttributeName": "date", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            },
            {
                "IndexName": "coach-id-date-index",
                "KeySchema": [
                    {"AttributeName": "coach_id", "KeyType": "HASH"},
                    {"AttributeName": "date", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            },
        ],
    )

async def _create_report_cards_table(db, table_name) -> None:
    """Tabella Report Cards (pagelle)."""
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "contract_id", "KeyType": "HASH"},
            {"AttributeName": "date", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "contract_id", "AttributeType": "S"},
            {"AttributeName": "date", "AttributeType": "S"},
            {"AttributeName": "student_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "student-id-date-index",
                "KeySchema": [
                    {"AttributeName": "student_id", "KeyType": "HASH"},
                    {"AttributeName": "date", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            }
        ],
    )

async def _create_debriefs_table(db, table_name) -> None:
    """Tabella Debriefs (note post-sessione)."""
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "student_id", "KeyType": "HASH"},
            {"AttributeName": "date", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "student_id", "AttributeType": "S"},
            {"AttributeName": "date", "AttributeType": "S"},
            {"AttributeName": "coach_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "coach-id-date-index",
                "KeySchema": [
                    {"AttributeName": "coach_id", "KeyType": "HASH"},
                    {"AttributeName": "date", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            }
        ],
    )

# -------------------------------------------------
# FUNZIONE PRINCIPALE
# -------------------------------------------------

async def ensure_tables(db) -> None:
    """Orchestra la creazione di tutte le tabelle necessarie."""
    try:
        response = await db.list_tables()
        table_names = response.get("TableNames", [])
        logger.info(f"Existing tables: {table_names}")

        tables_to_create = {
            settings.USERS_TABLE: _create_users_table,
            settings.PRODUCTS_TABLE: _create_products_table,
            settings.CONTRACTS_TABLE: _create_contracts_table,
            settings.INVOICES_TABLE: _create_invoices_table,
            settings.TRACKER_TABLE: _create_tracker_table,
            settings.REPORT_CARDS_TABLE: _create_report_cards_table,
            settings.DEBRIEFS_TABLE: _create_debriefs_table,
        }

        for table_name, create_func in tables_to_create.items():
            await create_if_not_exist(db, table_names, table_name, create_func)

    except Exception as e:
        logger.error(f"Error ensuring tables: {e}", exc_info=True)
        raise