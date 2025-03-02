from typing import ClassVar

from sqlmodel import Field, SQLModel

from .base import SequenceItemBase


class Submission(SequenceItemBase, table=True):
    id_prefix: ClassVar[str] = "sub"

    student_id: str = Field(foreign_key="user.id")
    teacher_id: str = Field(foreign_key="user.id")
    homework_task_id: str = Field(foreign_key="homeworktask.id")

    class Config:
        from_attributes = True
