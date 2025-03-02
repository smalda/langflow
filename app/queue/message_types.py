from datetime import datetime
from enum import Enum
from typing import Any, Dict


class MessageType(str, Enum):
    HOMEWORK_ASSIGNED = "homework_assigned"
    SUBMISSION_RECEIVED = "submission_received"
    FEEDBACK_PROVIDED = "feedback_provided"


class Message:
    def __init__(
        self, type: MessageType, recipient_id: str, data: Dict[str, Any]  # telegram_id
    ):
        self.type = type
        self.recipient_id = recipient_id
        self.data = data
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "recipient_id": self.recipient_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }
