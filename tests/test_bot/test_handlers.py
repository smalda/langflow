from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram import Chat, Update
from telegram import User as TelegramUser
from telegram.ext import ContextTypes, ConversationHandler

from app.bot.handlers.basic import BasicHandler
from app.bot.handlers.feedback import AWAITING_SUBMISSION_SELECTION, FeedbackHandler
from app.bot.handlers.homework import HomeworkHandler
from app.bot.handlers.submission import AWAITING_HOMEWORK_SELECTION, SubmissionHandler


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context, mock_api_client):
    # Given
    handler = BasicHandler(mock_api_client)

    # When
    await handler.start(mock_update, mock_context)

    # Then
    mock_update.message.reply_text.assert_called_once()
    assert "Welcome" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_role_callback_student(mock_update, mock_context, mock_api_client):
    # Given
    handler = BasicHandler(mock_api_client)
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "role_student"
    mock_update.callback_query.from_user = mock_update.effective_user

    # Mock API client response
    mock_api_client.get_or_create_user.return_value = {
        "role": "student",
        "tg_handle": "test_user",
    }

    # When
    await handler.role_callback(mock_update, mock_context)

    # Then
    mock_api_client.get_or_create_user.assert_called_once_with(
        telegram_id="123456789", username="test_user", role="student"
    )
    mock_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_homework_list_student(mock_update, mock_context, mock_api_client):
    # Given
    handler = HomeworkHandler(mock_api_client)
    mock_api_client.get_user_by_telegram_id.return_value = {
        "id": "student_1",
        "role": "student",
    }
    mock_api_client.get_homework_for_student.return_value = [
        {
            "id": "hw_1",
            "content": {"title": "Test Homework"},
            "status": "pending",
            "teacher_handle": "test_teacher",
        }
    ]

    # When
    await handler.list_homework(mock_update, mock_context)

    # Then
    mock_api_client.get_homework_for_student.assert_called_once()
    mock_update.message.reply_text.assert_called_once()
    text = mock_update.message.reply_text.call_args[0][0]
    assert "Test Homework" in text


@pytest.mark.asyncio
async def test_homework_list_teacher(mock_update, mock_context, mock_api_client):
    # Given
    handler = HomeworkHandler(mock_api_client)
    mock_api_client.get_user_by_telegram_id.return_value = {
        "id": "teacher_1",
        "role": "teacher",
    }
    mock_api_client.get_homework_for_teacher.return_value = [
        {
            "id": "hw_1",
            "content": {"title": "Test Homework"},
            "student_ids": ["student_1"],
        }
    ]

    # When
    await handler.list_homework(mock_update, mock_context)

    # Then
    mock_api_client.get_homework_for_teacher.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_start_submit_homework(mock_update, mock_context, mock_api_client):
    # Given
    handler = SubmissionHandler(mock_api_client)
    mock_api_client.get_user_by_telegram_id.return_value = {
        "id": "student_1",
        "role": "student",
    }
    mock_api_client.get_homework_for_student.return_value = [
        {
            "id": "hw_1",
            "content": {"title": "Test Homework"},
            "status": "pending",
            "teacher_handle": "test_teacher",  # Added this
            "teacher_telegram_id": "987654321",  # Added this
        }
    ]

    # When
    result = await handler.start_submit(mock_update, mock_context)

    # Then
    assert (
        result == AWAITING_HOMEWORK_SELECTION
    )  # Make sure this constant matches your handler
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_list_pending_feedback(mock_update, mock_context, mock_api_client):
    # Given
    handler = FeedbackHandler(mock_api_client)
    mock_api_client.get_user_by_telegram_id.return_value = {
        "id": "teacher_1",
        "role": "teacher",
    }
    mock_api_client.get_teacher_submissions.return_value = [
        {
            "id": "sub_1",
            "student_handle": "test_student",
            "homework_title": "Test Homework",
            "status": "pending",
            "content": {"text": "Test submission"},  # Added this
        }
    ]

    # When
    result = await handler.list_pending_feedback(mock_update, mock_context)

    # Then
    assert result == AWAITING_SUBMISSION_SELECTION  # Updated constant name
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_command(mock_update, mock_context, mock_api_client):
    # Given
    handler = BasicHandler(mock_api_client)

    # When
    result = await handler.cancel(mock_update, mock_context)

    # Then
    assert result == ConversationHandler.END
    mock_update.message.reply_text.assert_called_once_with("Operation cancelled.")
