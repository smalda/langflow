import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_settings():
    """Test default settings initialization"""
    settings = Settings()

    # Project info
    assert settings.PROJECT_NAME == "LangFlow Platform"
    assert settings.PROJECT_VERSION == "1.0.0"

    # Default values
    assert settings.RABBITMQ_HOST == "localhost"
    assert settings.RABBITMQ_PORT == 5672
    assert settings.RABBITMQ_USER == "guest"
    assert settings.RABBITMQ_PASS == "guest"

    # Queue settings
    assert settings.HOMEWORK_QUEUE == "homework_queue"
    assert settings.NOTIFICATION_QUEUE == "notification_queue"
    assert settings.FEEDBACK_QUEUE == "feedback_queue"
    assert settings.DEAD_LETTER_EXCHANGE == "dlx"
    assert settings.MESSAGE_TTL == 86400000  # 24 hours


def test_environment_variables():
    """Test settings with environment variables"""
    test_env = {
        "DATABASE_URL": "postgresql://testuser:testpass@testhost:5432/testdb",
        "RABBITMQ_HOST": "testhost",
        "RABBITMQ_PORT": "5673",
        "RABBITMQ_USER": "testuser",
        "RABBITMQ_PASS": "testpass",
        "TELEGRAM_BOT_TOKEN": "test_token",
    }

    with patch.dict(os.environ, test_env):
        settings = Settings()

        assert settings.DATABASE_URL == test_env["DATABASE_URL"]
        assert settings.RABBITMQ_HOST == test_env["RABBITMQ_HOST"]
        assert settings.RABBITMQ_PORT == 5673
        assert settings.RABBITMQ_USER == test_env["RABBITMQ_USER"]
        assert settings.RABBITMQ_PASS == test_env["RABBITMQ_PASS"]
        assert settings.TELEGRAM_BOT_TOKEN == test_env["TELEGRAM_BOT_TOKEN"]


def test_invalid_port_number():
    """Test validation of port number"""
    test_env = {
        "DATABASE_URL": "postgresql://testuser:testpass@testhost:5432/testdb",
        "RABBITMQ_PORT": "invalid_port",
    }

    with patch.dict(os.environ, test_env):
        with pytest.raises(ValueError) as exc_info:
            settings = Settings()
        assert "port" in str(exc_info.value).lower()


def test_queue_names_validation():
    """Test queue name format validation"""
    settings = Settings()

    assert settings.HOMEWORK_QUEUE.isalnum() or "_" in settings.HOMEWORK_QUEUE
    assert settings.NOTIFICATION_QUEUE.isalnum() or "_" in settings.NOTIFICATION_QUEUE
    assert settings.FEEDBACK_QUEUE.isalnum() or "_" in settings.FEEDBACK_QUEUE


def test_ttl_validation():
    """Test MESSAGE_TTL validation"""
    test_env = {
        "DATABASE_URL": "postgresql://testuser:testpass@testhost:5432/testdb",
        "MESSAGE_TTL": "-1",  # Invalid TTL
    }

    with patch.dict(os.environ, test_env):
        with pytest.raises(ValueError) as exc_info:
            settings = Settings()
        assert "ttl" in str(exc_info.value).lower()


def test_database_url_format():
    """Test DATABASE_URL format validation"""
    test_env = {"DATABASE_URL": "invalid_url_format"}

    with patch.dict(os.environ, test_env):
        with pytest.raises(ValueError) as exc_info:
            settings = Settings()
        assert "database url" in str(exc_info.value).lower()


def test_telegram_token_format():
    """Test Telegram token format validation"""
    test_env = {
        "DATABASE_URL": "postgresql://testuser:testpass@testhost:5432/testdb",
        "TELEGRAM_BOT_TOKEN": "invalid token",
    }

    with patch.dict(os.environ, test_env):
        with pytest.raises(ValueError) as exc_info:
            settings = Settings()
        assert "telegram token" in str(exc_info.value).lower()


def test_sensitive_info_hidden():
    """Test that sensitive information is hidden in string representation"""
    test_env = {
        "DATABASE_URL": "postgresql://user:password@host:5432/db",
        "TELEGRAM_BOT_TOKEN": "secret_token",
    }

    with patch.dict(os.environ, test_env):
        settings = Settings()
        settings_str = str(settings)

        assert "password" not in settings_str
        assert "secret_token" not in settings_str


def test_missing_required_settings():
    """Test handling of missing required settings"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings(DATABASE_URL=None)
        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("DATABASE_URL",) and error["type"] == "string_type"
            for error in errors
        )


def test_settings_immutability():
    """Test that settings cannot be modified after initialization"""
    settings = Settings()
    with pytest.raises((AttributeError, ValidationError)) as exc_info:
        settings.DATABASE_URL = "new_value"
    assert "frozen" in str(exc_info.value).lower()
