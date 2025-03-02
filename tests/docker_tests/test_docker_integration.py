import asyncio

import pytest
from httpx import AsyncClient

from .config import docker_settings


@pytest.mark.asyncio
@pytest.mark.docker
@pytest.mark.skip(reason="Needs fixing")
async def test_full_workflow():
    async with AsyncClient(
        base_url=f"http://{docker_settings.API_HOST}:{docker_settings.API_PORT}"
    ) as client:
        # Create a test user
        user_data = {
            "tg_handle": "test_user",
            "telegram_id": "123456789",
            "role": "teacher",
        }
        response = await client.post("/users/", json=user_data)
        assert response.status_code == 200

        # Create homework
        homework_data = {
            "teacher_id": user["id"],
            "student_ids": [],
            "content": {"title": "Test Homework"},
        }
        response = await client.post("/homework/assign/", json=homework_data)
        assert response.status_code == 200

        # Verify message was published to RabbitMQ
        # This would require setting up a test consumer
