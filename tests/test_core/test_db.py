"""
1. Basic CRUD operations for all models
2. Relationship testing between models
3. Query operations
4. Timestamp functionality
5. Unique constraints
6. Multiple record handling
7. Status handling
8. Foreign key relationships
"""

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.schemas.base import Status
from app.schemas.feedback import Feedback
from app.schemas.homework import HomeworkTask
from app.schemas.submission import Submission
from app.schemas.user import User, UserRole


def test_create_user(session: Session):
    # Given
    user = User(tg_handle="test_user", telegram_id="123456789", role=UserRole.STUDENT)

    # When
    session.add(user)
    session.commit()
    session.refresh(user)

    # Then
    assert user.id is not None
    assert user.tg_handle == "test_user"
    assert user.telegram_id == "123456789"
    assert user.role == UserRole.STUDENT


def test_create_homework(session: Session):
    # Given
    teacher = User(
        tg_handle="test_teacher", telegram_id="987654321", role=UserRole.TEACHER
    )
    session.add(teacher)
    session.commit()

    homework = HomeworkTask(
        teacher_id=teacher.id,
        student_ids=["student1", "student2"],
        content={"title": "Test Homework"},
    )

    # When
    session.add(homework)
    session.commit()
    session.refresh(homework)

    # Then
    assert homework.id is not None
    assert homework.teacher_id == teacher.id
    assert homework.content["title"] == "Test Homework"
    assert len(homework.student_ids) == 2


def test_create_submission(session: Session):
    # Given
    teacher = User(
        tg_handle="submission_teacher", telegram_id="111222333", role=UserRole.TEACHER
    )
    student = User(
        tg_handle="submission_student", telegram_id="333222111", role=UserRole.STUDENT
    )
    session.add(teacher)
    session.add(student)
    session.commit()

    homework = HomeworkTask(
        teacher_id=teacher.id,
        student_ids=[student.id],
        content={"title": "Submission Test Homework"},
    )
    session.add(homework)
    session.commit()

    submission = Submission(
        student_id=student.id,
        teacher_id=teacher.id,
        homework_task_id=homework.id,
        content={"text": "Test submission content"},
        status=Status.PENDING,
    )

    # When
    session.add(submission)
    session.commit()
    session.refresh(submission)

    # Then
    assert submission.id is not None
    assert submission.student_id == student.id
    assert submission.homework_task_id == homework.id
    assert submission.content["text"] == "Test submission content"
    assert submission.status == Status.PENDING


def test_create_feedback(session: Session):
    # Given
    teacher = User(
        tg_handle="feedback_teacher", telegram_id="444555666", role=UserRole.TEACHER
    )
    student = User(
        tg_handle="feedback_student", telegram_id="666555444", role=UserRole.STUDENT
    )
    session.add(teacher)
    session.add(student)
    session.commit()

    homework = HomeworkTask(
        teacher_id=teacher.id,
        student_ids=[student.id],
        content={"title": "Feedback Test Homework"},
    )
    session.add(homework)
    session.commit()

    submission = Submission(
        student_id=student.id,
        teacher_id=teacher.id,
        homework_task_id=homework.id,
        content={"text": "Submission for feedback"},
    )
    session.add(submission)
    session.commit()

    feedback = Feedback(
        student_id=student.id,
        teacher_id=teacher.id,
        submission_id=submission.id,
        content={"text": "Great work!"},
        status=Status.COMPLETED,
    )

    # When
    session.add(feedback)
    session.commit()
    session.refresh(feedback)

    # Then
    assert feedback.id is not None
    assert feedback.student_id == student.id
    assert feedback.submission_id == submission.id
    assert feedback.content["text"] == "Great work!"
    assert feedback.status == Status.COMPLETED


def test_query_user_by_telegram_id(session: Session):
    # Given
    user = User(tg_handle="query_user", telegram_id="999888777", role=UserRole.STUDENT)
    session.add(user)
    session.commit()

    # When
    query = select(User).where(User.telegram_id == "999888777")
    result = session.exec(query).first()

    # Then
    assert result is not None
    assert result.telegram_id == "999888777"
    assert result.tg_handle == "query_user"


def test_query_homework_by_teacher(session: Session):
    # Given
    teacher = User(
        tg_handle="query_teacher", telegram_id="777666555", role=UserRole.TEACHER
    )
    session.add(teacher)
    session.commit()

    # Create multiple homework assignments
    for i in range(3):
        homework = HomeworkTask(
            teacher_id=teacher.id,
            student_ids=["student1"],
            content={"title": f"Homework {i}"},
        )
        session.add(homework)
    session.commit()

    # When
    query = select(HomeworkTask).where(HomeworkTask.teacher_id == teacher.id)
    results = session.exec(query).all()

    # Then
    assert len(results) == 3
    assert all(hw.teacher_id == teacher.id for hw in results)


def test_query_student_submissions(session: Session):
    # Given
    student = User(
        tg_handle="submission_query_student",
        telegram_id="123321123",
        role=UserRole.STUDENT,
    )
    teacher = User(
        tg_handle="submission_query_teacher",
        telegram_id="321123321",
        role=UserRole.TEACHER,
    )
    session.add(student)
    session.add(teacher)
    session.commit()

    homework = HomeworkTask(
        teacher_id=teacher.id,
        student_ids=[student.id],
        content={"title": "Query Submission Test"},
    )
    session.add(homework)
    session.commit()

    # Create multiple submissions
    for i in range(3):
        submission = Submission(
            student_id=student.id,
            teacher_id=teacher.id,
            homework_task_id=homework.id,
            content={"text": f"Submission {i}"},
        )
        session.add(submission)
    session.commit()

    # When
    query = select(Submission).where(Submission.student_id == student.id)
    results = session.exec(query).all()

    # Then
    assert len(results) == 3
    assert all(sub.student_id == student.id for sub in results)


def test_timestamps_created(session: Session):
    # Given
    now = datetime.utcnow()

    user = User(
        tg_handle="timestamp_user", telegram_id="777888999", role=UserRole.STUDENT
    )

    # When
    session.add(user)
    session.commit()
    session.refresh(user)

    # Then
    assert user.created_at is not None
    assert now - timedelta(seconds=10) <= user.created_at <= now + timedelta(seconds=10)


def test_unique_telegram_id_constraint(session: Session):
    # Given
    user1 = User(
        tg_handle="unique_user1", telegram_id="111000111", role=UserRole.STUDENT
    )
    session.add(user1)
    session.commit()

    # When/Then
    user2 = User(
        tg_handle="unique_user2",
        telegram_id="111000111",  # Same telegram_id
        role=UserRole.STUDENT,
    )
    session.add(user2)

    with pytest.raises(Exception):  # Should raise an integrity error
        session.commit()
