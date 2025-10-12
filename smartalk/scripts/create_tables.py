from smartalk.core.dynamodb import get_dynamodb

USERS_TABLE = "Users"
SNAPSHOTS_TABLE = "PortfolioSnapshots"


async def _create_users_table(db) -> None:
    """
    Users:
      - PK: id (S)
      - GSI: email-index (HASH: email)
    Fields (esempi):
      id, email, name, coins (N), ads_seen (N),
      subscription (M: {type, status, renew_at}),
      current_portfolio_snapshot_id (S),            # -> sk SNAPSHOTS_TABLE
      current_sop_snapshot_id (S),                  # -> (Optional) sk SNAPSHOTS_TABLE
      created_at (N)                                # -> User registration date
    """
    await db.create_table(
        TableName=USERS_TABLE,
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


async def _create_snapshots_table(db) -> None:
    """
    PortfolioSnapshots:
      - PK: user_id (S)
      - SK: sk (S)  → formato: "{portfolio_id}##{ts_iso}"
    Esempio Portfolio:
      {
        "user_id": "u_123",
        "sk": "pf_abc##2025-10-08T10:00:00Z",
        "weights": {"USD": 1.0, "AAPL": 0.0, ...},    # max 10 + USD
        "prices": {"USD": 1.0, "AAPL": 172.33, ...},  # prezzi scattati al momento
        "op": "update_weights|add_symbol|remove_symbol|init",
        "sop_impact": 0.45,     # percentuale di impatto di una sop (in funzione di tempo trascorso e similarità di pesi)
        "ttl": 0                # se abiliti TTL
      }
    Query tipica (storia portafoglio corrente):
      KeyCondition: user_id = :uid AND begins_with(sk, :pfIdPrefix)
    Query tipica (portafoglio corrente):
      KeyCondition: user_id = :uid AND sk = :current_portfolio_snapshot_id)

    Esempio Sop:
      {
        "user_id": "u_123",
        "sk": "pf_abc#proposal#2025-10-08T10:00:00Z",
        "weights": {"USD": 1.0, "AAPL": 0.0, ...},    # max 10 + USD
      }
    Query tipica (sop corrente):
      KeyCondition: user_id = :uid AND sk = :current_sop_snapshot_id)
    """
    await db.create_table(
        TableName=SNAPSHOTS_TABLE,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
    )

    # (Opzionale) abilita TTL per scadenza snapshot storici
    client = db.meta.client
    await client.update_time_to_live(
        TableName=SNAPSHOTS_TABLE,
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
    )
    print(f"⏳ TTL enabled on {SNAPSHOTS_TABLE} (attribute: ttl)")


async def create_if_not_exist(db, table_names, table_name, create_function):
    # create table_name if not exists
    if table_name not in table_names:
        print(f"🚀 Creating {table_name} ...")
        await create_function(db)
        print(f"✅ {table_name} created")
    else:
        print(f"✅ {table_name} already exists")


async def ensure_tables() -> None:
    db = await get_dynamodb()
    client = db.meta.client
    resp = await client.list_tables()
    table_names = resp.get("TableNames", [])
    await create_if_not_exist(db, table_names, USERS_TABLE, _create_users_table)
    await create_if_not_exist(db, table_names, SNAPSHOTS_TABLE, _create_snapshots_table)
