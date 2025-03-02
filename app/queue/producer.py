import json
import logging

import pika

from .connection import get_rabbitmq_connection
from .message_types import Message

logger = logging.getLogger(__name__)


class NotificationProducer:
    def __init__(self):
        self.channel = None
        self.connection = None
        try:
            self._initialize_connection()
        except Exception as e:
            logger.error(f"Failed to initialize connection: {e}")

    def send_message(self, message: Message) -> bool:
        try:
            message_dict = message.to_dict()
            logger.info(f"Attempting to send message: {message_dict}")  # Add this line
            self.channel.basic_publish(
                exchange="",
                routing_key="notifications",
                body=json.dumps(message_dict),
                properties=pika.BasicProperties(
                    delivery_mode=2  # Make message persistent
                ),
            )
            logger.info("Message published successfully")  # Add this line
            return True
        except Exception as e:
            logger.error(
                f"Failed to send message: {e}", exc_info=True
            )  # Add exc_info=True
            return False

    def _initialize_connection(self):
        try:
            self.connection = get_rabbitmq_connection()
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue="notifications", durable=True)
        except Exception as e:
            logger.error(f"Failed to initialize connection: {e}")
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            raise

    def close(self):
        if self.channel and not self.channel.is_closed:
            self.channel.close()
        if self.connection and not self.connection.is_closed:
            self.connection.close()
