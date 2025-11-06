import logging

from smartalk.core.settings import settings

logger = logging.getLogger("startup")

########### TIPI DI DATO ##############
# S: String
# N: Number
# B: binario
# BOOL: Boolean
# NULL: null
# M: Map
# L: list
# SS: set string
# NS: set numerico
# BS: set binario
#######################################

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
            },
        ],
    )


async def _create_products_table(db, table_name) -> None:
    """Tabella Prodotti/Servizi."""
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "product_id", "AttributeType": "S"}],
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
            {"AttributeName": "report_card_cadency", "AttributeType": "N"},
            {"AttributeName": "report_card_start_month", "AttributeType": "S"},
            {"AttributeName": "report_card_generator_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "student-id-status-index",
                "KeySchema": [
                    {"AttributeName": "student_id", "KeyType": "HASH"},
                    {"AttributeName": "status", "KeyType": "RANGE"},
                ],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["left_calls", "used_calls", "max_end_date", "product_id"],
                },
            },
            {
                "IndexName": "client-id-status-index",
                "KeySchema": [
                    {"AttributeName": "client_id", "KeyType": "HASH"},
                    {"AttributeName": "status", "KeyType": "RANGE"},
                ],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["product_id", "student_id"],
                },
            },
            {
                "IndexName": "client-id-product-id-index",
                "KeySchema": [
                    {"AttributeName": "client_id", "KeyType": "HASH"},
                    {"AttributeName": "product_id", "KeyType": "RANGE"},
                ],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["status", "student_id"],
                },
            },
            {
                "IndexName": "report-card-cadency-report-card-start-month-index",
                "KeySchema": [
                    {"AttributeName": "report_card_cadency", "KeyType": "HASH"},
                    {"AttributeName": "report_card_start_month", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "report_card_generator_id-index",
                "KeySchema": [{"AttributeName": "report_card_generator_id", "KeyType": "HASH"}],
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
    - La Sort Key 'session_id' è una chiave composita (es. "COACH_ID#STUDENT_ID#ISO_DATE")
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
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["date", "product_id", "coach_id", "duration", "attendance", "notes"],
                },
            },
            {
                "IndexName": "coach-id-date-index",
                "KeySchema": [
                    {"AttributeName": "coach_id", "KeyType": "HASH"},
                    {"AttributeName": "date", "KeyType": "RANGE"},
                ],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["date", "student_id", "product_id", "coach_rate"],
                },
            },
        ],
    )


async def _create_report_card_generators_table(db, table_name) -> None:
    """Tabella Report Cards (pagelle).
    report_card_generator_id=student_id#client_id#report_card_cadency
        (es: ABC.XYZ#COMPANY_ID#1)
    """
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "report_card_generator_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "report_card_generator_id", "AttributeType": "S"},
        ],
    )


async def _create_report_cards_table(db, table_name) -> None:
    """Tabella Report Cards (pagelle).
    report_card_id=coach_id#report_card_generator_id
    start_month (es.: 2025-10)

    (student_id per il momento è implicito in report_card_generator_id)
    (quando esiste solo il no show report card, allora coach_id è l'id del coach con role "Head Coach")
    """
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "report_card_id", "KeyType": "HASH"},
            {"AttributeName": "start_month", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "report_card_id", "AttributeType": "S"},
            {"AttributeName": "coach_id", "AttributeType": "S"},
            {"AttributeName": "start_month", "AttributeType": "S"},
            {"AttributeName": "report_card_generator_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            # per vedere i completati di un periodo
            {
                "IndexName": "status-start-month-index",
                "KeySchema": [
                    {"AttributeName": "status", "KeyType": "HASH"},
                    {"AttributeName": "start_month", "KeyType": "RANGE"},
                ],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["end_month", "student_id", "coach_id"],
                },
            },
            # per editare da un coach le draft (o i no show)
            {
                "IndexName": "coach-id-status-index",
                "KeySchema": [
                    {"AttributeName": "coach_id", "KeyType": "HASH"},
                    {"AttributeName": "status", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            # per capire se esiste un report card di un altro coach
            {
                "IndexName": "report-card-generator-id-start-month-index",
                "KeySchema": [
                    {"AttributeName": "report_card_generator_id", "KeyType": "HASH"},
                    {"AttributeName": "start_month", "KeyType": "RANGE"},
                ],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["end_month", "coach_id"],
                },
            },
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
        client = db.meta.client
        response = await client.list_tables()
        table_names = response.get("TableNames", [])
        logger.info(f"Existing tables: {table_names}")

        tables_to_create = {
            settings.USERS_TABLE: _create_users_table,
            settings.PRODUCTS_TABLE: _create_products_table,
            settings.CONTRACTS_TABLE: _create_contracts_table,
            settings.INVOICES_TABLE: _create_invoices_table,
            settings.TRACKER_TABLE: _create_tracker_table,
            settings.REPORT_CARD_GENERATORS_TABLE: _create_report_card_generators_table,
            settings.REPORT_CARDS_TABLE: _create_report_cards_table,
            settings.DEBRIEFS_TABLE: _create_debriefs_table,
        }

        for table_name, create_func in tables_to_create.items():
            await create_if_not_exist(db, table_names, table_name, create_func)

    except Exception as e:
        logger.error(f"Error ensuring tables: {e}", exc_info=True)
        raise
