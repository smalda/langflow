"""
1. Creating submissions
2. Retrieving submissions by ID
3. Listing student submissions
4. Invalid submission handling
5. Status filtering
6. Pagination
7. Error cases
"""

import pytest

from app.schemas.base import Status


def test_create_submission(client):
    # Given
    # Create teacher
    teacher_data = {
        "tg_handle": "submission_teacher",
        "telegram_id": "111222333",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    # Create student
    student_data = {
        "tg_handle": "submission_student",
        "telegram_id": "333222111",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # Create homework
    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "Test Homework"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    homework_id = homework_response.json()["id"]

    # Create submission
    submission_data = {
        "homework_task_id": homework_id,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "content": {"text": "This is my submission"},
        "status": "pending",
    }

    # When
    response = client.post("/submissions/", json=submission_data)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["content"]["text"] == submission_data["content"]["text"]
    assert data["student_id"] == student_id
    assert data["teacher_id"] == teacher_id


def test_get_submission_by_id(client):
    # Given
    teacher_data = {
        "tg_handle": "get_submission_teacher",
        "telegram_id": "444555666",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "get_submission_student",
        "telegram_id": "666555444",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "Get Submission Test"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    homework_id = homework_response.json()["id"]

    submission_data = {
        "homework_task_id": homework_id,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "content": {"text": "Submission to retrieve"},
        "status": "pending",
    }
    submission_response = client.post("/submissions/", json=submission_data)
    submission_id = submission_response.json()["id"]

    # When
    response = client.get(f"/submissions/{submission_id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["content"]["text"] == "Submission to retrieve"


def test_get_student_submissions(client):
    # Given
    teacher_data = {
        "tg_handle": "list_submission_teacher",
        "telegram_id": "777888999",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "list_submission_student",
        "telegram_id": "999888777",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # Create multiple homework assignments and submissions
    for i in range(3):
        homework_data = {
            "teacher_id": teacher_id,
            "student_ids": [student_id],
            "content": {"title": f"Homework {i}"},
            "status": "pending",
        }
        homework_response = client.post("/homework/assign/", json=homework_data)
        homework_id = homework_response.json()["id"]

        submission_data = {
            "homework_task_id": homework_id,
            "student_id": student_id,
            "teacher_id": teacher_id,
            "content": {"text": f"Submission {i}"},
            "status": "pending",
        }
        client.post("/submissions/", json=submission_data)

    # When
    response = client.get(f"/submissions/student/{student_id}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    assert all(sub["student_id"] == student_id for sub in data)


def test_invalid_submission_homework(client):
    # Given
    teacher_data = {
        "tg_handle": "invalid_submission_teacher",
        "telegram_id": "123456789",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "invalid_submission_student",
        "telegram_id": "987654321",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    submission_data = {
        "homework_task_id": "nonexistent_homework_id",
        "student_id": student_id,
        "teacher_id": teacher_id,
        "content": {"text": "Invalid submission"},
        "status": "pending",
    }

    # When
    response = client.post("/submissions/", json=submission_data)

    # Then
    assert response.status_code == 404


def test_submission_status_filter(client):
    # Given
    teacher_data = {
        "tg_handle": "status_filter_teacher",
        "telegram_id": "111222444",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "status_filter_student",
        "telegram_id": "444222111",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "Status Filter Test"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    homework_id = homework_response.json()["id"]

    # Create submissions with different statuses
    statuses = ["pending", "completed"]
    for status in statuses:
        submission_data = {
            "homework_task_id": homework_id,
            "student_id": student_id,
            "teacher_id": teacher_id,
            "content": {"text": f"Submission with status {status}"},
            "status": status,
        }
        client.post("/submissions/", json=submission_data)

    # When
    response = client.get(
        f"/submissions/student/{student_id}", params={"submission_status": "pending"}
    )

    # Then
    assert response.status_code == 200
    data = response.json()
    assert all(sub["status"] == "pending" for sub in data)


def test_submission_pagination(client):
    # Given
    teacher_data = {
        "tg_handle": "pagination_teacher",
        "telegram_id": "555666777",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "pagination_student",
        "telegram_id": "777666555",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "Pagination Test"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    homework_id = homework_response.json()["id"]

    # Create multiple submissions
    for i in range(5):
        submission_data = {
            "homework_task_id": homework_id,
            "student_id": student_id,
            "teacher_id": teacher_id,
            "content": {"text": f"Submission {i}"},
            "status": "pending",
        }
        client.post("/submissions/", json=submission_data)

    # When
    response = client.get(
        f"/submissions/student/{student_id}", params={"offset": 0, "limit": 2}
    )

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2
