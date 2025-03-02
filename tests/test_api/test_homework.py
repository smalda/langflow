import pytest

from app.schemas.base import Status


def test_create_homework_basic(client):
    # Given
    # Create teacher
    teacher_data = {
        "tg_handle": "homework_teacher1",
        "telegram_id": "999888771",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    assert (
        teacher_response.status_code == 200
    ), f"Failed to create teacher: {teacher_response.json()}"
    teacher_id = teacher_response.json()["id"]

    # Create student
    student_data = {
        "tg_handle": "homework_student1",
        "telegram_id": "777888991",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    assert (
        student_response.status_code == 200
    ), f"Failed to create student: {student_response.json()}"
    student_id = student_response.json()["id"]

    # Create homework
    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "Test Homework", "description": "Test Description"},
        "status": "pending",
    }

    # When
    response = client.post(
        "/homework/assign/", json=homework_data
    )  # Note: changed endpoint to /homework/assign/

    # Then
    assert response.status_code == 200, f"Failed to create homework: {response.text}"
    data = response.json()
    assert data["content"]["title"] == "Test Homework"
    assert data["teacher_id"] == teacher_id
    assert student_id in data["student_ids"]
    assert data["status"] == "pending"


def test_create_homework_multiple_students(client):
    # Given
    # Create teacher
    teacher_data = {
        "tg_handle": "homework_teacher2",
        "telegram_id": "999888772",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    assert (
        teacher_response.status_code == 200
    ), f"Failed to create teacher: {teacher_response.json()}"
    teacher_id = teacher_response.json()["id"]

    # Create multiple students
    student_ids = []
    for i in range(3):
        student_data = {
            "tg_handle": f"homework_student_{i}",
            "telegram_id": f"77788899{i}",
            "role": "student",
            "meta": {},
        }
        student_response = client.post("/users/", json=student_data)
        assert (
            student_response.status_code == 200
        ), f"Failed to create student {i}: {student_response.json()}"
        student_ids.append(student_response.json()["id"])

    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": student_ids,
        "content": {
            "title": "Group Homework",
            "description": "Test for multiple students",
        },
        "status": "pending",
    }

    # When
    response = client.post("/homework/assign/", json=homework_data)  # Fixed endpoint

    # Then
    assert response.status_code == 200, f"Failed to create homework: {response.text}"
    data = response.json()
    assert (
        len(data["student_ids"]) == 3
    ), f"Expected 3 students, got {len(data['student_ids'])}"
    assert all(sid in data["student_ids"] for sid in student_ids)


