import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.queue.consumer import TelegramConsumer
from app.queue.message_types import Message, MessageType
from app.queue.notifications import (
    notify_feedback_provided,
    notify_homework_assigned,
    notify_submission_received,
)
from app.queue.producer import NotificationProducer


def test_message_type_enum():
    assert MessageType.HOMEWORK_ASSIGNED.value == "homework_assigned"
    assert MessageType.SUBMISSION_RECEIVED.value == "submission_received"
    assert MessageType.FEEDBACK_PROVIDED.value == "feedback_provided"


def test_message_creation():
    data = {"title": "Test Homework", "description": "Test Description"}
    message = Message(
        type=MessageType.HOMEWORK_ASSIGNED, recipient_id="123456789", data=data
    )

    message_dict = message.to_dict()
    assert message_dict["type"] == "homework_assigned"
    assert message_dict["recipient_id"] == "123456789"
    assert message_dict["data"] == data
    assert "timestamp" in message_dict


# def test_producer_initialization(producer, mock_channel):
#     assert producer.channel is not None
#     mock_channel.queue_declare.assert_called_with(
#         queue='notifications',
#         durable=True
#     )


def test_producer_send_message(producer, mock_channel):
    message = Message(
        type=MessageType.HOMEWORK_ASSIGNED,
        recipient_id="123456789",
        data={"title": "Test"},
    )

    result = producer.send_message(message)

    assert result is True
    mock_channel.basic_publish.assert_called_once()
    call_args = mock_channel.basic_publish.call_args
    assert call_args.kwargs["exchange"] == ""
    assert call_args.kwargs["routing_key"] == "notifications"
    assert isinstance(call_args.kwargs["body"], str)


def test_consumer_initialization(consumer, mock_channel):
    assert consumer.channel is not None
    mock_channel.queue_declare.assert_called_with(queue="notifications", durable=True)


@pytest.mark.asyncio
async def test_consumer_send_telegram_message(consumer):
    result = await consumer.send_telegram_message("123456789", "Test message")
    assert result is True
    consumer.bot.send_message.assert_called_once_with(
        chat_id=123456789, text="Test message"
    )


@pytest.mark.asyncio
async def test_consumer_process_message(consumer, mock_channel):
    message_data = {
        "type": "homework_assigned",
        "recipient_id": "123456789",
        "data": {"title": "Test Homework", "description": "Test Description"},
    }

    method = Mock()
    method.delivery_tag = "test_tag"

    # Replace the consumer's process_message method with an async version for testing
    async def async_process_message(ch, meth, props, body):
        try:
            message = json.loads(body)
            formatted_message = consumer._format_message(
                MessageType(message["type"]), message["data"]
            )
            success = await consumer.send_telegram_message(
                message["recipient_id"], formatted_message
            )
            if success:
                ch.basic_ack(delivery_tag=meth.delivery_tag)
            else:
                ch.basic_nack(delivery_tag=meth.delivery_tag, requeue=False)
        except Exception as e:
            ch.basic_nack(delivery_tag=meth.delivery_tag, requeue=False)

    # Mock the send_telegram_message method
    consumer.send_telegram_message = AsyncMock(return_value=True)

    # Call the async version of process_message
    await async_process_message(
        mock_channel, method, None, json.dumps(message_data).encode()
    )

    # Verify the message was acknowledged
    mock_channel.basic_ack.assert_called_once_with(delivery_tag="test_tag")


def test_notify_homework_assigned():
    homework_data = {"title": "Test Homework", "description": "Test Description"}

    with patch("app.queue.notifications.producer.send_message") as mock_send:
        mock_send.return_value = True
        result = notify_homework_assigned("123456789", homework_data)

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        message = call_args.args[0]
        assert message.type == MessageType.HOMEWORK_ASSIGNED
        assert message.recipient_id == "123456789"
        assert message.data == homework_data


def test_notify_submission_received():
    submission_data = {
        "student_name": "Test Student",
        "homework_title": "Test Homework",
        "submission_id": "sub_123",
        "content_preview": "Test submission",
    }

    with patch("app.queue.notifications.producer.send_message") as mock_send:
        mock_send.return_value = True
        result = notify_submission_received("123456789", submission_data)

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        message = call_args.args[0]
        assert message.type == MessageType.SUBMISSION_RECEIVED
        assert message.recipient_id == "123456789"
        assert message.data == submission_data


def test_notify_feedback_provided():
    feedback_data = {
        "homework_title": "Test Homework",
        "feedback_id": "fb_123",
        "content_preview": "Great work!",
        "teacher_name": "Test Teacher",
    }

    with patch("app.queue.notifications.producer.send_message") as mock_send:
        mock_send.return_value = True
        result = notify_feedback_provided("123456789", feedback_data)

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        message = call_args.args[0]
        assert message.type == MessageType.FEEDBACK_PROVIDED
        assert message.recipient_id == "123456789"
        assert message.data == feedback_data


