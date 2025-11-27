#!/usr/bin/env python3
"""
Script completo:
1. Avvia automaticamente Ngrok (se non già attivo)
2. Legge il tunnel HTTPS da localhost:4040
3. Aggiorna il file .env con CALENDAR_SYNC_WEBHOOK_URL
4. Mantiene intatta la struttura del file

Uso:
    poetry run python scripts/start_ngrok_and_update_env.py
"""

import os
import subprocess
import time
from pathlib import Path

import requests

NGROK_API = "http://127.0.0.1:4040/api/tunnels"
ENV_FILE = Path(".env")


def is_ngrok_running() -> bool:
    """Controlla se Ngrok è già attivo."""
    try:
        requests.get(NGROK_API, timeout=1)
        return True
    except Exception:
        return False


def start_ngrok(port: int = 8001):
    """Avvia ngrok http <port> in background."""
    print(f"🚀 Avvio Ngrok tunnel sulla porta {port}...")

    # avvia ngrok in background, senza bloccare
    process = subprocess.Popen(
        ["ngrok", "http", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    # attende che l'API 4040 si avvii
    for _ in range(30):
        if is_ngrok_running():
            print(f"🚀 Ngrok avviato (PID {process.pid})")
            return
        time.sleep(0.5)

    raise RuntimeError("❌ Ngrok non è partito correttamente")


def get_ngrok_url() -> str:
    """Ritorna la prima URL https del tunnel Ngrok."""
    res = requests.get(NGROK_API)
    tunnels = res.json().get("tunnels", [])
    for t in tunnels:
        if t.get("proto") == "https":
            return t["public_url"]
    raise RuntimeError("❌ Nessun tunnel HTTPS trovato.")


def update_env(ngrok_url: str):
    """Aggiorna CALENDAR_SYNC_WEBHOOK_URL nel .env mantenendo la struttura."""
    if not ENV_FILE.exists():
        raise FileNotFoundError(".env non trovato!")

    new_line = f"CALENDAR_SYNC_WEBHOOK_URL={ngrok_url}/calendar-sync/callback\n"

    updated = False
    content = []

    with ENV_FILE.open("r", encoding="utf-8") as f:
        for line in f.readlines():
            if line.startswith("CALENDAR_SYNC_WEBHOOK_URL="):
                content.append(new_line)
                updated = True
            else:
                content.append(line)

    if not updated:
        content.append("\n" + new_line)

    with ENV_FILE.open("w", encoding="utf-8") as f:
        f.writelines(content)

    return new_line.strip()


def main():
    print("\n=== SMARTALK NGROK AUTO-SETUP ===\n")

    # 1. avvia ngrok se necessario
    pid = None
    if not is_ngrok_running():
        start_ngrok()
    else:
        print("ℹ️  Ngrok è già in esecuzione.")

    # 2. ottieni URL
    print("\n🔍 Recupero URL pubblica Ngrok...")
    url = get_ngrok_url()
    print(f"   ➜ {url}")

    # 3. aggiorna .env
    print("\n📝 Aggiornamento .env...")
    final_line = update_env(url)
    print(f"   ➜ {final_line}")

    print("\n🎉 FATTO!")
    print("   Ora puoi avviare il backend e Google Calendar riceverà i webhook.\n")


if __name__ == "__main__":
    main()
