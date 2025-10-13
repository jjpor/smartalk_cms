# Smartals CMS
CMS for Smartlak

# Uso di poetry

## 1. Entra nella cartella del progetto
cd <nome-cartella-progetto>

## 2. Configura Poetry per creare l'ambiente virtuale nel progetto
poetry config virtualenvs.in-project true

## 3. Usa Python 3.11 per il progetto
poetry init
poetry env use python3.11
(su win: poetry env use 3.11)

## 4. Installa le dipendenze del progetto
poetry install

## 5. Verifica la versione di Python usata nel venv
poetry run python --version

# Da ora in poi, per lanciare comandi nel progetto:
#   poetry run <comando>
# Esempio:
poetry run uvicorn smartalk.app:app --reload
poetry run uvicorn smartalk.app:app --host localhost --port 8000 --reload

## Docker

docker compose up --build
docker compose down

## git
git config core.autocrlf input