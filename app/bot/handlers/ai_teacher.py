import asyncio
import os
from typing import Dict, Optional, Set

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..ai_teacher import AITeacher
from ..memory import MemoryBuffer
from ..retrying_httpx_client import AsyncRetryingClient

load_dotenv()

import logging

logger = logging.getLogger(__name__)

# States
AI_CONVERSATION = 1


class AITeacherHandler:
    def __init__(self, client: AsyncRetryingClient):
        self.teacher = AITeacher(api_key=os.getenv("OPENAI_API_KEY"), client=client)
        self.user_buffers: Dict[str, MemoryBuffer] = {}
        self.active_conversations: Set[str] = set()
        self.thinking_animations = [
            "🤔 Thinking",
            "🤔 Thinking.",
            "🤔 Thinking..",
            "🤔 Thinking...",
            "🧠 Processing",
            "🧠 Processing.",
            "🧠 Processing..",
            "🧠 Processing...",
            "💭 Contemplating",
            "💭 Contemplating.",
            "💭 Contemplating..",
            "💭 Contemplating...",
        ]

    async def cleanup(self):
        """Cleanup method to be called when shutting down"""
        await self.teacher.close()

    async def get_user_by_telegram_id(
        self, telegram_id: str, max_retries: Optional[int] = None
    ) -> Dict:
        # No pagination needed for single user
        response = await self.teacher.api_client.get(
            f"/users/by_telegram_id/{telegram_id}", max_retries=max_retries
        )
        return response.json()

    def get_handler(self) -> ConversationHandler:
        """Return the conversation handler for AI teacher"""
        return ConversationHandler(
            entry_points=[CommandHandler("ai_teacher", self.start_conversation)],
            states={
                AI_CONVERSATION: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, self.handle_message
                    ),
                ]
            },
            fallbacks=[CommandHandler("leave", self.end_conversation)],
            name="ai_teacher_conversation",
            persistent=False,
        )

    async def get_or_create_buffer(self, user_telegram_id: str) -> MemoryBuffer:
        """Get existing buffer or create new one for user"""
        if user_telegram_id not in self.user_buffers:
            user = await self.get_user_by_telegram_id(user_telegram_id)
            user_id = user["id"]

            self.user_buffers[user_telegram_id] = MemoryBuffer(student_id=user_id)
        return self.user_buffers[user_telegram_id]

    async def start_conversation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Start a conversation with AI teacher"""
        user_telegram_id = str(update.effective_user.id)

        # First check if user is a student
        try:
            user = await self.get_user_by_telegram_id(user_telegram_id)
            if user["role"] != "student":
                await update.message.reply_text(
                    "Sorry, AI teacher is only available for students. "
                    "Teachers have access to other commands - use /help to see them."
                )
                return ConversationHandler.END
        except Exception as e:
            await update.message.reply_text(
                "Error checking user role. Please try again later or contact support."
            )
            logger.error(f"Error checking user role: {e}")
            return ConversationHandler.END

        # Check if already in conversation
        if user_telegram_id in self.active_conversations:
            await update.message.reply_text(
                "You're already talking with the AI teacher. "
                "Send /leave to end the current conversation first."
            )
            return ConversationHandler.END

        # Add to active conversations
        self.active_conversations.add(user_telegram_id)

        # Get or create memory buffer
        await self.get_or_create_buffer(user_telegram_id)

        # Send welcome message
        await update.message.reply_text(
            "👋 Hello! I'm your AI English teacher. "
            "We can have a conversation about your learning, "
            "homework, or anything related to English.\n\n"
            "You can:\n"
            "• Ask for new homework\n"
            "• Submit your work\n"
            "• Get feedback\n"
            "• Analyze your progress\n\n"
            "To end our conversation, just send /leave"
        )

        return AI_CONVERSATION

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle a message in the AI teacher conversation"""
        user_telegram_id = str(update.effective_user.id)

        if user_telegram_id not in self.active_conversations:
            await update.message.reply_text(
                "Please start a conversation with /ai_teacher first."
            )
            return ConversationHandler.END

        # Show typing indicator
        # await context.bot.send_chat_action(
        #     chat_id=update.effective_chat.id,
        #     action=ChatAction.TYPING
        # )

        try:
            # Send initial thinking message and start animation
            thinking_message = await update.message.reply_text("🤔 Thinking...")
            animation_task = asyncio.create_task(
                self.animate_thinking(thinking_message, context)
            )

            # Get user's memory buffer
            buffer = await self.get_or_create_buffer(user_telegram_id)

            try:
                # Process message through AI teacher
                response = await self.teacher.process_message(
                    message=update.message.text, memory=buffer
                )

                # Cancel and cleanup the animation
                animation_task.cancel()
                try:
                    await animation_task
                except asyncio.CancelledError:
                    pass

                # Send response
                await update.message.reply_text(response)
                return AI_CONVERSATION

            finally:
                # Make sure we cancel the animation task
                if not animation_task.done():
                    animation_task.cancel()
                    try:
                        await animation_task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            print(f"Error in AI teacher conversation: {e}")
            await update.message.reply_text(
                "I'm sorry, I encountered an error while processing your message. "
                "Please try again or start a new conversation with /ai_teacher"
            )
            return AI_CONVERSATION

    async def end_conversation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """End the conversation with AI teacher"""
        user_telegram_id = str(update.effective_user.id)

        if user_telegram_id in self.active_conversations:
            self.active_conversations.remove(user_telegram_id)

            await update.message.reply_text(
                "Conversation ended. Your progress and memory are saved. "
                "You can start a new conversation anytime with /ai_teacher"
            )

        return ConversationHandler.END

    async def animate_thinking(self, message, context: ContextTypes.DEFAULT_TYPE):
        """Animate thinking status in a message"""
        while True:
            for frame in self.thinking_animations:
                try:
                    await message.edit_text(frame)
                    await asyncio.sleep(0.5)  # Adjust speed of animation
                except asyncio.CancelledError:
                    # Make sure we remove the thinking message when done
                    try:
                        await message.delete()
                    except:
                        pass
                    raise
                except Exception:
                    # If we can't edit the message (too many edits too quickly), just continue
                    continue
