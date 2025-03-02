import asyncio
import json
import logging

from telegram import Bot

from .connection import get_rabbitmq_connection
from .message_types import MessageType

logger = logging.getLogger(__name__)


class TelegramConsumer:
    def __init__(self, bot_token: str):
        self._initialize_connection()
        self.bot = Bot(token=bot_token)
        # Create a new event loop for this consumer
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def _initialize_connection(self):
        self.connection = get_rabbitmq_connection()
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue="notifications", durable=True)

    def _format_message(self, msg_type: MessageType, data: dict) -> str:
        # Remove async since we'll call it synchronously now
        if msg_type == MessageType.HOMEWORK_ASSIGNED:
            return (
                f"📚 New homework assigned!\n\n"
                f"Title: {data['title']}\n"
                f"Description: {data.get('description', 'No description provided')}"
            )
        elif msg_type == MessageType.SUBMISSION_RECEIVED:
            return (
                f"✅ New submission received!\n\n"
                f"From: {data['student_name']}\n"
                f"Homework: {data['homework_title']}\n"
                f"Submission ID: {data['submission_id']}\n\n"
                f"Preview:\n{data.get('content_preview', 'No content preview available')}"
            )
        elif msg_type == MessageType.FEEDBACK_PROVIDED:
            return (
                f"📝 New feedback received!\n\n"
                f"Homework: {data['homework_title']}\n"
                f"From: {data['teacher_name']}\n"
                f"Feedback ID: {data['feedback_id']}\n\n"
                f"Preview:\n{data.get('content_preview', 'No feedback preview available')}"
            )

        return "New notification received"

    async def send_telegram_message(self, chat_id: str, text: str):
        try:
            # Convert string telegram_id to integer if possible
            try:
                numeric_chat_id = int(chat_id)
            except ValueError:
                logger.error(f"Invalid telegram_id format: {chat_id}")
                return False

            await self.bot.send_message(chat_id=numeric_chat_id, text=text)
            return True
        except Exception as e:
            logger.error(f"Failed to send telegram message: {e}", exc_info=True)
            return False

    def process_message(self, ch, method, properties, body):
        try:
            logger.info(f"Received message: {body}")
            message = json.loads(body)
            formatted_message = self._format_message(
                MessageType(message["type"]), message["data"]
            )
            logger.info(f"Formatted message: {formatted_message}")
            logger.info(f"Attempting to send to: {message['recipient_id']}")

            # Use the event loop to run the async send
            success = self.loop.run_until_complete(
                self.send_telegram_message(message["recipient_id"], formatted_message)
            )

            if success:
                logger.info("Message sent successfully")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logger.error("Failed to send message")
                ch.basic_nack(
                    delivery_tag=method.delivery_tag, requeue=False
                )  # Don't requeue failed messages

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        try:
            self.channel.basic_qos(prefetch_count=1)
            logger.info("Set QoS prefetch to 1")

            self.channel.basic_consume(
                queue="notifications", on_message_callback=self.process_message
            )
            logger.info("Set up basic_consume")

            logger.info("Starting to consume messages...")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Error in start_consuming: {e}", exc_info=True)
            raise
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    def close(self):
        if self.channel and not self.channel.is_closed:
            self.channel.close()
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        if self.loop and not self.loop.is_closed():
            self.loop.close()
