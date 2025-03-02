import logging

from sqlmodel import Session, select

from ..schemas.user import User, UserRole

logger = logging.getLogger(__name__)


async def create_ai_teacher(engine):
    """Create AI teacher user if it doesn't exist"""
    try:
        with Session(engine) as session:
            # Check if AI teacher already exists
            statement = select(User).where(User.id == "usr_ai_teacher")
            existing_teacher = session.exec(statement).first()

            if not existing_teacher:
                logger.info("Creating AI teacher user...")
                ai_teacher = User(
                    id="usr_ai_teacher",
                    tg_handle="AI_teacher",
                    telegram_id="1234567890",
                    role=UserRole.TEACHER,
                    meta={"is_ai": True},
                )
                session.add(ai_teacher)
                session.commit()
                logger.info("AI teacher user created successfully")
            else:
                logger.info("AI teacher user already exists")

    except Exception as e:
        logger.error(f"Error creating AI teacher: {e}")
        raise
