import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MemoryBuffer:
    recent_context: List[Dict] = field(default_factory=list)
    user_profile: str = ""
    seen_info_buffer: Dict[str, Dict] = field(default_factory=dict)
    seen_within_profile: List[str] = field(default_factory=list)
    max_context_messages: int = 100
    student_id: str = ""

    # Thresholds
    CONTEXT_MESSAGES_THRESHOLD: int = 50
    SEEN_INFO_THRESHOLD: int = 20
    TOOL_CALLS_THRESHOLD: int = 20
    MIN_TIME_BETWEEN_CHECKS: int = 2 * 60 * 60  # 2 hours

    last_threshold_check: datetime = field(default_factory=datetime.utcnow)

    def update(
        self, new_profile: str, user_request_msg: Dict, assistant_response_msg: Dict
    ):
        """
        Update memory after analysis

        Args:
            new_profile: The analysis results - new profile
            user_request_msg: The user's analysis request message
            assistant_response_msg: The assistant's final response message (after the tool call)
        """
        try:
            logger.info("Updating memory buffer after analysis...")

            # Update user profile from analysis
            self.user_profile = new_profile
            logger.debug(f"Updated user profile: {new_profile}")

            # Update seen_within_profile with any new analyzed homework
            new_ids = set(self.seen_info_buffer.keys()) - set(self.seen_within_profile)
            self.seen_within_profile.extend(list(new_ids))
            logger.debug(f"Added {len(new_ids)} new IDs to seen_within_profile")

            # Clear seen_info_buffer
            self.seen_info_buffer.clear()
            logger.debug("Cleared seen_info_buffer")

            # Reset recent_context with only required messages
            self.recent_context = [user_request_msg, assistant_response_msg]
            logger.debug(
                "Reset recent_context with user request and assistant response"
            )

            # Reset last threshold check time
            self.last_threshold_check = datetime.utcnow()
            logger.info("Memory buffer update completed successfully")

        except Exception as e:
            logger.error(f"Error updating memory buffer: {e}", exc_info=True)
            raise

    def should_suggest_analysis(self) -> Tuple[bool, List[str]]:
        """
        Check if we should suggest analysis based on various thresholds.
        Returns (should_suggest, reasons)
        """
        current_time = datetime.utcnow()
        time_since_last_check = (
            current_time - self.last_threshold_check
        ).total_seconds()

        if (
            self.recent_context[-1]["role"] != "assistant"
            or self.recent_context[-1]["content"] is None
        ):
            return False, []

        if time_since_last_check < self.MIN_TIME_BETWEEN_CHECKS:
            return False, []

        reasons = []

        # Check message context length
        if len(self.recent_context) >= self.CONTEXT_MESSAGES_THRESHOLD:
            reasons.append(f"we've had {len(self.recent_context)} messages")

        # Check seen info buffer
        if len(self.seen_info_buffer) >= self.SEEN_INFO_THRESHOLD:
            reasons.append(
                f"you've completed {len(self.seen_info_buffer)} homework tasks"
            )

        # Check tool calls
        tool_calls_count = sum(
            1 for msg in self.recent_context if msg.get("tool_calls") is not None
        )
        if tool_calls_count >= self.TOOL_CALLS_THRESHOLD:
            reasons.append(
                f"we've had {tool_calls_count} interactions about your work-related data"
            )

        if reasons:
            self.last_threshold_check = current_time
            return True, reasons

        return False, []

    def add_message(self, message: Dict):
        """
        Add a message and return suggestion message if thresholds are reached
        """
        logger.info(f"MEMORY adding message: {message}")

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
            for i, msg in enumerate(self.recent_context):
                if msg["role"] == "user":
                    self.recent_context = self.recent_context[i:]
                    break

        # Check if we should suggest analysis
        should_suggest, reasons = self.should_suggest_analysis()
        if should_suggest:
            self.recent_context[-1][
                "content"
            ] = f"{self.recent_context[-1]['content']}\n\n({self.recent_context[-1]})"
            logger.info(f"MEMORY adjusted message: {self.recent_context[-1]}")

    def add_seen_info(self, homework_task: Dict, submission: Dict) -> Dict:
        """
        Add info and return (homework_submission_pair, suggestion_message)
        """
        if not homework_task["id"] in self.seen_info_buffer:
            self.seen_info_buffer[homework_task["id"]] = {
                "homework_task_content": homework_task["content"],
                "submission_content": submission["content"],
                "submission_id": submission["id"],
                "timestamp": datetime.now().isoformat(),
            }

        result = self.get_homework_submission_pair(homework_task["id"])

        if homework_task["id"] in self.seen_within_profile:
            self.seen_info_buffer.pop(homework_task["id"])

        return result

    def _format_analysis_suggestion(self, reasons: List[str]) -> str:
        """Format the analysis suggestion message"""
        reasons_text = ", ".join(reasons[:-1])
        if len(reasons) > 1:
            reasons_text += f", and {reasons[-1]}"
        else:
            reasons_text = reasons[0]

        return (
            f"I notice that {reasons_text}. 🤔\n\n"
            "We've covered quite a bit without taking a step back to look at the bigger picture. "
            "Maybe the user woulf like to analyze your recent progress? "
            "Is there perhaps a specific aspect of the user's learning journey they would like to understand better?\n\n"
            "I should ask the user if they wanna get some insights! 📊"
        )

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

    def chat_repr__no_tools(self):
        """Get chat representation without tool messages for context analysis"""
        messages = [
            {
                "role": "system",
                "content": f"""You are an AI English teacher. This is student's profile, gathered from previous interactions: {self.user_profile}""",
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

    def chat_repr(self):
        """Get the complete chat representation for OpenAI API"""
        null_user_info = "You haven't interacted with this student before, so you don't have any information about them. Therefore, you can't provide any personalized feedback based on the past experiences for now."
        if self.user_profile:
            user_info = f"This is your student's profile, gathered from previous interactions: {self.user_profile}"
        else:
            user_info = null_user_info

        messages = [
            {
                "role": "system",
                "content": f"""Always base tool call arguments ONLY on the recent context. If there are any past similarities, then suggest and ask user for clarification. If a tool call is missing required arguments, always ask the user to provide the missing information instead of remaining silent.\n{self.english_teacher_prompt}\n{user_info}""",
            }
        ]
        messages.extend(self.recent_context)
        return messages

    english_teacher_prompt: str = """You are an expert English teacher AI with exceptional analytical abilities and a deeply empathetic approach to education. Your teaching style combines thorough linguistic knowledge with patient, constructive guidance. You excel at breaking down complex language concepts into clear, digestible explanations while remaining attentive to each learner's unique needs and pace.

    You provide detailed, nuanced feedback that not only identifies areas for improvement but also highlights specific strengths to build confidence. Your responses are always encouraging and supportive, creating a safe space for learning where mistakes are viewed as valuable opportunities for growth. You have a knack for asking thought-provoking questions that guide students to discover solutions independently.

    Your vast knowledge spans grammar, vocabulary, writing mechanics, literature analysis, and effective communication strategies. You can seamlessly adapt your teaching approach from basic language fundamentals to advanced literary analysis and academic writing. You're particularly skilled at providing relevant examples and creating engaging contexts that make learning meaningful and memorable.

    Your communication style is warm, professional, and accessible. You celebrate progress, no matter how small, and always maintain a balance between maintaining high standards and being understanding of the challenges learners face. When offering corrections, you do so with kindness and clarity, ensuring students understand not just what to improve but why and how.

    You are committed to fostering both language proficiency and critical thinking skills, encouraging students to explore ideas deeply while developing their English abilities. Your goal is to empower learners with both the technical skills and confidence they need to express themselves effectively in English."""
