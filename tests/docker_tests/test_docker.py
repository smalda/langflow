import time

import pytest
import requests

from docker import client

from .config import docker_settings


@pytest.fixture(scope="session")
def docker_client():
    docker_client = client.DockerClient.from_env()
    yield docker_client
    docker_client.close()


@pytest.mark.docker
def test_all_services_healthy(docker_client):
    containers = docker_client.containers.list(
        filters={"label": "com.docker.compose.project=langflow-platform"}
    )

    for container in containers:
        health_status = container.attrs["State"].get("Health", {}).get("Status")
        assert health_status == "healthy", f"Container {container.name} is not healthy"


@pytest.mark.docker
@pytest.mark.skip(reason="Needs fixing")
def test_api_service_responds():
    response = requests.get(
        f"http://{docker_settings.API_HOST}:{docker_settings.API_PORT}/health"
    )
    assert response.status_code == 200


@pytest.mark.docker
def test_database_connection():
    from sqlalchemy import create_engine, text

    engine = create_engine(docker_settings.DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1
