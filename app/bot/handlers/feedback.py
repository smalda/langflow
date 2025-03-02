import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from .base import BaseHandler
from .utils import create_selection_menu

logger = logging.getLogger(__name__)

AWAITING_SUBMISSION_SELECTION = 1
AWAITING_FEEDBACK = 2


class FeedbackHandler(BaseHandler):
    async def list_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show feedback list based on user role"""
        user = await self.api_client.get_user_by_telegram_id(
            str(update.effective_user.id)
        )

        if user["role"] == "student":
            # Get student's submissions
            submissions = await self.api_client.get_student_submissions(user["id"])
            message = "📝 Your feedback:\n\n"

            for submission in submissions:
                feedback_list = await self.api_client.get_submission_feedback(
                    submission["id"]
                )
                if feedback_list:
                    for feedback in feedback_list:
                        homework_title = (
                            feedback.get("homework_task", {})
                            .get("content", {})
                            .get("title", "Untitled")
                        )
                        feedback_text = feedback.get("content", {}).get(
                            "text", "No feedback provided"
                        )
                        created_at = feedback.get("created_at", "Unknown date")

                        message += (
                            f"📚 Homework: {homework_title}\n"
                            f"✍️ Feedback: {feedback_text[:100]}...\n"
                            f"🕒 Date: {created_at}\n"
                            f"-------------------\n\n"
                        )
        else:
            # Get teacher's given feedback
            submissions = await self.api_client.get_teacher_submissions(user["id"])
            message = "📝 Feedback you've given:\n\n"

            for submission in submissions:
                feedback_list = await self.api_client.get_submission_feedback(
                    submission["id"]
                )
                if feedback_list:
                    for feedback in feedback_list:
                        homework_title = (
                            feedback.get("homework_task", {})
                            .get("content", {})
                            .get("title", "Untitled")
                        )
                        student_handle = feedback.get("submission", {}).get(
                            "student_handle", "Unknown student"
                        )
                        feedback_text = feedback.get("content", {}).get(
                            "text", "No feedback provided"
                        )
                        created_at = feedback.get("created_at", "Unknown date")

                        message += (
                            f"👤 Student: @{student_handle}\n"
                            f"📚 Homework: {homework_title}\n"
                            f"✍️ Feedback: {feedback_text[:100]}...\n"
                            f"🕒 Date: {created_at}\n"
                            f"-------------------\n\n"
                        )

        await update.message.reply_text(
            message or "No feedback found!",
            reply_markup=create_selection_menu(
                [], done_button=False
            ),  # Just home button
        )

    async def list_pending_feedback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show list of submissions pending feedback"""
        if not await self.check_user_role(str(update.effective_user.id), "teacher"):
            await update.message.reply_text(
                "Only teachers can provide feedback!",
                reply_markup=create_selection_menu([], done_button=False),
            )
            return ConversationHandler.END

        user = await self.api_client.get_user_by_telegram_id(
            str(update.effective_user.id)
        )

        submissions = await self.api_client.get_teacher_submissions(user["id"])

        logger.info(
            f"User {user['id']} requested pending feedback, these are the submissions: {submissions}"
        )

        if not submissions:
            await update.message.reply_text(
                "No submissions pending feedback!",
                reply_markup=create_selection_menu([], done_button=False),
            )
            return ConversationHandler.END

        # Store submissions in context for later use
        context.user_data["submissions"] = {sub["id"]: sub for sub in submissions}

        # Create options with just the submission ID as callback data
        options = [
            (
                sub["id"],  # callback_data
                f"@{sub['student_handle']} - {sub['homework_title']}",  # display_text
            )
            for sub in submissions
            if sub["status"] == "pending"  # Only show pending submissions
        ]

        if not options:
            await update.message.reply_text(
                "No pending submissions to review!",
                reply_markup=create_selection_menu([], done_button=False),
            )
            return ConversationHandler.END

        markup = create_selection_menu(options, done_button=False)
        await update.message.reply_text(
            "Select submission to review:", reply_markup=markup
        )
        return AWAITING_SUBMISSION_SELECTION

    async def handle_submission_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle submission selection and prompt for feedback"""
        query = update.callback_query
        await query.answer()

        submission_id = query.data
        # Get submission data from stored context
        submission = context.user_data["submissions"][submission_id]
        context.user_data["selected_submission"] = submission

        # Use create_selection_menu with just the home button
        markup = create_selection_menu([], done_button=False)

        await query.edit_message_text(
            f"Selected submission from student @{submission['student_handle']}\n"
            f"For homework: {submission['homework_title']}\n\n"
            f"Content: {submission['content']['text']}\n\n"
            "Please write your feedback:",
            reply_markup=create_selection_menu(
                [], done_button=False
            ),  # Just home button
        )
        return AWAITING_FEEDBACK

    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the actual feedback content"""
        submission = context.user_data.get("selected_submission")
        if not submission:
            await update.message.reply_text(
                "Something went wrong. Please start over with /feedback"
            )
            return ConversationHandler.END

        user = await self.api_client.get_user_by_telegram_id(
            str(update.effective_user.id)
        )

        feedback_data = {
            "submission_id": submission["id"],
            "teacher_id": user["id"],
            "student_id": submission["student_id"],
            "content": {"text": update.message.text},
            "status": "completed",
        }

        try:
            await self.api_client.provide_feedback(feedback_data)
            await update.message.reply_text("✅ Feedback provided successfully!")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to provide feedback: {str(e)}")

        # Clear the stored data
        context.user_data.pop("selected_submission", None)
        context.user_data.pop("submissions", None)
        return ConversationHandler.END
