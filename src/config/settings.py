from pydantic_settings import BaseSettings
from pydantic import Field
import os
import base64

class Settings(BaseSettings):
    POSTGRES_USER: str = Field(...)
    POSTGRES_PASSWORD: str = Field(...)
    POSTGRES_HOST: str = Field(...)
    POSTGRES_DB_PORT: int = Field(...)
    POSTGRES_DB: str = Field(...)

    SECRET_KEY_ACCESS: str = Field(
        default_factory=lambda: base64.urlsafe_b64encode(os.urandom(32)).decode()
    )
    SECRET_KEY_REFRESH: str = Field(
        default_factory=lambda: base64.urlsafe_b64encode(os.urandom(32)).decode()
    )
    JWT_SIGNING_ALGORITHM: str = Field("HS256")

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

def get_settings() -> Settings:
    return Settings()