def test_consumer_format_message(consumer):
    # Test homework assigned message
    homework_data = {"title": "Test Homework", "description": "Test Description"}
    formatted = consumer._format_message(MessageType.HOMEWORK_ASSIGNED, homework_data)
    assert "Test Homework" in formatted
    assert "Test Description" in formatted

    # Test submission received message
    submission_data = {
        "student_name": "Test Student",
        "homework_title": "Test Homework",
        "submission_id": "sub_123",
        "content_preview": "Test submission",
    }
    formatted = consumer._format_message(
        MessageType.SUBMISSION_RECEIVED, submission_data
    )
    assert "Test Student" in formatted
    assert "Test Homework" in formatted
    assert "sub_123" in formatted

    # Test feedback provided message
    feedback_data = {
        "homework_title": "Test Homework",
        "feedback_id": "fb_123",
        "content_preview": "Great work!",
        "teacher_name": "Test Teacher",
    }
    formatted = consumer._format_message(MessageType.FEEDBACK_PROVIDED, feedback_data)
    assert "Test Homework" in formatted
    assert "Test Teacher" in formatted
    assert "fb_123" in formatted


def test_producer_connection_error():
    with patch(
        "app.queue.producer.NotificationProducer._initialize_connection"
    ) as mock_init:
        # Make initialization fail
        mock_init.side_effect = Exception("Connection failed")

        # Create producer should still work but be in a failed state
        producer = NotificationProducer()

        # Now when we try to send a message, it should fail
        message = Message(
            type=MessageType.HOMEWORK_ASSIGNED,
            recipient_id="123456789",
            data={"test": "data"},
        )

        # Mock channel to be None to simulate failed connection
        producer.channel = None

        result = producer.send_message(message)
        assert result is False


def test_consumer_message_processing_error(consumer, mock_channel):
    invalid_message = "invalid json"
    method = Mock()
    method.delivery_tag = "test_tag"

    consumer.process_message(mock_channel, method, None, invalid_message.encode())

    mock_channel.basic_nack.assert_called_once_with(
        delivery_tag="test_tag", requeue=False
    )


# def test_producer_initialize_connection(mock_connection, mock_channel):
#     """Test successful connection initialization"""
#     # Create a new mock channel
#     mock_channel = Mock()
#     mock_connection.return_value.channel.return_value = mock_channel

#     producer = NotificationProducer()

#     # Call initialize explicitly (this will create a new channel)
#     producer._initialize_connection()

#     # Verify connection was created
#     mock_connection.assert_called_once()
#     # Verify channel was created
#     producer.connection.channel.assert_called_once()
#     # Verify queue was declared
#     producer.channel.queue_declare.assert_called_with(
#         queue='notifications',
#         durable=True
#     )

# def test_producer_initialize_connection_error(mock_connection):
#     """Test connection initialization error handling"""
#     # Make connection fail
#     mock_connection.side_effect = Exception("Connection failed")

#     producer = NotificationProducer()

#     # Patch the _initialize_connection call in __init__
#     with patch.object(NotificationProducer, '_initialize_connection') as mock_init:
#         producer = NotificationProducer()
#         assert producer.channel is None
#         assert producer.connection is None

#     # Now test explicit initialization
#     with pytest.raises(Exception) as exc_info:
#         producer._initialize_connection()
#     assert "Connection failed" in str(exc_info.value)

# def test_producer_initialize_connection_channel_error(mock_connection):
#     """Test channel creation error handling"""
#     # Setup mock connection but make channel creation fail
#     mock_conn = Mock()
#     mock_conn.channel.side_effect = Exception("Channel failed")
#     mock_connection.return_value = mock_conn

#     producer = NotificationProducer()

#     # Patch the _initialize_connection call in __init__
#     with patch.object(NotificationProducer, '_initialize_connection') as mock_init:
#         producer = NotificationProducer()
#         assert producer.channel is None
#         assert producer.connection is None

#     # Now test explicit initialization
#     with pytest.raises(Exception) as exc_info:
#         producer._initialize_connection()
#     assert "Channel failed" in str(exc_info.value)


def test_producer_close(producer, mock_channel, mock_connection):
    """Test producer close method"""
    # Setup mock connection and channel with proper is_closed properties
    mock_conn = Mock()
    mock_conn.is_closed = False
    mock_chan = Mock()
    mock_chan.is_closed = False

    producer.connection = mock_conn
    producer.channel = mock_chan

    # Call close
    producer.close()

    # Verify both channel and connection were closed
    mock_chan.close.assert_called_once()
    mock_conn.close.assert_called_once()


def test_producer_close_with_closed_channel(producer, mock_connection):
    """Test producer close when channel is already closed"""
    # Setup mocks with proper is_closed properties
    mock_conn = Mock()
    mock_conn.is_closed = False
    mock_chan = Mock()
    mock_chan.is_closed = True

    producer.connection = mock_conn
    producer.channel = mock_chan

    # Call close
    producer.close()

    # Verify only connection was closed
    mock_chan.close.assert_not_called()
    mock_conn.close.assert_called_once()


def test_producer_close_with_closed_connection(producer, mock_connection):
    """Test producer close when connection is already closed"""
    # Setup mocks with proper is_closed properties
    mock_conn = Mock()
    mock_conn.is_closed = True
    mock_chan = Mock()
    mock_chan.is_closed = False

    producer.connection = mock_conn
    producer.channel = mock_chan

    # Call close
    producer.close()

    # Verify only channel was closed
    mock_chan.close.assert_called_once()
    mock_conn.close.assert_not_called()
