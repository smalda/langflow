from typing import ClassVar

from sqlmodel import Field, SQLModel

from .base import SequenceItemBase


class Feedback(SequenceItemBase, table=True):
    id_prefix: ClassVar[str] = "fb"

    student_id: str = Field(foreign_key="user.id")
    teacher_id: str = Field(foreign_key="user.id")
    submission_id: str = Field(foreign_key="submission.id")

    class Config:
        from_attributes = True
