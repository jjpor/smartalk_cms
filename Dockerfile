# Usa l'immagine ufficiale di Python 3.11 su base leggera (slim)
FROM python:3.11-slim

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# --------------------------
# Installazione di Poetry
# --------------------------
# Allinea la versione di Poetry a quella usata in locale (2.1.4)
ENV POETRY_VERSION=2.1.4
RUN pip install "poetry==$POETRY_VERSION"

# Configura Poetry per usare l'ambiente del container invece di crearne uno separato
RUN poetry config virtualenvs.create false

# --------------------------
# Installazione delle Dipendenze
# --------------------------
# Copia solo i file necessari per l'installazione delle dipendenze
COPY pyproject.toml poetry.lock ./

# Installa le dipendenze usando Poetry.
# Il flag --no-root impedisce di installare il pacchetto "smartalk_cms" stesso
RUN poetry install --no-root --only main

# --------------------------
# Copia del Codice e Avvio
# --------------------------
# Copia il resto del codice sorgente (smartalk)
COPY smartalk smartalk/

# Espone la porta di Uvicorn
EXPOSE 8000

# Comando di avvio per Uvicorn/FastAPI
# L'host 0.0.0.0 permette l'accesso dall'esterno del container
CMD ["poetry", "run", "uvicorn", "smartalk.app:app", "--host", "0.0.0.0", "--port", "8000"]