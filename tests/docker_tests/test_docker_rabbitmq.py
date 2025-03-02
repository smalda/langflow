import pika
import pytest

from .config import docker_settings


@pytest.mark.docker
def test_rabbitmq_connection():
    """Verify RabbitMQ connection works in Docker environment."""
    credentials = pika.PlainCredentials(
        docker_settings.RABBITMQ_USER, docker_settings.RABBITMQ_PASS
    )
    parameters = pika.ConnectionParameters(
        host=docker_settings.RABBITMQ_HOST,
        port=docker_settings.RABBITMQ_PORT,
        credentials=credentials,
    )

    connection = pika.BlockingConnection(parameters)
    assert connection.is_open
    channel = connection.channel()
    assert channel.is_open

    connection.close()
