import logging
from functools import lru_cache

from pika import BlockingConnection, ConnectionParameters, PlainCredentials

from ..core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_rabbitmq_connection():
    return BlockingConnection(
        ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=PlainCredentials(
                settings.RABBITMQ_USER, settings.RABBITMQ_PASS
            ),
            heartbeat=600,
        )
    )
