from enum import Enum
from typing import ClassVar, Dict, Optional

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel

from .base import TimeStampedModel


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"


class User(TimeStampedModel, table=True):
    id_prefix: ClassVar[str] = "usr"

    tg_handle: str = Field(unique=True, index=True)
    telegram_id: str = Field(unique=True, index=True)  # Numeric Telegram ID

    role: UserRole
    meta: Dict = Field(default_factory=dict, sa_type=JSON)

    class Config:
        from_attributes = True
