import logging

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .base import BaseHandler
from .utils import create_selection_menu

logger = logging.getLogger(__name__)


class BasicHandler(BaseHandler):
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command - initial bot interaction"""
        try:
            # Check if user already exists
            user = await self.api_client.get_user_by_telegram_id(
                str(update.effective_user.id), max_retries=1
            )

            # If user exists, show their current role
            await update.message.reply_text(
                f"Welcome back! You are already registered as a {user['role']}.\n\n"
                "Use /help to see available commands."
            )
            return

        except httpx.HTTPError as e:
            # If user doesn't exist (404) show role selection
            if getattr(e.response, "status_code", None) == 404:
                options = [
                    ("role_student", "👨‍🎓 I'm a Student"),
                    ("role_teacher", "👨‍🏫 I'm a Teacher"),
                ]

                await update.message.reply_text(
                    "Welcome to LangFlow Bot! 🎓\n\n" "Please select your role:",
                    reply_markup=create_selection_menu(options, done_button=False),
                )
            else:
                # Handle other API errors
                logger.error(f"Error checking user existence: {e}")
                await update.message.reply_text(
                    "Sorry, there was an error. Please try again later."
                )

    async def role_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle role selection"""
        query = update.callback_query
        await query.answer()
        role = query.data.split("_")[1]  # 'role_student' -> 'student'

        try:
            await self.api_client.get_or_create_user(
                telegram_id=str(query.from_user.id),
                username=query.from_user.username or f"user_{query.from_user.id}",
                role=role,
            )

            await query.edit_message_text(
                f"You're registered as a {role}! 🎉\n\n"
                "Use /help to see available commands."
            )
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            await query.edit_message_text(
                "Sorry, there was an error registering you. "
                "Please try again with /start"
            )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /help command - show available commands"""
        help_text = (
            "🎓 LangFlow Bot Help\n\n"
            "Common Commands:\n"
            "/start - Register or change role\n"
            "/help - Show this help message\n"
            "/homework - View your homework\n"
            "/feedback - View your feedback\n\n"
            "Student Commands:\n"
            "/submit <homework_id> - Submit your homework\n\n"
            "/ai_teacher - Start conversation with AI English teacher 🤖\n\n"
            "Teacher Commands:\n"
            "/assign - Create new homework assignment\n"
            "/pending_feedback - View submissions needing feedback\n\n"
            "Tips:\n"
            "• Use homework IDs when submitting or providing feedback\n"
            "• You can view your homework at any time with /homework\n"
            "• Teachers can select multiple students when assigning homework"
        )

        await update.message.reply_text(help_text)
