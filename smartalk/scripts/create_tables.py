import logging

from smartalk.core.settings import settings

logger = logging.getLogger("startup")


async def _create_users_table(db, table_name) -> None:
    """
    Users:
      - PK: id (S)
      - GSI: email-index (HASH: email)
    Fields (esempi):
      id, email, name, created_at
      name (S)
      created_at (N)       # -> User registration / creation date
    """
    await db.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            }
        ],
    )


async def create_if_not_exist(db, table_names, table_name, create_function):
    # create table_name if not exists
    logger.info(f"Check on table {table_name}")
    if table_name not in table_names:
        logger.info(f"Creating {table_name} ...")
        await create_function(db, table_name)
        logger.info(f"{table_name} created")
    else:
        logger.info(f"{table_name} already exists")


async def ensure_tables(db) -> None:
    client = db.meta.client
    resp = await client.list_tables()
    table_names = resp.get("TableNames", [])
    # List here table creation, checking existence or create it
    await create_if_not_exist(db, table_names, settings.USERS_TABLE, _create_users_table)
