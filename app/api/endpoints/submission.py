"""
1. `GET /submissions/{submission_id}` - Get specific submission
2. `POST /submissions/` - Create new submission
3. `GET /submissions/student/{student_id}` - Get all submissions from a student
4. `GET /submissions/teacher/{teacher_id}` - Get all submissions for a teacher
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ...db.base import get_db
from ...queue.notifications import notify_submission_received
from ...schemas.base import Status
from ...schemas.homework import HomeworkTask
from ...schemas.submission import Submission
from ...schemas.user import User, UserRole

router = APIRouter()


@router.get("/{submission_id}", response_model=Submission)
def get_submission_by_id(submission_id: str, db: Session = Depends(get_db)):
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )
    return submission


@router.post("/", response_model=Submission)
def create_submission(submission: Submission, db: Session = Depends(get_db)):
    # Verify student exists and is actually a student
    student = db.get(User, submission.student_id)
    if not student or student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    # Verify homework exists and student is assigned to it
    homework = db.get(HomeworkTask, submission.homework_task_id)
    if not homework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Homework task not found"
        )

    # Add validation for cancelled homework
    if homework.status == Status.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit to cancelled homework",
        )

    if submission.student_id not in homework.student_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student is not assigned to this homework",
        )

    # Verify that teacher_id matches homework's teacher
    if submission.teacher_id != homework.teacher_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teacher ID doesn't match homework's teacher",
        )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Get teacher info and notify about new submission
    teacher = db.get(User, submission.teacher_id)
    notify_submission_received(
        teacher_tg_id=teacher.telegram_id,
        submission_data={
            "student_name": student.tg_handle,
            "homework_title": homework.content.get("title", "Untitled"),
            "submission_id": submission.id,
            "content_preview": (
                submission.content.get("text", "")[:100] + "..."
                if len(submission.content.get("text", "")) > 100
                else submission.content.get("text", "")
            ),
        },
    )

    return submission


@router.get("/student/{student_id}", response_model=List[Submission])
def get_student_submissions(
    student_id: str,
    submission_status: Optional[str] = None,
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

    query = select(Submission).where(Submission.student_id == student_id)

    if submission_status:
        query = query.where(Submission.status == submission_status)

    submissions = db.exec(query.offset(offset).limit(limit)).all()

    return submissions


@router.get("/teacher/{teacher_id}", response_model=List[Submission])
def get_teacher_submissions(
    teacher_id: str,
    submission_status: Optional[str] = None,
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

    query = select(Submission).where(Submission.teacher_id == teacher_id)

    if submission_status:
        query = query.where(Submission.status == submission_status)

    submissions = db.exec(query.offset(offset).limit(limit)).all()

    return submissions
