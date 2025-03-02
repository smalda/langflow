"""
1. `GET /feedback/{feedback_id}` - Get specific feedback
2. `POST /feedback/` - Create new feedback
3. `GET /feedback/submission/{submission_id}` - Get all feedback for a submission
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ...db.base import get_db
from ...queue.notifications import notify_feedback_provided
from ...schemas.base import Status
from ...schemas.feedback import Feedback
from ...schemas.homework import HomeworkTask
from ...schemas.submission import Submission
from ...schemas.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{feedback_id}", response_model=Feedback)
def get_feedback_by_id(feedback_id: str, db: Session = Depends(get_db)):
    feedback = db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found"
        )
    return feedback


@router.post("/", response_model=Feedback)
def create_feedback(feedback: Feedback, db: Session = Depends(get_db)):
    # Verify teacher exists and is actually a teacher
    teacher = db.get(User, feedback.teacher_id)
    if not teacher or teacher.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
        )

    # Verify submission exists
    submission = db.get(Submission, feedback.submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    # Verify student matches submission
    if feedback.student_id != submission.student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID doesn't match submission's student",
        )

    # Verify teacher matches submission
    if (
        feedback.teacher_id != submission.teacher_id
        and feedback.teacher_id != "usr_ai_teacher"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teacher ID doesn't match submission's teacher",
        )

    try:
        # Add feedback
        db.add(feedback)

        # Update submission status
        submission = db.get(Submission, feedback.submission_id)
        submission.status = Status.COMPLETED

        # Update homework status
        homework = db.get(HomeworkTask, submission.homework_task_id)

        # Check if all students have completed submissions with feedback
        all_completed = True
        for student_id in homework.student_ids:
            student_submission = db.exec(
                select(Submission).where(
                    Submission.homework_task_id == homework.id,
                    Submission.student_id == student_id,
                )
            ).first()

            if not student_submission or student_submission.status != Status.COMPLETED:
                all_completed = False
                break

        if all_completed:
            homework.status = Status.COMPLETED

        db.commit()

        # Get notification data for student
        student = db.get(User, feedback.student_id)
        teacher = db.get(User, feedback.teacher_id)

        # Notify student about new feedback
        notify_feedback_provided(
            student_tg_id=student.telegram_id,
            feedback_data={
                "homework_title": homework.content.get("title", "Untitled"),
                "feedback_id": feedback.id,
                "content_preview": (
                    feedback.content.get("text", "")[:100] + "..."
                    if len(feedback.content.get("text", "")) > 100
                    else feedback.content.get("text", "")
                ),
                "teacher_name": teacher.tg_handle,
            },
        )

        return feedback

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/submission/{submission_id}", response_model=List[Feedback])
def get_submission_feedback(
    submission_id: str,
    submission_status: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    # Verify submission exists
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    query = select(Feedback).where(Feedback.submission_id == submission_id)

    if submission_status:
        query = query.where(Feedback.status == submission_status)

    feedback_list = db.exec(query.offset(offset).limit(limit)).all()

    return feedback_list


import os
from typing import Dict, List

from openai import OpenAI
from pydantic import BaseModel, Field


class GenerateFeedbackRequest(BaseModel):
    homework_title: str
    homework_description: str
    submission_text: str
    submission_id: str
    chat_context: List[Dict]
    student_id: str = ""


class FeedbackGenerationModel(BaseModel):
    feedback_text: str = Field(
        ..., description="Detailed, constructive feedback on the submission"
    )
    score: int = Field(..., description="Score between 0 and 100")


@router.post("/generate/", response_model=Dict)
def generate_feedback(request: GenerateFeedbackRequest, db: Session = Depends(get_db)):
    # logger.info(f"Received feedback generation request: {request}")

    chat_context = request.chat_context

    _prompt = f"""This is the detailed info on the homework task and submission.

    Homework Task:
    Title: {request.homework_title}
    Description: {request.homework_description}

    Student's Submission (evaluate exactly what is written below):
    {request.submission_text}

    Please provide:
    1. An honest evaluation of the actual submitted content, addressing:
       - Whether the submission meets the basic requirements
       - How well it addresses each point from the homework description
       - The quality and appropriateness of the writing
       - Specific examples from the submission to support your feedback
       - What was done correctly (if anything)
       - What needs improvement
       - Specific steps the student should take to meet the assignment requirements

    3. A numerical score (0-100) that accurately reflects:
       - The completeness of the submission
       - How well it meets the stated requirements
       - The quality of the content provided
       - The appropriateness of the writing style and effort shown

    Note: Base your evaluation solely on the actual submitted content, not on what an ideal submission might contain.
"""

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Modify the last user message
    if chat_context and chat_context[-1]["role"] == "user":
        chat_context[-1]["content"] = f"{chat_context[-1]['content']}\n{_prompt}"

    import json

    logger.info(f"Submission generation messages: {json.dumps(chat_context, indent=4)}")

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=chat_context,
            response_format=FeedbackGenerationModel,
        )

        feedback_content = completion.choices[0].message.parsed

        # Create a Feedback instance
        feedback = Feedback(
            student_id=request.student_id,
            teacher_id="usr_ai_teacher",
            submission_id=request.submission_id,
            content={
                "text": feedback_content.feedback_text,
                "score": feedback_content.score,
                "homework_title": request.homework_title,
            },
            status=Status.COMPLETED,
        )

        # Save to database using the create_feedback endpoint
        # db.add(feedback)
        # db.commit()
        # db.refresh(feedback)

        result = create_feedback(feedback=feedback, db=db)

        logger.info(f"Created feedback: {result.id}")

        # Notify student about new feedback
        # notify_feedback_provided(
        #     student_tg_id=request.telegram_id,
        #     feedback_data={
        #         "homework_title": request.homework_title,
        #         "feedback_id": feedback.id,
        #         "content_preview": feedback.content.get("text", "")[:100] + "..."
        #                 if len(feedback.content.get("text", "")) > 100
        #                 else feedback.content.get("text", ""),
        #         "teacher_name": "AI Teacher"
        #     }
        # )

        return {
            "feedback_text": feedback_content.feedback_text,
            "score": feedback_content.score,
            "homework_title": request.homework_title,
        }

    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
