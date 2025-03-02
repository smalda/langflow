"""
These tests cover:
1. Basic CRUD operations
2. Role-based user creation
3. Duplicate handling
4. Validation errors
5. Pagination
6. Complex JSON metadata
7. Edge cases with empty/invalid data
"""

import pytest

from app.schemas.user import UserRole


def test_create_user(client):
    # Given
    user_data = {
        "tg_handle": "test_user",
        "telegram_id": "123456789",
        "role": "student",
        "meta": {},
    }

    # When
    response = client.post("/users/", json=user_data)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["tg_handle"] == user_data["tg_handle"]
    assert data["telegram_id"] == user_data["telegram_id"]
    assert data["role"] == user_data["role"]


def test_get_user_by_telegram_id(client):
    # Given
    user_data = {
        "tg_handle": "get_test_user",
        "telegram_id": "987654321",
        "role": "teacher",
        "meta": {},
    }
    client.post("/users/", json=user_data)

    # When
    response = client.get(f"/users/by_telegram_id/{user_data['telegram_id']}")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["tg_handle"] == user_data["tg_handle"]
    assert data["role"] == user_data["role"]


import pytest

from app.schemas.user import UserRole


def test_create_user_student(client):
    # Given
    user_data = {
        "tg_handle": "test_student",
        "telegram_id": "123456789",
        "role": "student",
        "meta": {"grade": "beginner"},
    }

    # When
    response = client.post("/users/", json=user_data)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["tg_handle"] == user_data["tg_handle"]
    assert data["telegram_id"] == user_data["telegram_id"]
    assert data["role"] == user_data["role"]
    assert data["meta"] == user_data["meta"]


def test_create_user_teacher(client):
    # Given
    user_data = {
        "tg_handle": "test_teacher",
        "telegram_id": "987654321",
        "role": "teacher",
        "meta": {"specialization": "ballet"},
    }

    # When
    response = client.post("/users/", json=user_data)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "teacher"
    assert data["meta"]["specialization"] == "ballet"


def test_duplicate_telegram_id(client):
    # Given
    user_data = {
        "tg_handle": "original_user",
        "telegram_id": "111222333",
        "role": "student",
        "meta": {},
    }
    client.post("/users/", json=user_data)

    # When
    duplicate_data = {
        "tg_handle": "duplicate_user",
        "telegram_id": "111222333",  # Same telegram_id
        "role": "student",
        "meta": {},
    }
    response = client.post("/users/", json=duplicate_data)

    # Then
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_get_all_teachers(client):
    # Given
    teacher_data = {
        "tg_handle": "another_teacher",
        "telegram_id": "444555666",
        "role": "teacher",
        "meta": {},
    }
    client.post("/users/", json=teacher_data)

    # When
    response = client.get("/users/teachers/")

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(user["role"] == "teacher" for user in data)


def test_invalid_role(client):
    # Given
    user_data = {
        "tg_handle": "invalid_role_user",
        "telegram_id": "999000999",
        "role": "invalid_role",  # Invalid role
        "meta": {},
    }

    # When
    response = client.post("/users/", json=user_data)

    # Then
    assert response.status_code == 422  # Validation error


def test_get_users_with_role_filter(client):
    # When
    response = client.get("/users/", params={"role": "student"})

    # Then
    assert response.status_code == 200
    data = response.json()
    assert all(user["role"] == "student" for user in data)


def test_get_user_by_invalid_telegram_id(client):
    # When
    response = client.get("/users/by_telegram_id/nonexistent")

    # Then
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_users_pagination(client):
    # Given - Create multiple users
    for i in range(5):
        user_data = {
            "tg_handle": f"pagination_user_{i}",
            "telegram_id": f"55555{i}",
            "role": "student",
            "meta": {},
        }
        client.post("/users/", json=user_data)

    # When - Get paginated results
    response = client.get("/users/", params={"offset": 0, "limit": 3})

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 3  # Should respect the limit


def test_empty_telegram_handle(client):
    # Given
    user_data = {
        "tg_handle": "",  # Empty handle
        "telegram_id": "777888999",
        "role": "student",
        "meta": {},
    }

    # When
    response = client.post("/users/", json=user_data)

    # Then
    assert response.status_code == 422  # Validation error


def test_valid_meta_json(client):
    # Given
    user_data = {
        "tg_handle": "meta_test_user",
        "telegram_id": "123123123",
        "role": "student",
        "meta": {
            "age": 25,
            "preferences": {"style": "contemporary", "level": "intermediate"},
        },
    }

    # When
    response = client.post("/users/", json=user_data)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["preferences"]["style"] == "contemporary"
