from pydantic import BaseSettings


class Settings(BaseSettings):
    # DynamoDB
    AWS_REGION: str
    DYNAMO_ENDPOINT: str | None = None
    AWS_ACCESS_KEY_ID: str | None = "dummy"
    AWS_SECRET_ACCESS_KEY: str | None = "dummy"

    # JWT
    JWT_SECRET: str
    JWT_ALG: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str

    class Config:
        env_file = ".env"


settings = Settings()
