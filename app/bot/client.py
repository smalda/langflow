import os
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

from .retrying_httpx_client import AsyncRetryingClient

load_dotenv()

import logging

logger = logging.getLogger(__name__)


class APIClient:
    def __init__(self, client: AsyncRetryingClient):

        self.client = client
        self.default_pagination = {"offset": 0, "limit": 100}

    async def check_health(self) -> bool:
        try:
            logger.info("Checking API health...")
            response = await self.client.get("/health")
            logger.info(f"Health check response: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_or_create_user(
        self, telegram_id: str, username: str, role: str
    ) -> Dict:
        # No pagination needed for single user operations
        try:
            response = await self.client.get(
                f"/users/by_telegram_handle/{username}", max_retries=1  # Only try once
            )
            if response.status_code == 200:
                return response.json()
        except httpx.HTTPError:
            pass

        user_data = {"tg_handle": username, "telegram_id": telegram_id, "role": role}
        response = await self.client.post("/users/", json=user_data)
        return response.json()

    async def get_user_by_telegram_id(
        self, telegram_id: str, max_retries: Optional[int] = None
    ) -> Dict:
        # No pagination needed for single user
        response = await self.client.get(
            f"/users/by_telegram_id/{telegram_id}", max_retries=max_retries
        )
        return response.json()

    async def get_all_students(self) -> List[Dict]:
        response = await self.client.get(
            "/users/students/", params=self.default_pagination
        )
        return response.json()

    async def get_all_teachers(self) -> List[Dict]:
        response = await self.client.get(
            "/users/teachers/", params=self.default_pagination
        )
        return response.json()

    async def get_homework_for_student(self, student_id: str) -> List[Dict]:
        # Get base homework list
        response = await self.client.get(
            f"/homework/student/{student_id}", params=self.default_pagination
        )
        homework_list = response.json()

        # Get base homework list
        response = await self.client.get(
            f"/homework/student/{student_id}", params=self.default_pagination
        )
        homework_list = response.json()

        # Collect unique teacher IDs
        teacher_ids = {hw["teacher_id"] for hw in homework_list}

        # Get teacher information for each unique teacher ID
        teachers_info = {}
        for teacher_id in teacher_ids:
            try:
                teacher_response = await self.client.get(f"/users/{teacher_id}")
                if teacher_response.status_code == 200:
                    teacher_data = teacher_response.json()
                    teachers_info[teacher_id] = teacher_data
            except Exception as e:
                logger.error(f"Error fetching teacher info for {teacher_id}: {e}")

        # Enrich homework data with teacher information
        enriched_homework = []
        for hw in homework_list:
            teacher_info = teachers_info.get(hw["teacher_id"], {})
            enriched_hw = {
                **hw,
                "teacher_handle": teacher_info.get("tg_handle", "Unknown"),
                "teacher_telegram_id": teacher_info.get("telegram_id", "Unknown"),
            }
            enriched_homework.append(enriched_hw)

        return enriched_homework

    async def get_homework_for_teacher(self, teacher_id: str) -> List[Dict]:
        response = await self.client.get(
            f"/homework/teacher/{teacher_id}", params=self.default_pagination
        )
        return response.json()

    # async def assign_homework(self, data: Dict[str, Any]) -> Dict:
    # response = await self.client.post("/homework/assign/", json=data)
    # return response.json()

    async def assign_homework(self, data: Dict[str, Any]) -> Dict:
        logger.info(f"Sending homework assignment request with data: {data}")
        response = await self.client.post("/homework/assign/", json=data)
        logger.info(f"Received response: {response.status_code}")
        logger.info(f"Response content: {response.content}")
        return response.json()

    async def submit_homework(self, data: Dict[str, Any]) -> Dict:
        response = await self.client.post("/submissions/", json=data)
        return response.json()

    async def get_homework_by_id(self, homework_id: str) -> Dict:
        # No pagination needed for single submission
        response = await self.client.get(f"/homework/{homework_id}")
        return response.json()

    async def get_submission_by_id(self, submission_id: str) -> Dict:
        # No pagination needed for single submission
        response = await self.client.get(f"/submissions/{submission_id}")
        return response.json()

    async def get_student_submissions(self, student_id: str) -> List[Dict]:
        response = await self.client.get(
            f"/submissions/student/{student_id}", params=self.default_pagination
        )
        return response.json()

    async def get_teacher_submissions(self, teacher_id: str) -> List[Dict]:
        # Get base submissions list
        response = await self.client.get(
            f"/submissions/teacher/{teacher_id}", params=self.default_pagination
        )
        submissions_list = response.json()

        # Collect unique student IDs and homework IDs
        student_ids = {sub["student_id"] for sub in submissions_list}
        homework_ids = {sub["homework_task_id"] for sub in submissions_list}

        # Get student information
        students_info = {}
        for student_id in student_ids:
            try:
                student_response = await self.client.get(f"/users/{student_id}")
                if student_response.status_code == 200:
                    student_data = student_response.json()
                    students_info[student_id] = student_data
            except Exception as e:
                logger.error(f"Error fetching student info for {student_id}: {e}")

        # Get homework information
        homework_info = {}
        for homework_id in homework_ids:
            try:
                homework_response = await self.client.get(f"/homework/{homework_id}")
                if homework_response.status_code == 200:
                    homework_data = homework_response.json()
                    homework_info[homework_id] = homework_data
            except Exception as e:
                logger.error(f"Error fetching homework info for {homework_id}: {e}")

        # Enrich submissions data
        enriched_submissions = []
        for sub in submissions_list:
            student_info = students_info.get(sub["student_id"], {})
            homework_data = homework_info.get(sub["homework_task_id"], {})

            enriched_sub = {
                **sub,
                "student_handle": student_info.get("tg_handle", "Unknown"),
                "student_telegram_id": student_info.get("telegram_id", "Unknown"),
                "homework_title": homework_data.get("content", {}).get(
                    "title", "Untitled"
                ),
            }
            enriched_submissions.append(enriched_sub)

        return enriched_submissions

    async def provide_feedback(self, data: Dict[str, Any]) -> Dict:
        response = await self.client.post("/feedback/", json=data)
        return response.json()

    async def get_submission_feedback(self, submission_id: str) -> List[Dict]:
        # First get the basic feedback list
        feedback_response = await self.client.get(
            f"/feedback/submission/{submission_id}", params=self.default_pagination
        )
        feedback_list = feedback_response.json()

        if not feedback_list:
            return []

        # Get the submission details to get homework info
        try:
            submission_response = await self.client.get(f"/submissions/{submission_id}")
            submission = submission_response.json()

            # Get homework details
            homework_response = await self.client.get(
                f"/homework/{submission['homework_task_id']}"
            )
            homework = homework_response.json()

            # Enrich each feedback item with homework and submission info
            enriched_feedback = []
            for feedback in feedback_list:
                enriched_feedback_item = {
                    **feedback,
                    "homework_task": homework,
                    "submission": submission,
                }
                enriched_feedback.append(enriched_feedback_item)

            return enriched_feedback

        except Exception as e:
            logger.error(f"Error enriching feedback data: {e}")
            return feedback_list  # Return basic feedback if enrichment fails

    async def close(self):
        await self.client.aclose()
