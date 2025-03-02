import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.run_consumer import main


@pytest.mark.asyncio
async def test_consumer_normal_operation():
    """Test normal consumer operation and graceful shutdown"""

    mock_consumer = Mock()
    mock_consumer.channel = Mock()
    mock_consumer.connection = Mock()

    mock_loop = Mock()
    mock_loop.close = Mock()

    with patch("asyncio.new_event_loop", return_value=mock_loop), patch(
        "asyncio.set_event_loop"
    ), patch("app.run_consumer.TelegramConsumer", return_value=mock_consumer), patch(
        "app.run_consumer.settings"
    ) as mock_settings:

        # Configure mock to raise KeyboardInterrupt after start_consuming
        mock_consumer.start_consuming.side_effect = KeyboardInterrupt()
        mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

        # Run main
        main()

        # Verify the consumer was started
        mock_consumer.start_consuming.assert_called_once()

        # Verify cleanup was performed
        mock_consumer.channel.close.assert_called_once()
        mock_consumer.connection.close.assert_called_once()
        mock_loop.close.assert_called_once()


@pytest.mark.asyncio
async def test_consumer_unexpected_error():
    """Test handling of unexpected errors during consumer operation"""

    mock_consumer = Mock()
    mock_consumer.channel = Mock()
    mock_consumer.connection = Mock()

    mock_loop = Mock()
    mock_loop.close = Mock()

    with patch("asyncio.new_event_loop", return_value=mock_loop), patch(
        "asyncio.set_event_loop"
    ), patch("app.run_consumer.TelegramConsumer", return_value=mock_consumer), patch(
        "app.run_consumer.settings"
    ) as mock_settings:

        # Configure mock to raise an unexpected error
        mock_consumer.start_consuming.side_effect = Exception("Unexpected error")
        mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

        # Run main and expect exception
        with pytest.raises(Exception) as exc_info:
            main()

        assert str(exc_info.value) == "Unexpected error"

        # Verify cleanup was still performed
        mock_consumer.channel.close.assert_called_once()
        mock_consumer.connection.close.assert_called_once()
        mock_loop.close.assert_called_once()


@pytest.mark.asyncio
async def test_consumer_cleanup_error():
    """Test handling of errors during cleanup"""

    mock_consumer = Mock()
    mock_consumer.channel = Mock()
    mock_consumer.connection = Mock()

    # Configure cleanup to fail
    mock_consumer.channel.close.side_effect = Exception("Cleanup error")

    mock_loop = Mock()
    mock_loop.close = Mock()

    with patch("asyncio.new_event_loop", return_value=mock_loop), patch(
        "asyncio.set_event_loop"
    ), patch("app.run_consumer.TelegramConsumer", return_value=mock_consumer), patch(
        "app.run_consumer.settings"
    ) as mock_settings:

        mock_consumer.start_consuming.side_effect = KeyboardInterrupt()
        mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

        # Run main
        main()

        # Verify that even with cleanup errors, the loop was closed
        mock_loop.close.assert_called_once()


@pytest.mark.asyncio
async def test_consumer_initialization_error():
    """Test handling of errors during consumer initialization"""

    with patch("asyncio.new_event_loop"), patch("asyncio.set_event_loop"), patch(
        "app.run_consumer.TelegramConsumer"
    ) as mock_consumer_class, patch("app.run_consumer.settings") as mock_settings:

        # Configure consumer initialization to fail
        mock_consumer_class.side_effect = Exception("Initialization error")
        mock_settings.TELEGRAM_BOT_TOKEN = "test_token"

        # Run main and expect exception
        with pytest.raises(Exception) as exc_info:
            main()

        assert str(exc_info.value) == "Initialization error"


@pytest.mark.asyncio
async def test_consumer_missing_token():
    """Test handling of missing Telegram token"""

    with patch("asyncio.new_event_loop"), patch("asyncio.set_event_loop"), patch(
        "app.run_consumer.settings"
    ) as mock_settings:

        # Configure missing token
        mock_settings.TELEGRAM_BOT_TOKEN = None

        # Run main and expect exception
        with pytest.raises(Exception):
            main()
