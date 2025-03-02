from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from ..client import APIClient


class BaseHandler:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    async def check_user_role(self, telegram_id: str, expected_role: str) -> bool:
        user = await self.api_client.get_user_by_telegram_id(telegram_id)
        return user["role"] == expected_role

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel and end the conversation."""
        await update.message.reply_text("Operation cancelled.")
        return ConversationHandler.END

    def get_main_menu_button(self) -> InlineKeyboardMarkup:
        """Creates a keyboard with just the main menu button"""
        return [
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
        ]

    def add_home_button(
        self, keyboard: List[List[InlineKeyboardButton]]
    ) -> InlineKeyboardMarkup:
        """Adds home button to existing keyboard"""
        return InlineKeyboardMarkup(
            keyboard
            + [
                [
                    InlineKeyboardButton(
                        "🏠 Back to Main Menu", callback_data="main_menu"
                    )
                ]
            ]
        )

    async def return_to_main_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle return to main menu"""
        query = update.callback_query
        if query:
            await query.answer()
            # Clear all user data
            context.user_data.clear()
            await query.edit_message_text(
                "Main Menu\n\nUse /help to see available commands.", reply_markup=None
            )
        else:
            context.user_data.clear()
            await update.message.reply_text(
                "Main Menu\n\nUse /help to see available commands.", reply_markup=None
            )
        return ConversationHandler.END
