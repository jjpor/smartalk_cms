import inspect
import json
import os

import boto3

from smartalk.core.settings import settings

LOCAL_ENDPOINT = settings.DYNAMO_ENDPOINT or "http://localhost:8000"


def _extract_table_names():
    """
    Estrae automaticamente tutte le tabelle definite nella sezione
    '# Tables' del file settings.py.

    Funziona leggendo l'ordine dei campi in settings.__fields__ e
    prendendo tutto ciò che viene dopo il commento '# Tables' e prima
    della prossima sezione (JWT, Google OAuth, Scheduler ecc.).
    """
    source = inspect.getsource(settings.__class__)
    lines = source.splitlines()

    # 1) Trova posizione "# Tables"
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("# Tables"):
            start_idx = i
            break
    if start_idx is None:
        raise RuntimeError("Non trovo la sezione '# Tables' in settings.py")

    # 2) Raccoglie i nomi delle variabili fino alla prossima riga vuota
    table_vars = []
    for line in lines[start_idx + 1 :]:
        if not line.strip():
            break  # finito blocco tabelle
        if ":" in line:  # riga tipo: USERS_TABLE: str
            var_name = line.strip().split(":")[0]
            table_vars.append(var_name)

    # 3) Converti nomi variabili → valori reali
    #    (es. USERS_TABLE → "smartalk-users")
    actual_table_names = [getattr(settings, var) for var in table_vars]

    return actual_table_names


def export_local(table_names):
    """
    Esporta tutte le tabelle locali in /dumps/<table>.json
    """
    os.makedirs("dumps", exist_ok=True)
    ddb = boto3.resource(
        "dynamodb",
        endpoint_url=LOCAL_ENDPOINT,
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    print("\n=== EXPORT DA DYNAMODB LOCALE ===")

    for table_name in table_names:
        if table_name == settings.CALENDAR_SYNC_TABLE:
            print(f"SKIP {table_name} (calendar_sync non va importata)")
            continue

        table = ddb.Table(table_name)
        print(f"→ Esporto {table_name} ...")

        items = []
        scan_kwargs = {}
        while True:
            resp = table.scan(**scan_kwargs)
            items.extend(resp.get("Items", []))
            if "LastEvaluatedKey" in resp:
                scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
            else:
                break

        with open(f"dumps/{table_name}.json", "w") as f:
            json.dump(items, f)

        print(f"  ✔ {len(items)} items salvati")


def import_to_aws(table_names):
    """
    Importa da /dumps/*.json nel DynamoDB AWS.
    """
    ddb = boto3.resource(
        "dynamodb",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    print("\n=== IMPORT SU AWS DYNAMODB ===")

    for table_name in table_names:
        if table_name == settings.CALENDAR_SYNC_TABLE:
            print(f"SKIP {table_name} (calendar_sync deve restare vuota)")
            continue

        path = f"dumps/{table_name}.json"
        if not os.path.exists(path):
            print(f"✖ File mancante per {table_name}, salto.")
            continue

        table = ddb.Table(table_name)
        print(f"→ Importo {table_name} ...")

        items = json.load(open(path))

        for item in items:
            table.put_item(Item=item)

        print(f"  ✔ {len(items)} items importati")


def main():
    table_names = _extract_table_names()

    print("\nTabelle individuate automaticamente:")
    for t in table_names:
        print(" -", t)

    export_local(table_names)
    import_to_aws(table_names)

    print("\n=== COMPLETATO ===\n")


if __name__ == "__main__":
    main()