def test_get_homework_by_id(client):
    # Given - Create homework first
    # Create teacher
    teacher_data = {
        "tg_handle": "homework_teacher3",
        "telegram_id": "999888773",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    assert teacher_response.status_code == 200
    teacher_id = teacher_response.json()["id"]

    # Create student
    student_data = {
        "tg_handle": "homework_student3",
        "telegram_id": "777888993",
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
        "content": {"title": "Get By ID Test", "description": "Test Description"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    assert (
        homework_response.status_code == 200
    ), f"Failed to create homework: {homework_response.text}"
    homework_id = homework_response.json()["id"]

    # When
    response = client.get(f"/homework/{homework_id}")

    # Then
    assert response.status_code == 200, f"Failed to get homework: {response.text}"
    data = response.json()
    assert data["id"] == homework_id
    assert data["content"]["title"] == "Get By ID Test"


def test_get_teacher_homework(client):
    # Given
    teacher_data = {
        "tg_handle": "homework_teacher4",
        "telegram_id": "999888774",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    assert teacher_response.status_code == 200
    teacher_id = teacher_response.json()["id"]

    # Create student for homework assignments
    student_data = {
        "tg_handle": "homework_student4",
        "telegram_id": "777888994",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    assert student_response.status_code == 200
    student_id = student_response.json()["id"]

    # Create multiple homework assignments
    for i in range(3):
        homework_data = {
            "teacher_id": teacher_id,
            "student_ids": [student_id],
            "content": {
                "title": f"Teacher Test {i}",
                "description": f"Description {i}",
            },
            "status": "pending",
        }
        response = client.post("/homework/assign/", json=homework_data)
        assert (
            response.status_code == 200
        ), f"Failed to create homework {i}: {response.text}"

    # When
    response = client.get(f"/homework/teacher/{teacher_id}")

    # Then
    assert (
        response.status_code == 200
    ), f"Failed to get teacher homework: {response.text}"
    data = response.json()
    assert len(data) == 3, f"Expected 3 homework assignments, got {len(data)}"
    assert all(hw["teacher_id"] == teacher_id for hw in data)


def test_invalid_teacher_homework(client):
    # Given - Create a student
    student_data = {
        "tg_handle": "student_trying_homework",
        "telegram_id": "123456789",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    assert student_response.status_code == 200
    student_id = student_response.json()["id"]

    # Create another student as target
    target_student_data = {
        "tg_handle": "target_student",
        "telegram_id": "987654321",
        "role": "student",
        "meta": {},
    }
    target_response = client.post("/users/", json=target_student_data)
    assert target_response.status_code == 200
    target_id = target_response.json()["id"]

    homework_data = {
        "teacher_id": student_id,  # Student trying to create homework
        "student_ids": [target_id],
        "content": {"title": "Invalid Homework", "description": "Should fail"},
        "status": "pending",
    }

    # When
    response = client.post("/homework/assign/", json=homework_data)

    # Then
    assert response.status_code == 404
    error_detail = response.json()["detail"].lower()
    assert any(
        msg in error_detail
        for msg in ["teacher not found", "not found", "invalid teacher"]
    )


def test_homework_with_rich_content(client):
    # Given
    # Create teacher
    teacher_data = {
        "tg_handle": "homework_teacher5",
        "telegram_id": "999888775",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    assert (
        teacher_response.status_code == 200
    ), f"Failed to create teacher: {teacher_response.json()}"
    teacher_id = teacher_response.json()["id"]

    # Create a student
    student_data = {
        "tg_handle": "homework_student5",
        "telegram_id": "777888995",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    assert (
        student_response.status_code == 200
    ), f"Failed to create student: {student_response.json()}"
    student_id = student_response.json()["id"]

    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],  # Added student_id
        "content": {
            "title": "Rich Content Homework",
            "description": "Main description",
            "sections": [
                {"name": "Section 1", "content": "Detail 1"},
                {"name": "Section 2", "content": "Detail 2"},
            ],
            "due_date": "2024-12-31",
            "difficulty": "intermediate",
        },
        "status": "pending",
    }

    # When
    response = client.post("/homework/assign/", json=homework_data)  # Fixed endpoint

    # Then
    assert response.status_code == 200, f"Failed to create homework: {response.text}"
    data = response.json()
    assert data["content"]["sections"][0]["name"] == "Section 1"
    assert data["content"]["due_date"] == "2024-12-31"


def test_get_nonexistent_homework(client):
    # When
    response = client.get("/homework/nonexistent_id")

    # Then
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_student_homework_with_status(client):
    # Given
    teacher_data = {
        "tg_handle": "homework_teacher6",
        "telegram_id": "999888776",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "homework_student6",
        "telegram_id": "777888996",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # Create homeworks with different statuses
    statuses = ["pending", "completed", "cancelled"]
    for status in statuses:
        homework_data = {
            "teacher_id": teacher_id,
            "student_ids": [student_id],
            "content": {
                "title": f"{status.title()} Homework",
                "description": f"Test {status}",
            },
            "status": status,
        }
        client.post("/homework/", json=homework_data)

    # When
    response = client.get(
        f"/homework/student/{student_id}", params={"homework_status": "pending"}
    )

    # Then
    assert response.status_code == 200
    data = response.json()
    assert all(hw["status"] == "pending" for hw in data)
