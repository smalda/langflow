import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from .base import BaseHandler
from .utils import create_selection_menu

logger = logging.getLogger(__name__)

# Add new state
AWAITING_HOMEWORK_SELECTION = 1
AWAITING_SUBMISSION = 2


class SubmissionHandler(BaseHandler):
    async def start_submit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_user_role(str(update.effective_user.id), "student"):
            await update.message.reply_text("Only students can submit homework!")
            return ConversationHandler.END

        # Get user info
        user = await self.api_client.get_user_by_telegram_id(
            str(update.effective_user.id)
        )

        # Get available homework
        homework_list = await self.api_client.get_homework_for_student(user["id"])

        if not homework_list:
            await update.message.reply_text(
                "No homework available to submit!",
                reply_markup=create_selection_menu([], done_button=False),
            )
            return ConversationHandler.END

        # Create options for the menu
        options = [
            (
                hw["id"],  # callback_data
                f"@{hw['teacher_handle']} - {hw['content'].get('title', 'Untitled')}",  # display_text
            )
            for hw in homework_list
            if hw["status"] == "pending"  # Only show pending homework
        ]

        if not options:
            await update.message.reply_text(
                "No pending homework to submit!",
                reply_markup=create_selection_menu([], done_button=False),
            )
            return ConversationHandler.END

        markup = create_selection_menu(
            options, done_button=False
        )  # No need for done button here
        await update.message.reply_text(
            "Select homework to submit:", reply_markup=markup
        )
        return AWAITING_HOMEWORK_SELECTION

    async def handle_homework_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle the homework selection and prompt for submission content"""
        query = update.callback_query
        await query.answer()

        if query.data == "main_menu":
            context.user_data.clear()
            return ConversationHandler.END

        homework_id = query.data
        context.user_data["selected_homework"] = homework_id

        # Get homework details for better UX
        homework = await self.api_client.get_homework_by_id(homework_id)

        try:
            await query.edit_message_text(
                f"Selected homework: {homework['content'].get('title', 'Untitled')}\n\n"
                "Please send your submission content as a message.",
                reply_markup=create_selection_menu(
                    [], done_button=False
                ),  # Just home button
            )
            return AWAITING_SUBMISSION
        except Exception as e:
            logger.error(f"Error handling homework selection: {e}")
            context.user_data.clear()
            return ConversationHandler.END

    async def handle_submission(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle the actual submission content"""
        homework_id = context.user_data.get("selected_homework")
        if not homework_id:
            await update.message.reply_text(
                "Something went wrong. Please start over with /submit"
            )
            return ConversationHandler.END

        user = await self.api_client.get_user_by_telegram_id(
            str(update.effective_user.id)
        )
        homework = await self.api_client.get_homework_by_id(homework_id)

        submission_data = {
            "homework_task_id": homework_id,
            "student_id": user["id"],
            "teacher_id": homework["teacher_id"],
            "content": {"text": update.message.text},
            "status": "pending",
        }

        try:
            submission = await self.api_client.submit_homework(submission_data)
            await update.message.reply_text("✅ Homework submitted successfully!")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to submit homework: {str(e)}")

        # Clear the stored homework ID
        context.user_data.pop("selected_homework", None)
        return ConversationHandler.END
