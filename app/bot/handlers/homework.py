"""
This handler provides:
1. Listing homework (different views for students and teachers)
2. Starting homework assignment process (teachers only)
3. Handling homework content input
4. Student selection with toggle functionality
5. Proper cleanup of temporary data
6. Error handling at each step
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from .base import BaseHandler
from .submission import SubmissionHandler
from .utils import create_selection_menu

AWAITING_CONTENT = 1
AWAITING_STUDENTS = 2


class HomeworkHandler(BaseHandler):
    def __init__(self, api_client):
        super().__init__(api_client)
        self.submission_handler = SubmissionHandler(api_client)  # Add this

    async def list_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show homework list based on user role"""
        user = await self.api_client.get_user_by_telegram_id(
            str(update.effective_user.id)
        )

        if user["role"] == "student":
            homework_list = await self.api_client.get_homework_for_student(user["id"])
            message = "📚 Your homework:\n\n"
            for hw in homework_list:
                status_emoji = {
                    "pending": "⏳",
                    "completed": "✅",
                    "cancelled": "X",
                    "feedback_received": "📝",
                }.get(hw["status"], "❓")

                message += (
                    f"{status_emoji} {hw['content'].get('title', 'Untitled')}\n"
                    f"ID: {hw['id']}\n"
                    f"Status: {hw['status']}\n\n"
                )
        else:
            homework_list = await self.api_client.get_homework_for_teacher(user["id"])
            message = "📚 Homework you've assigned:\n\n"
            for hw in homework_list:
                message += (
                    f"📝 {hw['content'].get('title', 'Untitled')}\n"
                    f"ID: {hw['id']}\n"
                    f"Assigned to: {len(hw['student_ids'])} students\n\n"
                )

        # if user['role'] == 'student':
        #     custom_buttons = [[InlineKeyboardButton("📝 Submit Homework", callback_data="submit_homework")]]
        # else:
        #     custom_buttons = None
        custom_buttons = None
        await update.message.reply_text(
            message or "No homework found!",
            reply_markup=create_selection_menu([], custom_buttons=custom_buttons),
        )

    async def handle_submit_button(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle the submit homework button press"""
        query = update.callback_query
        await query.answer()

        # Redirect to submission handler's start_submit
        return await self.submission_handler.start_submit(update, context)

    async def start_assign(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start homework assignment process"""
        if not await self.check_user_role(str(update.effective_user.id), "teacher"):
            await update.message.reply_text("Only teachers can assign homework!")
            return ConversationHandler.END

        await update.message.reply_text(
            "Please send the homework content in format:\n\n"
            "Title: <title>\nDescription: <description>"
        )
        return AWAITING_CONTENT

    async def handle_homework_content(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Process homework content and show student selection"""
        text = update.message.text
        try:
            title = text.split("Title:")[1].split("Description:")[0].strip()
            description = text.split("Description:")[1].strip()

            context.user_data["homework_content"] = {
                "title": title,
                "description": description,
            }

            # Get list of students
            students = await self.api_client.get_all_students()
            if students == []:
                await update.message.reply_text(
                    "No students found!\nUse /help to see available commands"
                )
                return ConversationHandler.END

            options = [
                (
                    student["id"],
                    f"{'✅ ' if student['id'] in context.user_data.get('selected_students', []) else '❌ '}{student['tg_handle']}",
                )
                for student in students
            ]

            await update.message.reply_text(
                "Select students to assign homework to:",
                reply_markup=create_selection_menu(
                    options,
                    done_button=True,  # We need the Done button here
                    home_button=False,
                ),
            )
            return AWAITING_STUDENTS

        except Exception as e:
            await update.message.reply_text(
                "Invalid format! Please use:\nTitle: <title>\nDescription: <description>"
            )
            return AWAITING_CONTENT

    async def handle_student_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        await query.answer()

        import logging

        logger = logging.getLogger(__name__)  # Add logger
        logger.info(f"Callback data received: {query.data}")

        if query.data == "done":
            selected_students = context.user_data.get("selected_students", [])
            if not selected_students:
                await query.edit_message_text(
                    "Please select at least one student!",
                    reply_markup=query.message.reply_markup,
                )
                return AWAITING_STUDENTS

            # Create homework
            user = await self.api_client.get_user_by_telegram_id(
                str(update.effective_user.id)
            )

            homework_data = {
                "teacher_id": user["id"],
                "student_ids": selected_students,
                "content": context.user_data["homework_content"],
                "status": "pending",
            }

            try:
                await self.api_client.assign_homework(homework_data)
                await query.edit_message_text("✅ Homework assigned successfully!")
            except Exception as e:
                await query.edit_message_text(f"❌ Failed to assign homework: {str(e)}")

            # Clear temporary data
            context.user_data.clear()

            return ConversationHandler.END

        else:
            student_id = query.data
            logger.info(f"Callback data handled: {student_id}")
            if "selected_students" not in context.user_data:
                context.user_data["selected_students"] = []

            # Toggle student selection
            if student_id in context.user_data["selected_students"]:
                context.user_data["selected_students"].remove(student_id)
            else:
                context.user_data["selected_students"].append(student_id)

            # Update message with current selection
            students = await self.api_client.get_all_students()
            keyboard = []
            message_text = (
                "Select students to assign homework to:\n\nSelected students:"
            )

            for student in students:
                logger.info(f"Callback data created: {student['id']}")
                selected = (
                    "✅ "
                    if student["id"] in context.user_data["selected_students"]
                    else "❌ "
                )
                options = [
                    (
                        student["id"],
                        f"{'✅ ' if student['id'] in context.user_data['selected_students'] else '❌ '}{student['tg_handle']}",
                    )
                    for student in students
                ]
                if student["id"] in context.user_data["selected_students"]:
                    message_text += f"\n- {student['tg_handle']}"

            try:
                # Try to edit both message text and reply markup
                await query.edit_message_text(
                    text=message_text,
                    reply_markup=create_selection_menu(
                        options, done_button=True, home_button=False
                    ),
                )
            except telegram.error.BadRequest as e:
                if "Message is not modified" in str(e):
                    # If the message content hasn't changed, just ignore the error
                    pass
                else:
                    # If it's a different error, raise it
                    raise

            return AWAITING_STUDENTS
