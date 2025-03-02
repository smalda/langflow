# import pytest
# import asyncio
# import pika
# import json
# from unittest.mock import AsyncMock
# from telegram import Update, User as TelegramUser, Chat
# from telegram.ext import ContextTypes
# from app.bot.handlers.homework import HomeworkHandler
# from app.bot.handlers.basic import BasicHandler
# from app.bot.client import APIClient
# from app.queue.consumer import TelegramConsumer
# from app.queue.producer import NotificationProducer
# from fastapi.testclient import TestClient
# from app.main import app

# @pytest.mark.integration
# class TestCompleteWorkflow:
#     @pytest.fixture(autouse=True)
#     def setup(self, client, session):
#         """Setup test environment with real components"""
#         # Setup API client with real FastAPI test client
#         self.api_client = APIClient(base_url="http://test")
#         self.api_client.client = client

#         # Setup RabbitMQ connection
#         credentials = pika.PlainCredentials('guest', 'guest')
#         parameters = pika.ConnectionParameters(
#             host='localhost',
#             port=5672,
#             credentials=credentials,
#             connection_attempts=3,
#             retry_delay=5
#         )

#         try:
#             # Create connection and channel
#             self.rabbitmq_connection = pika.BlockingConnection(parameters)
#             self.channel = self.rabbitmq_connection.channel()

#             # Declare queue
#             self.channel.queue_declare(queue='notifications', durable=True)

#             # Setup producer and consumer with our channel
#             self.producer = NotificationProducer()
#             self.producer.channel = self.channel

#             # For consumer, we'll just use the channel for verification
#             self.notification_queue = 'notifications'

#         except pika.exceptions.AMQPConnectionError as e:
#             pytest.skip(f"RabbitMQ connection failed: {e}")

#         # Setup handlers with real API client
#         self.basic_handler = BasicHandler(self.api_client)
#         self.homework_handler = HomeworkHandler(self.api_client)

#         yield

#         # Cleanup
#         try:
#             if hasattr(self, 'channel') and self.channel is not None:
#                 self.channel.close()
#             if hasattr(self, 'rabbitmq_connection') and self.rabbitmq_connection is not None:
#                 self.rabbitmq_connection.close()
#         except:
#             pass

#     def get_messages_from_queue(self):
#         """Helper method to get messages from RabbitMQ queue"""
#         messages = []

#         while True:
#             method_frame, header_frame, body = self.channel.basic_get(
#                 queue=self.notification_queue,
#                 auto_ack=True
#             )

#             if method_frame:
#                 messages.append(json.loads(body))
#             else:
#                 break

#         return messages

#     @pytest.mark.asyncio
#     async def test_teacher_student_registration(self):
#         """Test teacher and student registration through bot commands"""

#         # First create users directly through API to ensure they exist
#         # Create teacher
#         teacher_data = {
#             "tg_handle": "test_teacher",
#             "telegram_id": "123456789",
#             "role": "teacher",
#             "meta": {}
#         }
#         response = self.api_client.client.post("/users/", json=teacher_data)
#         assert response.status_code == 200
#         teacher_db = response.json()

#         # Create student
#         student_data = {
#             "tg_handle": "test_student",
#             "telegram_id": "987654321",
#             "role": "student",
#             "meta": {}
#         }
#         response = self.api_client.client.post("/users/", json=student_data)
#         assert response.status_code == 200
#         student_db = response.json()

#         # Create Telegram user objects
#         teacher_user = TelegramUser(
#             id=123456789,
#             is_bot=False,
#             first_name="Test",
#             username="test_teacher"
#         )
#         teacher_chat = Chat(id=123456789, type="private")
#         teacher_message = AsyncMock(
#             from_user=teacher_user,
#             chat=teacher_chat
#         )
#         teacher_update = AsyncMock(
#             message=teacher_message,
#             effective_user=teacher_user
#         )
#         teacher_context = AsyncMock(user_data={})

#         student_user = TelegramUser(
#             id=987654321,
#             is_bot=False,
#             first_name="Test",
#             username="test_student"
#         )
#         student_chat = Chat(id=987654321, type="private")
#         student_message = AsyncMock(
#             from_user=student_user,
#             chat=student_chat
#         )
#         student_update = AsyncMock(
#             message=student_message,
#             effective_user=student_user
#         )
#         student_context = AsyncMock(user_data={})

#         # Test /start command for both users
#         await self.basic_handler.start(teacher_update, teacher_context)
#         await self.basic_handler.start(student_update, student_context)

