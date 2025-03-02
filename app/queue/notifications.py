from .message_types import Message, MessageType
from .producer import NotificationProducer

producer = NotificationProducer()


def notify_homework_assigned(student_tg_id: str, homework_data: dict):
    message = Message(
        type=MessageType.HOMEWORK_ASSIGNED,
        recipient_id=student_tg_id,
        data={
            "title": homework_data.get("title"),
            "description": (
                homework_data.get("description", "")[:100] + "..."
                if len(homework_data.get("description", "")) > 100
                else homework_data.get("description", "")
            ),
        },
    )
    return producer.send_message(message)


def notify_submission_received(teacher_tg_id: str, submission_data: dict):
    message = Message(
        type=MessageType.SUBMISSION_RECEIVED,
        recipient_id=teacher_tg_id,
        data={
            "student_name": submission_data["student_name"],
            "homework_title": submission_data["homework_title"],
            "submission_id": submission_data["submission_id"],
            "content_preview": submission_data["content_preview"],
        },
    )
    return producer.send_message(message)


def notify_feedback_provided(student_tg_id: str, feedback_data: dict):
    message = Message(
        type=MessageType.FEEDBACK_PROVIDED,
        recipient_id=student_tg_id,
        data={
            "homework_title": feedback_data["homework_title"],
            "feedback_id": feedback_data["feedback_id"],
            "content_preview": feedback_data["content_preview"],
            "teacher_name": feedback_data["teacher_name"],
        },
    )
    return producer.send_message(message)
