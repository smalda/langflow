from fastapi import APIRouter

from .endpoints import feedback, homework, submission, user

api_router = APIRouter()

api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(homework.router, prefix="/homework", tags=["homework"])
api_router.include_router(
    submission.router, prefix="/submissions", tags=["submissions"]
)
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
