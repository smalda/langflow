from typing import ClassVar, List

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel

from .base import SequenceItemBase
from .user import UserRole


class HomeworkTask(SequenceItemBase, table=True):
    id_prefix: ClassVar[str] = "hw"

    teacher_id: str = Field(foreign_key="user.id")
    student_ids: List[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String))
    )

    class Config:
        from_attributes = True
