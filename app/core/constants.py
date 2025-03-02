from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"


class HomeworkStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FEEDBACK_RECEIVED = "feedback_received"


class SubmissionType(str, Enum):
    HOMEWORK = "homework"
    FEEDBACK = "feedback"


class FeedbackStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
