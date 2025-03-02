import os
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "LangFlow"
    PROJECT_VERSION: str = "1.0.0"

    # Database settings
    DATABASE_URL: str = Field(default=os.getenv("DATABASE_URL"))
    TEST_DATABASE_URL: str = Field(default="postgresql://localhost/langflow_test")

    # RabbitMQ settings
    RABBITMQ_HOST: str = Field(default=os.getenv("RABBITMQ_HOST", "localhost"))
    RABBITMQ_PORT: int = Field(default=int(os.getenv("RABBITMQ_PORT", "5672")))
    RABBITMQ_USER: str = Field(default=os.getenv("RABBITMQ_USER", "guest"))
    RABBITMQ_PASS: str = Field(default=os.getenv("RABBITMQ_PASS", "guest"))

    # Queue names
    HOMEWORK_QUEUE: str = "homework_queue"
    NOTIFICATION_QUEUE: str = "notification_queue"
    FEEDBACK_QUEUE: str = "feedback_queue"

    # Queue settings
    DEAD_LETTER_EXCHANGE: str = "dlx"
    MESSAGE_TTL: int = Field(default=86400000)  # 24 hours

    # Telegram settings
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=os.getenv("TELEGRAM_BOT_TOKEN"))

    model_config = SettingsConfigDict(frozen=True)

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: Optional[str]) -> str:
        if not v or not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError(
                "Database URL must be a valid PostgreSQL connection string"
            )
        return v

    @field_validator("RABBITMQ_PORT")
    @classmethod
    def validate_port(cls, v: Any) -> int:
        try:
            port = int(v)
            if port < 1 or port > 65535:
                raise ValueError()
            return port
        except (TypeError, ValueError):
            raise ValueError("Port must be a valid number between 1 and 65535")

    @field_validator("MESSAGE_TTL")
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        if not isinstance(v, int) or v <= 0:
            raise ValueError("MESSAGE_TTL must be a positive integer")
        return v

    @field_validator("TELEGRAM_BOT_TOKEN")
    @classmethod
    def validate_telegram_token(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Telegram token cannot be empty if provided")
            if " " in v:  # Additional validation for token format
                raise ValueError("Telegram token cannot contain spaces")
        return v

    def __str__(self) -> str:
        """Hide sensitive information in string representation"""
        settings_dict = self.model_dump()
        # Mask sensitive fields
        for key in ["DATABASE_URL", "TELEGRAM_BOT_TOKEN", "RABBITMQ_PASS"]:
            if key in settings_dict and settings_dict[key]:
                settings_dict[key] = "***"
        return str(settings_dict)


settings = Settings()
