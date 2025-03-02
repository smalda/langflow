import time

import pytest

from docker import client

from .config import docker_settings


@pytest.fixture(scope="session", autouse=True)
def ensure_docker_services():
    """Ensure all Docker services are up and healthy before running tests"""
    docker_client = client.DockerClient.from_env()
    max_retries = 30
    retry_interval = 1

    for _ in range(max_retries):
        containers = docker_client.containers.list(
            filters={"label": "com.docker.compose.project=langflow-platform"}
        )

        all_healthy = all(
            container.attrs["State"].get("Health", {}).get("Status") == "healthy"
            for container in containers
        )

        if all_healthy:
            break

        time.sleep(retry_interval)

    yield

    docker_client.close()
