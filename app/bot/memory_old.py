from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class MemoryBuffer:
    recent_context: List[Dict] = field(default_factory=list)
    user_profile: str = ""
    seen_info_buffer: Dict[str, Dict] = field(default_factory=dict)
    seen_within_profile: List[str] = field(default_factory=list)
    max_context_messages: int = 100
    student_id: str = ""

    def add_message(self, message: Dict):
        """Add a complete message (with all metadata) to recent context"""
        if (
            message["role"] == "assistant"
            and message["content"] is None
            and "tool_calls" not in message
        ):
            self.recent_context.append(
                {
                    "role": "assistant",
                    "content": "(I encountered an error, but I must recover and resume the conversation immediately)",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            self.recent_context.append(message)

        if len(self.recent_context) > self.max_context_messages:
            # Find the first user message and remove everything before it
            for i, msg in enumerate(self.recent_context):
                if msg["role"] == "user":
                    self.recent_context = self.recent_context[i:]
                    break

    def add_seen_info(self, homework_task: Dict, submission: Dict) -> Dict:
        """Add a homework-submission pair to seen info"""
        if not homework_task["id"] in self.seen_info_buffer:
            self.seen_info_buffer[homework_task["id"]] = {
                "homework_task_content": homework_task["content"],
                "submission_content": submission["content"],
                "submission_id": submission["id"],
                "timestamp": datetime.now().isoformat(),
            }

        return self.get_homework_submission_pair(homework_task["id"])

    def get_homework_submission_pair(self, homework_task_id: str) -> Dict:
        """Get a homework-submission pair from seen info"""
        if homework_task_id in self.seen_info_buffer:
            seen_info = self.seen_info_buffer[homework_task_id]
            return {
                "homework_task_title": seen_info["homework_task_content"]["title"],
                "homework_task_description": seen_info["homework_task_content"][
                    "description"
                ],
                "submission_text": seen_info["submission_content"]["text"],
                "submission_id": seen_info["submission_id"],
                "timestamp": seen_info["timestamp"],
            }
        return {}

    def chat_repr(self):
        """Get the complete chat representation for OpenAI API"""
        messages = [
            {
                "role": "system",
                "content": f"""Always base tool call arguments ONLY on the recent context. If there are any past similarities, then suggest and ask user for clarification. If a tool call is missing required arguments, always ask the user to provide the missing information instead of remaining silent.
You are an AI English teacher. This is your student's profile, gathered from previous interactions:
{self.user_profile}""",
            }
        ]
        messages.extend(self.recent_context)
        return messages

    def chat_repr__no_tools(self):
        """Get chat representation without tool messages for context analysis"""
        messages = [
            {
                "role": "system",
                "content": f"""You are an AI English teacher. This is student's profile, gathered from previous interactions:
{self.user_profile}""",
            }
        ]
        messages.extend(
            [
                message
                for message in self.recent_context
                if message["role"] != "tool" and message["content"] is not None
            ]
        )
        return messages