#         # Simulate role selection callbacks
#         teacher_update.callback_query = AsyncMock(
#             data="role_teacher",
#             from_user=teacher_user,
#             message=teacher_message
#         )
#         student_update.callback_query = AsyncMock(
#             data="role_student",
#             from_user=student_user,
#             message=student_message
#         )

#         # Process role selections
#         await self.basic_handler.role_callback(teacher_update, teacher_context)
#         await self.basic_handler.role_callback(student_update, student_context)

#         # Verify users exist in database using sync client
#         response = self.api_client.client.get(f"/users/by_telegram_id/{teacher_data['telegram_id']}")
#         assert response.status_code == 200
#         teacher_result = response.json()

#         response = self.api_client.client.get(f"/users/by_telegram_id/{student_data['telegram_id']}")
#         assert response.status_code == 200
#         student_result = response.json()

#         # Verify user data
#         assert teacher_result["role"] == "teacher"
#         assert student_result["role"] == "student"
#         assert teacher_result["tg_handle"] == "test_teacher"
#         assert student_result["tg_handle"] == "test_student"

#         # Store IDs for next tests
#         self.teacher_id = teacher_result["id"]
#         self.student_id = student_result["id"]

#         # Print debug information
#         print(f"Teacher ID: {self.teacher_id}")
#         print(f"Student ID: {self.student_id}")

#     @pytest.mark.asyncio
#     async def test_homework_assignment(self):
#         """Test homework assignment flow through bot commands"""
#         # Previous assertions
#         assert hasattr(self, 'teacher_id'), "Teacher ID not found. Run registration test first."
#         assert hasattr(self, 'student_id'), "Student ID not found. Run registration test first."

#         # Create teacher message for /assign command
#         teacher_user = TelegramUser(
#             id=123456789,
#             is_bot=False,
#             first_name="Test",
#             username="test_teacher"
#         )
#         teacher_chat = Chat(id=123456789, type="private")
#         teacher_message = AsyncMock(
#             from_user=teacher_user,
#             chat=teacher_chat,
#             text="/assign"
#         )
#         teacher_update = AsyncMock(
#             message=teacher_message,
#             effective_user=teacher_user
#         )
#         teacher_context = AsyncMock(user_data={})

#         # Start homework assignment process
#         result = await self.homework_handler.start_assign(teacher_update, teacher_context)
#         assert result == self.homework_handler.AWAITING_CONTENT

#         # Simulate teacher entering homework content
#         homework_content = (
#             "Title: Integration Test Homework\n"
#             "Description: This is a test homework assignment"
#         )
#         teacher_message.text = homework_content

#         # Handle homework content
#         result = await self.homework_handler.handle_homework_content(teacher_update, teacher_context)
#         assert result == self.homework_handler.AWAITING_STUDENTS

#         # Verify the homework content was stored in context
#         assert "homework_content" in teacher_context.user_data
#         assert teacher_context.user_data["homework_content"]["title"] == "Integration Test Homework"

#         # Simulate student selection
#         teacher_update.callback_query = AsyncMock(
#             data=self.student_id,
#             from_user=teacher_user,
#             message=teacher_message
#         )

#         # Handle student selection
#         result = await self.homework_handler.handle_student_selection(teacher_update, teacher_context)
#         assert result == self.homework_handler.AWAITING_STUDENTS

#         # Verify student was selected
#         assert "selected_students" in teacher_context.user_data
#         assert self.student_id in teacher_context.user_data["selected_students"]

#         # Simulate done button click
#         teacher_update.callback_query.data = "done"
#         await self.homework_handler.handle_student_selection(teacher_update, teacher_context)

#         # Verify homework was created in database
#         response = self.api_client.client.get(f"/homework/teacher/{self.teacher_id}")
#         assert response.status_code == 200
#         homeworks = response.json()

#         # Find our homework
#         created_homework = None
#         for hw in homeworks:
#             if hw["content"].get("title") == "Integration Test Homework":
#                 created_homework = hw
#                 break

#         assert created_homework is not None
#         assert self.student_id in created_homework["student_ids"]
#         assert created_homework["teacher_id"] == self.teacher_id

#         # Store homework ID for next tests
#         self.homework_id = created_homework["id"]

#         # Check messages in the queue
#         messages = self.get_messages_from_queue()

#         # Verify notification content
#         homework_notifications = [
#             msg for msg in messages
#             if msg['type'] == 'homework_assigned' and
#                str(msg['recipient_id']) == "987654321"  # student's telegram_id
#         ]

#         assert len(homework_notifications) > 0
#         notification = homework_notifications[0]
#         assert "Integration Test Homework" in notification['data']['title']

#         print(f"Created Homework ID: {self.homework_id}")
