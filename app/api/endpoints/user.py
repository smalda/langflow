"""
1. `/users/me` - Get current user by telegram handle
2. `/users/{user_id}` - Get user by ID
3. `/users/by_handle/{tg_handle}` - Get user by telegram handle
4. `/users/` - Get all users (with optional role filter)
5. `/users/students/` - Get all students
6. `/users/teachers/` - Get all teachers
7. `/users/` (POST) - Create new user
"""

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, or_, select

from ...db.base import get_db
from ...schemas.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

# @router.get("/me", response_model=User)
# def get_current_user(
#     tg_handle: str,  # This would come from auth/security in real app
#     db: Session = Depends(get_db)
# ):
#     user = db.exec(
#         select(User).where(User.tg_handle == tg_handle)
#     ).first()

#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
#     return user


@router.get("/by_telegram_id/{telegram_id}", response_model=User)
def get_user_by_telegram_id(telegram_id: str, db: Session = Depends(get_db)):
    user = db.exec(select(User).where(User.telegram_id == telegram_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/by_telegram_handle/{tg_handle}", response_model=User)
def get_user_by_telegram_handle(
    tg_handle: str,  # This would come from auth/security in real app
    db: Session = Depends(get_db),
):
    user = db.exec(select(User).where(User.tg_handle == tg_handle)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("/{user_id}", response_model=User)
def get_user_by_id(user_id: str, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


# @router.get("/by_handle/{tg_handle}", response_model=User)
# def get_user_by_handle(
#     tg_handle: str,
#     db: Session = Depends(get_db)
# ):
#     user = db.exec(
#         select(User).where(User.tg_handle == tg_handle)
#     ).first()

#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
#     return user


@router.get("/", response_model=List[User])
async def get_users(
    role: Optional[UserRole] = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = select(User)
    if role:
        query = query.where(User.role == role)

    users = db.exec(query.offset(offset).limit(limit)).all()
    return users


@router.get("/students/", response_model=List[User])
def get_all_students(offset: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    students = db.exec(
        select(User).where(User.role == UserRole.STUDENT).offset(offset).limit(limit)
    ).all()
    return students


@router.get("/teachers/", response_model=List[User])
def get_all_teachers(offset: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    teachers = db.exec(
        select(User).where(User.role == UserRole.TEACHER).offset(offset).limit(limit)
    ).all()
    return teachers


@router.post("/", response_model=User)
async def create_user(user: User, db: Session = Depends(get_db)):
    if user.role not in [UserRole.STUDENT, UserRole.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user role"
        )

    if user.tg_handle == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot have an empty telegram handle for user",
        )

    # Check if user with this handle already exists
    existing_user = db.exec(
        select(User).where(
            or_(User.tg_handle == user.tg_handle, User.telegram_id == user.telegram_id)
        )
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this telegram handle or ID already exists",
        )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


import json
from typing import Dict, List

from openai import OpenAI
from pydantic import BaseModel, Field

from ...schemas.feedback import Feedback
from ...schemas.homework import HomeworkTask
from ...schemas.submission import Submission


class UserAnalysisModel(BaseModel):
    new_user_profile: str = Field(
        ..., description="Updated user profile based on recent learning activities"
    )
    user_growth_story: str = Field(
        ..., description="Narrative of user's learning progress"
    )
    user_areas_of_improvement: str = Field(
        ..., description="List of areas where user can improve"
    )
    user_specific_aspect_analysis: str = Field(
        ..., description="Analysis of user's specific aspect defined in the prompt"
    )


class AnalysisRequest(BaseModel):
    user_id: str
    chat_context: List[Dict]
    current_profile: str
    seen_within_profile: List[str]
    aspect_to_analyze: str


@router.post("/analysis/{user_id}", response_model=Dict)
def analyze_user(request: AnalysisRequest, db: Session = Depends(get_db)):
    """Analyze user's progress and generate insights"""
    try:
        user_id = request.user_id

        # 1. Get all user's data
        submissions = db.exec(
            select(Submission).where(Submission.student_id == user_id)
        ).all()

        homeworks = db.exec(
            select(HomeworkTask).where(HomeworkTask.student_ids.contains([user_id]))
        ).all()

        feedbacks = db.exec(
            select(Feedback).where(Feedback.student_id == user_id)
        ).all()

        logger.info(
            f"User {user_id} has {len(submissions)} submissions, {len(homeworks)} homeworks, and {len(feedbacks)} feedbacks"
        )

        # 2. Filter to new exercises
        filtered_exercises = []
        unseen_homework_ids = []
        for homework in homeworks:
            if homework.id not in request.seen_within_profile:
                # Find related submission and feedback
                submission = next(
                    (s for s in submissions if s.homework_task_id == homework.id), None
                )
                feedback = (
                    next(
                        (f for f in feedbacks if f.submission_id == submission.id), None
                    )
                    if submission
                    else None
                )

                if submission and feedback:  # Only include complete cycles
                    filtered_exercises.append(
                        {
                            "homework": homework.content,
                            "submission": submission.content,
                            "feedback": feedback.content,
                        }
                    )
                    unseen_homework_ids.append(homework.id)

        logger.info(f"Filtered exercises len: {len(filtered_exercises)}")

        # 3. Prepare analysis prompt
        _prompt = f"""Based on:
            Current Profile: {request.current_profile}
            Recent Learning Activities: {json.dumps(filtered_exercises, indent=2)}
            Aspect to Analyze: {request.aspect_to_analyze}

Please provide:
1. Updated profile reflecting recent progress (new_user_profile)
2. Concrete growth story based on actual activities (user_growth_story)
3. Specific improvement areas supported by activity data (user_areas_of_improvement)
4. Analysis of {request.aspect_to_analyze} backed by recent performance (user_specific_aspect_analysis)

Only include information that can be directly supported by the provided data.
If certain aspects lack data, acknowledge the limitations.
"""

        # 4. Generate analysis
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        chat_context = request.chat_context
        if chat_context and chat_context[-1]["role"] == "user":
            chat_context[-1]["content"] = f"{chat_context[-1]['content']}\n{_prompt}"

        completion = client.beta.chat.completions.parse(
            model="gpt-4o", messages=chat_context, response_format=UserAnalysisModel
        )

        logger.info(f"Analysis generated for user {user_id}")

        analysis = completion.choices[0].message.parsed

        return {
            "profile": analysis.new_user_profile,
            "growth_story": analysis.user_growth_story,
            "areas_of_improvement": analysis.user_areas_of_improvement,
            "specific_aspect_analysis": analysis.user_specific_aspect_analysis,
            "analyzed_homework_ids": unseen_homework_ids,
        }

    except Exception as e:
        logger.error(f"Error analyzing user: {e}")
        raise HTTPException(status_code=500, detail=str(e))
