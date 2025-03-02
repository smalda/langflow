"""
1. `GET /homework/{homework_id}` - Get specific homework
2. `POST /homework/assign/` - Assign new homework
3. `GET /homework/student/{student_id}` - Get all homework for a student
4. `GET /homework/teacher/{teacher_id}` - Get all homework from a teacher
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ...db.base import get_db
from ...queue.notifications import notify_homework_assigned
from ...schemas.base import Status
from ...schemas.homework import HomeworkTask
from ...schemas.submission import Submission
from ...schemas.user import User, UserRole

logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

router = APIRouter()


@router.get("/{homework_id}", response_model=HomeworkTask)
def get_homework_by_id(homework_id: str, db: Session = Depends(get_db)):
    homework = db.get(HomeworkTask, homework_id)
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )
    return homework


@router.post("/assign/", response_model=HomeworkTask)
def assign_homework(homework: HomeworkTask, db: Session = Depends(get_db)):
    try:
        logger.info(f"Assigning homework: {homework}")

        # Special case for AI teacher
        if homework.teacher_id == "usr_ai_teacher":
            logger.info("AI teacher detected, skipping teacher verification")
        else:
            # Verify teacher exists and is actually a teacher
            teacher = db.get(User, homework.teacher_id)
            if not teacher or teacher.role != UserRole.TEACHER:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
                )

        # Verify all students exist
        students = db.exec(
            select(User).where(
                User.id.in_(homework.student_ids), User.role == UserRole.STUDENT
            )
        ).all()

        logger.info(
            f"FFFFFound {len(students)} students, for {len(homework.student_ids)} of the assigned"
        )

        if len(students) != len(homework.student_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more student IDs are invalid",
            )

        logger.info(f"Found {len(students)} students")

        db.add(homework)
        db.commit()
        db.refresh(homework)

        logger.info(f"Assigned homework to {len(students)} students")

        # Notify each student about new homework
        for student in students:
            notify_homework_assigned(
                student_tg_id=student.telegram_id,
                homework_data={
                    "title": homework.content.get("title"),
                    "description": homework.content.get("description"),
                },
            )

        return homework
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/student/{student_id}", response_model=List[HomeworkTask])
def get_student_homework(
    student_id: str,
    homework_status: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    # Verify student exists and is actually a student
    student = db.get(User, student_id)
    if not student or student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    query = select(HomeworkTask).where(HomeworkTask.student_ids.contains([student_id]))

    if homework_status:
        query = query.where(HomeworkTask.status == homework_status)

    homework = db.exec(query.offset(offset).limit(limit)).all()

    return homework


@router.get("/teacher/{teacher_id}", response_model=List[HomeworkTask])
def get_teacher_homework(
    teacher_id: str,
    homework_status: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    # Verify teacher exists and is actually a teacher
    teacher = db.get(User, teacher_id)
    if not teacher or teacher.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
        )

    query = select(HomeworkTask).where(HomeworkTask.teacher_id == teacher_id)

    if homework_status:
        query = query.where(HomeworkTask.status == homework_status)

    homework = db.exec(query.offset(offset).limit(limit)).all()

    return homework


@router.patch("/{homework_id}/status")
def update_homework_status(
    homework_id: str, status: Status, db: Session = Depends(get_db)
):
    homework = db.get(HomeworkTask, homework_id)
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found"
        )

    homework.status = status
    db.commit()
    db.refresh(homework)
    return homework


# @router.get("/by_submission/{submission_id}", response_model=HomeworkTask)
# def get_homework_by_submission_id(
#     submission_id: str,
#     db: Session = Depends(get_db)
# ):
#     # First get the submission to find its homework_task_id
#     submission = db.get(Submission, submission_id)
#     if not submission:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Submission not found"
#         )

#     # Then get the homework task
#     homework = db.get(HomeworkTask, submission.homework_task_id)
#     if not homework:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Homework task not found"
#         )

#     return homework

from pydantic import BaseModel, Field


class HomeworkGenerationModel(BaseModel):
    title: str = Field(..., description="Title of the homework")
    description: str = Field(..., description="The homework task itself")


import os
from typing import Dict, List


class GenerateHomeworkRequest(BaseModel):
    homework_topic: str
    language_level: str
    student_stress_level: str
    chat_context: List[Dict]
    student_id: str = ""


@router.post("/generate/", response_model=Dict)
def generate_homework(request: GenerateHomeworkRequest, db: Session = Depends(get_db)):
    logger.info(f"Received request: {request}")

    topic = request.homework_topic
    language_level = request.language_level
    student_stress_level = request.student_stress_level
    chat_context = request.chat_context
    student_id = request.student_id

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Modify the last user message
    if chat_context and chat_context[-1]["role"] == "user":
        chat_context[-1][
            "content"
        ] = f"{chat_context[-1]['content']}\nPlease generate a homework with these conditions:\nTopic: {topic}\nDifficulty: {language_level}\nMy Stress Level: {student_stress_level}\nGenerate only the homework title and text."

    logger.info(f"Completion: {chat_context}")

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=chat_context,
            response_format=HomeworkGenerationModel,
        )

        logger.info(f"Completion: {completion}")

        description = completion.choices[0].message.parsed.description
        title = completion.choices[0].message.parsed.title

        # Create a HomeworkTask instance
        homework_task = HomeworkTask(
            teacher_id="usr_ai_teacher",
            student_ids=[student_id],
            content={
                "title": title,
                "description": description,
                "language_level": language_level,
                "stress_level": student_stress_level,
                "topic": topic,
            },
        )

        logger.info(f"Parsed all data: {homework_task}")

        # Call assign_homework with the created instance
        result = assign_homework(homework=homework_task, db=db)

        logger.info(f"Assigned: {result.id}")

        return {
            "title": title,
            "description": description,
            "language_level": language_level,
            "stress_level": student_stress_level,
            "topic": topic,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
