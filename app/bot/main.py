import asyncio
import logging
import os
import sys
from signal import SIGABRT, SIGINT, SIGTERM, signal

from dotenv import load_dotenv

from .client import APIClient

load_dotenv()

from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .handlers.ai_teacher import AITeacherHandler
from .handlers.basic import BasicHandler
from .handlers.feedback import (
    AWAITING_FEEDBACK,
    AWAITING_SUBMISSION_SELECTION,
    FeedbackHandler,
)
from .handlers.homework import AWAITING_CONTENT, AWAITING_STUDENTS, HomeworkHandler
from .handlers.submission import (
    AWAITING_HOMEWORK_SELECTION,
    AWAITING_SUBMISSION,
    SubmissionHandler,
)
from .retrying_httpx_client import AsyncRetryingClient

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class LangFlowBot:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.base_url = "http://api:8000"

        self.httpx_client = AsyncRetryingClient(
            base_url=self.base_url,
            timeout=30.0,
            max_retries=5,
            initial_retry_delay=1.0,
            max_retry_delay=32.0,
        )

        self.api_client = APIClient(self.httpx_client)
        self.application = None

    async def verify_api_connection(self):
        max_attempts = 5
        delay = 1

        # raise Exception("WHOZZAT")

        for attempt in range(max_attempts):
            if await self.api_client.check_health():
                logger.info("Successfully connected to API")
                return True

            if attempt < max_attempts - 1:
                logger.warning(
                    f"API connection attempt {attempt + 1} failed, retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= 2

        raise RuntimeError("Could not connect to API after multiple attempts")

    def setup(self):
        """Initialize bot and handlers"""
        # Verify API connection first
        asyncio.get_event_loop().run_until_complete(self.verify_api_connection())

        logger.info(f"DEBUG LANGFLOWBOT: {self.application}")
        # self.ai_teacher_handler = AITeacherHandler()
        try:
            logger.info("Creating AITeacherHandler")
            self.ai_teacher_handler = AITeacherHandler(self.httpx_client)
            logger.info("Successfully created AITeacherHandler")
        except Exception as e:
            logger.error(f"Error creating AITeacherHandler: {e}", exc_info=True)
            raise

        # Initialize handlers
        basic_handler = BasicHandler(self.api_client)
        homework_handler = HomeworkHandler(self.api_client)
        submission_handler = SubmissionHandler(self.api_client)
        feedback_handler = FeedbackHandler(self.api_client)

        # Build application
        self.application = (
            Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
        )

        # Add basic handlers
        self.application.add_handler(CommandHandler("start", basic_handler.start))
        self.application.add_handler(CommandHandler("help", basic_handler.help))
        self.application.add_handler(
            CallbackQueryHandler(basic_handler.role_callback, pattern="^role_")
        )

        # Add other handlers
        self.application.add_handler(
            CommandHandler("homework", homework_handler.list_homework)
        )
        self.application.add_handler(
            CallbackQueryHandler(
                homework_handler.handle_submit_button, pattern="^submit_homework$"
            )
        )
        self.application.add_handler(
            ConversationHandler(
                entry_points=[CommandHandler("assign", homework_handler.start_assign)],
                states={
                    AWAITING_CONTENT: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            homework_handler.handle_homework_content,
                        )
                    ],
                    AWAITING_STUDENTS: [
                        CallbackQueryHandler(
                            homework_handler.handle_student_selection,
                            pattern="^(usr_|done)",
                        )
                    ],
                },
                fallbacks=[CommandHandler("cancel", homework_handler.cancel)],
            )
        )

        self.application.add_handler(
            ConversationHandler(
                entry_points=[
                    CommandHandler("submit", submission_handler.start_submit)
                ],
                states={
                    AWAITING_HOMEWORK_SELECTION: [
                        CallbackQueryHandler(
                            submission_handler.handle_homework_selection
                        )
                    ],
                    AWAITING_SUBMISSION: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            submission_handler.handle_submission,
                        )
                    ],
                },
                fallbacks=[CommandHandler("cancel", submission_handler.cancel)],
            )
        )

        self.application.add_handler(
            CommandHandler("feedback", feedback_handler.list_feedback)
        )

        # Add callback handler for main menu button
        self.application.add_handler(
            CallbackQueryHandler(
                basic_handler.return_to_main_menu, pattern="^main_menu$"
            )
        )

        self.application.add_handler(
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        "pending_feedback", feedback_handler.list_pending_feedback
                    )
                ],
                states={
                    AWAITING_SUBMISSION_SELECTION: [
                        CallbackQueryHandler(
                            feedback_handler.handle_submission_selection
                        )
                    ],
                    AWAITING_FEEDBACK: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            feedback_handler.handle_feedback,
                        )
                    ],
                },
                fallbacks=[CommandHandler("cancel", feedback_handler.cancel)],
            )
        )

        self.application.add_handler(self.ai_teacher_handler.get_handler())

    def start(self):
        """Start the bot"""
        # self.application.initialize()
        # await self.application.start()
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    def stop(self):
        """Stop the bot"""
        if self.application:
            self.application.stop()
            # await self.application.shutdown()

        # Close API client
        # await self.api_client.close()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Signal received: {signum}")
    sys.exit(0)


def main():
    """Main function"""
    bot = LangFlowBot()
    bot.setup()

    # Define signal handlers
    # def signal_handler(signum, frame):
    #     asyncio.create_task(bot.stop())

    # Register signal handlers
    signal(SIGINT, signal_handler)
    signal(SIGTERM, signal_handler)
    signal(SIGABRT, signal_handler)

    try:
        bot.start()
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
    finally:
        # await bot.ai_teacher_handler.teacher.close()
        bot.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
