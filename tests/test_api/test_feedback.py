import pytest

from app.schemas.base import Status


def test_create_feedback(client):
    # Given
    # Create teacher
    teacher_data = {
        "tg_handle": "feedback_teacher1",
        "telegram_id": "111222444",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    assert teacher_response.status_code == 200
    teacher_id = teacher_response.json()["id"]

    # Create student
    student_data = {
        "tg_handle": "feedback_student1",
        "telegram_id": "444222111",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    assert student_response.status_code == 200
    student_id = student_response.json()["id"]

    # Create homework
    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "Test Homework"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    assert homework_response.status_code == 200
    homework_id = homework_response.json()["id"]

    # Create submission
    submission_data = {
        "homework_task_id": homework_id,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "content": {"text": "Test submission"},
        "status": "pending",
    }
    submission_response = client.post("/submissions/", json=submission_data)
    assert submission_response.status_code == 200
    submission_id = submission_response.json()["id"]

    # Create feedback
    feedback_data = {
        "submission_id": submission_id,
        "teacher_id": teacher_id,
        "student_id": student_id,
        "content": {"text": "Good work!"},
        "status": "completed",
    }

    # When
    response = client.post("/feedback/", json=feedback_data)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["content"]["text"] == "Good work!"
    assert data["teacher_id"] == teacher_id
    assert data["student_id"] == student_id
    assert data["submission_id"] == submission_id


def test_get_feedback_by_id(client):
    # Given
    # Create teacher
    teacher_data = {
        "tg_handle": "feedback_teacher2",
        "telegram_id": "222333555",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    # Create student
    student_data = {
        "tg_handle": "feedback_student2",
        "telegram_id": "555333222",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # Create homework
    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "Get Feedback Test"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    homework_id = homework_response.json()["id"]

    # Create submission
    submission_data = {
        "homework_task_id": homework_id,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "content": {"text": "Test submission"},
        "status": "pending",
    }
    submission_response = client.post("/submissions/", json=submission_data)
    submission_id = submission_response.json()["id"]

    # Create feedback
    feedback_data = {
        "submission_id": submission_id,
        "teacher_id": teacher_id,
        "student_id": student_id,
        "content": {"text": "Detailed feedback"},
        "status": "completed",
    }
    feedback_response = client.post("/feedback/", json=feedback_data)
    feedback_id = feedback_response.json()["id"]

    # When
    response = client.get(f"/feedback/{feedback_id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["content"]["text"] == "Detailed feedback"
    assert data["id"] == feedback_id


def test_get_submission_feedback(client):
    # Given
    # Create teacher
    teacher_data = {
        "tg_handle": "feedback_teacher3",
        "telegram_id": "333444666",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    # Create student
    student_data = {
        "tg_handle": "feedback_student3",
        "telegram_id": "666444333",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # Create homework
    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "List Feedback Test"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    homework_id = homework_response.json()["id"]

    # Create submission
    submission_data = {
        "homework_task_id": homework_id,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "content": {"text": "Test submission"},
        "status": "pending",
    }
    submission_response = client.post("/submissions/", json=submission_data)
    submission_id = submission_response.json()["id"]

    # Create multiple feedback entries
    for i in range(3):
        feedback_data = {
            "submission_id": submission_id,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "content": {"text": f"Feedback {i}"},
            "status": "completed",
        }
        client.post("/feedback/", json=feedback_data)

    # When
    response = client.get(f"/feedback/submission/{submission_id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    assert all(feedback["submission_id"] == submission_id for feedback in data)


def test_invalid_feedback_submission(client):
    # Given
    teacher_data = {
        "tg_handle": "feedback_teacher4",
        "telegram_id": "444555777",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "feedback_student4",
        "telegram_id": "777555444",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # Try to create feedback for non-existent submission
    feedback_data = {
        "submission_id": "nonexistent_submission_id",
        "teacher_id": teacher_id,
        "student_id": student_id,
        "content": {"text": "Invalid feedback"},
        "status": "completed",
    }

    # When
    response = client.post("/feedback/", json=feedback_data)

    # Then
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_feedback_status_filter(client):
    # Given
    # Create teacher
    teacher_data = {
        "tg_handle": "feedback_teacher5",
        "telegram_id": "555666888",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    # Create student
    student_data = {
        "tg_handle": "feedback_student5",
        "telegram_id": "888666555",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # Create homework
    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "Status Filter Test"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    homework_id = homework_response.json()["id"]

    # Create submission
    submission_data = {
        "homework_task_id": homework_id,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "content": {"text": "Test submission"},
        "status": "pending",
    }
    submission_response = client.post("/submissions/", json=submission_data)
    submission_id = submission_response.json()["id"]

    # Create feedback with different statuses
    statuses = ["pending", "completed"]
    for status in statuses:
        feedback_data = {
            "submission_id": submission_id,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "content": {"text": f"Feedback with status {status}"},
            "status": status,
        }
        client.post("/feedback/", json=feedback_data)

    # When
    response = client.get(
        f"/feedback/submission/{submission_id}",
        params={"submission_status": "completed"},
    )

    # Then
    assert response.status_code == 200
    data = response.json()
    assert all(feedback["status"] == "completed" for feedback in data)
