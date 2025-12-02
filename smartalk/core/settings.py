from pydantic import EmailStr
from pydantic_settings import BaseSettings


class settings(BaseSettings):
    # Email
    SENDER: EmailStr

    # DynamoDB
    AWS_REGION: str
    DYNAMO_ENDPOINT: str | None = None
    AWS_ACCESS_KEY_ID: str | None = "dummy"
    AWS_SECRET_ACCESS_KEY: str | None = "dummy"

    # Tables
    USERS_TABLE: str
    PRODUCTS_TABLE: str
    CONTRACTS_TABLE: str
    INVOICES_TABLE: str
    TRACKER_TABLE: str
    REPORT_CARDS_TABLE: str
    REPORT_CARD_GENERATORS_TABLE: str
    DEBRIEFS_TABLE: str
    COMPANY_EMPLOYEES_TABLE: str
    BOOKING_CALLS_TABLE: str

    # JWT
    JWT_SECRET: str
    JWT_ALG: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GMAIL_TOKEN_JSON: str
    CALENDAR_SERVICE: str

    # --- Variabili per la migrazione ---
    # Impostare a 'True' nel file .env solo per il primo avvio
    RUN_DATA_MIGRATION: bool = False
    RUN_INIT_CALENDARS: bool = False
    LOCAL_ENDPOINT: str

    # Startup
    INTERNAL_STARTUP_KEY: str

    # Scheduler
    # su cron-job.org impostare Header: X-CRON-SECRET: CRON_SECRET
    CRON_SECRET: str

    # real time calendar sync
    CALENDAR_SYNC_TABLE: str
    CALENDAR_SYNC_WEBHOOK_URL: str

    class Config:
        env_file = ".env"


settings = settings()
