import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel
from telegram import Chat, Update
from telegram import User as TelegramUser
from telegram.ext import ContextTypes

from app.bot.client import APIClient
from app.core.config import settings
from app.db.base import get_db
from app.main import app
from app.queue.consumer import TelegramConsumer
from app.queue.producer import NotificationProducer

pytest_plugins = ["pytest_asyncio"]


# Database Fixtures
@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine"""
    test_engine = create_engine(settings.TEST_DATABASE_URL)
    SQLModel.metadata.create_all(bind=test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def session(db_engine):
    """Create database session"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(session):
    """Create FastAPI test client"""

    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Queue Fixtures
@pytest.fixture
def mock_channel():
    """Create mock RabbitMQ channel"""
    channel = Mock()
    channel.queue_declare = Mock()
    return channel


@pytest.fixture
def mock_connection(mock_channel):
    """Create mock RabbitMQ connection"""
    with patch("app.queue.connection.get_rabbitmq_connection") as mock:
        connection = Mock()
        connection.channel.return_value = mock_channel
        mock.return_value = connection
        yield mock


@pytest.fixture
def producer(mock_connection, mock_channel):
    """Create mock producer"""
    with patch("app.queue.producer.NotificationProducer._initialize_connection"):
        producer = NotificationProducer()
        producer.channel = mock_channel
        producer.connection = mock_connection.return_value
        return producer


@pytest.fixture
def consumer(mock_connection, mock_channel):
    """Create mock consumer"""
    with patch("telegram.Bot") as mock_bot_class:
        mock_bot = Mock()
        mock_bot.send_message = AsyncMock(return_value=True)
        mock_bot_class.return_value = mock_bot

        with patch("app.queue.consumer.TelegramConsumer._initialize_connection"):
            consumer = TelegramConsumer("fake_token")
            mock_channel.queue_declare(queue="notifications", durable=True)
            consumer.channel = mock_channel
            consumer.bot = mock_bot
            return consumer


# Bot Fixtures


@pytest.fixture
def mock_bot():
    """Create mock Telegram bot"""
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def telegram_user():
    """Create mock Telegram user"""
    user = Mock(spec=TelegramUser)
    user.id = 123456789
    user.username = "test_user"
    return user


@pytest.fixture
def mock_message(telegram_user):
    """Create mock Telegram message"""
    message = AsyncMock()
    message.from_user = telegram_user
    message.chat = Mock(spec=Chat)
    message.chat.id = telegram_user.id
    return message


@pytest.fixture
def mock_update(mock_message):
    """Create mock Telegram update with async callback query"""
    update = Mock(spec=Update)
    update.effective_user = mock_message.from_user
    update.message = mock_message

    # Add AsyncMock for callback query
    callback_query = AsyncMock()
    callback_query.answer = AsyncMock()
    callback_query.edit_message_text = AsyncMock()
    callback_query.from_user = update.effective_user
    callback_query.message = mock_message
    update.callback_query = callback_query

    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context"""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context


@pytest.fixture
def mock_api_client():
    """Create mock API client"""
    return AsyncMock()


# Async Support
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# API Client Fixture
@pytest_asyncio.fixture
async def api_client(client):
    """Create API client for bot tests"""
    api_client = APIClient(base_url="http://test")
    api_client.client = client
    return api_client
