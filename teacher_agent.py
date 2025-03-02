import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Self, Set

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


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
        # Construct messages array
        messages = [
            {
                "role": "system",
                "content": f"""If a tool call is missing required arguments, always ask the user to provide the missing information instead of remaining silent.\nYou are an AI English teacher. This is your student's profile, gathered from previous interactions:
                {self.user_profile}""",
            }
        ]

        # Add recent context
        messages.extend(self.recent_context)

        return messages

    def chat_repr__no_tools(self):
        # Construct messages array
        messages = [
            {
                "role": "system",
                "content": f"""You are an AI English teacher. This is student's profile, gathered from previous interactions:
                {self.user_profile}""",
            }
        ]

        # Add recent context
        messages.extend(
            [
                message
                for message in self.recent_context
                if message["role"] != "tool" and message["content"] is not None
            ]
        )

        return messages


class TeacherAgent:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.memory = MemoryBuffer()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "assign_homework",
                    "description": "Create a new homework assignment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "homework_topic": {
                                "type": "string",
                                "description": "Topic of the homework task",
                            },
                            "language_level": {
                                "type": "string",
                                "enum": ["A1", "A2", "B1", "B2", "C1", "C2"],
                                "description": "Target language proficiency level",
                            },
                            "student_stress_level": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "Consider student's current workload",
                            },
                        },
                        "required": [
                            "homework_topic",
                            "language_level",
                            "student_stress_level",
                        ],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_homework_by_title",
                    "description": "Get info on a homework task by its title",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "homework_title": {
                                "type": "string",
                                "description": "Full or partial title of the homework",
                            }
                        },
                        "required": ["homework_title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_submission_by_homework_title_without_final_feedback",
                    "description": "Get user's submission for a homework task when the user isn't directly asking to receive a mark. Should be used when the user wants to discuss the submission.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "homework_title": {
                                "type": "string",
                                "description": "Full or partial title of the homework",
                            }
                        },
                        "required": ["homework_title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "give_final_feedback_for_submission_by_homework_title",
                    "description": "Provide feedback for a submission given homework title when the user directly asks to receive a mark. Be critical but very constructive. Pay attention to the details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "homework_title": {
                                "type": "string",
                                "description": "Full or partial title of the homework",
                            }
                        },
                        "required": ["homework_title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_user_profile",
                    "description": "Analyze user based on all available information. Also provide specific analysis for the aspect that the user is interested in (should always be provided)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "aspect_to_analyze": {
                                "type": "string",
                            }
                        },
                        "required": ["aspect_to_analyze"],
                    },
                },
            },
        ]

    def assign_homework(
        self, homework_topic: str, language_level: str, student_stress_level: str
    ) -> str:
        """Real implementation making API call"""
        missing_args = []
        if not homework_topic:
            missing_args.append("homework_topic")
        if not language_level:
            missing_args.append("language_level")
        if not student_stress_level:
            missing_args.append("student_stress_level")

        if missing_args:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Missing arguments: {', '.join(missing_args)}. Ask the user to provide them.",
                }
            )

        import httpx

        timeout = httpx.Timeout(60.0, read=60.0)

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    "http://localhost:8000/homework/generate/",
                    json={
                        "homework_topic": homework_topic,
                        "language_level": language_level,
                        "student_stress_level": student_stress_level,
                        "chat_context": self.memory.chat_repr__no_tools(),
                        "student_id": self.memory.student_id,
                    },
                )

            response.raise_for_status()
            generated_content = response.json()

            # Create homework task format
            return json.dumps(generated_content)

        except Exception as e:
            print(f"Error calling homework generation API: {e}")
            # Fallback to mock in case of error
            return json.dumps({"status": "error", "message": str(e)})

    def get_homework_by_title(self, homework_title: str) -> str:
        missing_args = []
        if not homework_title:
            missing_args.append("homework_title")
        if missing_args:
            return json.dumps(
                {
                    "error": f"Missing arguments: {', '.join(missing_args)}. Ask the user to provide them."
                }
            )

        import httpx

        try:
            with httpx.Client(timeout=30.0) as client:
                # First get all student's homework
                response = client.get(
                    f"http://localhost:8000/homework/student/{self.memory.student_id}"
                )
                response.raise_for_status()
                all_homework = response.json()

                for homework in all_homework:
                    # Check if this homework's title matches what we're looking for
                    if (
                        homework_title.lower()
                        in homework.get("content", {}).get("title", "").lower()
                    ):
                        result = {
                            "homework_task_title": homework.get("content", {}).get(
                                "title", ""
                            ),
                            "homework_task_description": homework.get(
                                "content", {}
                            ).get("description", ""),
                        }

                        return json.dumps(result)

                return json.dumps(
                    {
                        "homework_task_title": None,
                        "homework_task_description": None,
                    }
                )

        except Exception as e:
            print(f"Error searching submissions: {e}")
            return json.dumps(
                {
                    "error": str(e),
                    "homework_task_title": None,
                    "homework_task_description": None,
                }
            )

    def get_submission_by_homework_title_without_final_feedback(
        self, homework_title: str
    ) -> str:
        """Real implementation making API call"""
        missing_args = []
        if not homework_title:
            missing_args.append("homework_title")
        if missing_args:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Missing arguments: {', '.join(missing_args)}. Ask the user to provide them.",
                }
            )

        import httpx

        try:
            with httpx.Client(timeout=30.0) as client:
                # First get all student's submissions
                response = client.get(
                    f"http://localhost:8000/submissions/student/{self.memory.student_id}"
                )
                response.raise_for_status()
                all_submissions = response.json()

                # For each submission, get its homework task and check the title
                for submission in all_submissions:
                    homework_task_id = submission["homework_task_id"]
                    if homework_task_id not in self.memory.seen_info_buffer:
                        homework_response = client.get(
                            f"http://localhost:8000/homework/{homework_task_id}"
                        )
                        homework_task = homework_response.json()

                        # Add to memory
                        homework_submission_pair = self.memory.add_seen_info(
                            homework_task, submission
                        )
                    else:
                        homework_submission_pair = (
                            self.memory.get_homework_submission_pair(homework_task_id)
                        )

                    # Check if this homework's title matches what we're looking for
                    if (
                        homework_title.lower()
                        in homework_submission_pair.get(
                            "homework_task_title", ""
                        ).lower()
                    ):
                        print(f"Found matching pair: {homework_submission_pair}")
                        result = {
                            "homework_task_title": homework_submission_pair[
                                "homework_task_title"
                            ],
                            "homework_task_description": homework_submission_pair[
                                "homework_task_description"
                            ],
                            "submission_text": homework_submission_pair[
                                "submission_text"
                            ],
                            "submission_id": homework_submission_pair["submission_id"],
                        }

                        return json.dumps(result)

                return json.dumps(
                    {
                        "homework_task_title": None,
                        "homework_task_description": None,
                        "submission_text": None,
                        "submission_id": None,
                    }
                )

        except Exception as e:
            print(f"Error searching submissions: {e}")
            return json.dumps(
                {
                    "error": str(e),
                    "homework_task_title": None,
                    "homework_task_description": None,
                    "submission_text": None,
                    "submission_id": None,
                }
            )

    def give_final_feedback_for_submission_by_homework_title(
        self, homework_title: str
    ) -> str:
        """Real implementation making API calls"""
        missing_args = []
        if not homework_title:
            missing_args.append("homework_title")
        if missing_args:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Missing arguments: {', '.join(missing_args)}. Ask the user to provide them.",
                }
            )

        import httpx

        try:
            # First get the submission info
            submission_info = json.loads(
                self.get_submission_by_homework_title_without_final_feedback(
                    homework_title
                )
            )

            if not submission_info.get("homework_task_title"):
                return json.dumps(
                    {
                        "error": f"No submission found for this homework title, with another error generated: {submission_info['error']}"
                    }
                )

            # Now generate feedback
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    "http://localhost:8000/feedback/generate/",
                    json={
                        "homework_title": submission_info["homework_task_title"],
                        "homework_description": submission_info[
                            "homework_task_description"
                        ],
                        "submission_text": submission_info["submission_text"],
                        "chat_context": self.memory.chat_repr__no_tools(),
                        "student_id": self.memory.student_id,
                        "submission_id": submission_info["submission_id"],
                    },
                )

                response.raise_for_status()
                feedback_data = response.json()

                return json.dumps(
                    {
                        "homework_title": feedback_data["homework_title"],
                        "submission_text": submission_info["submission_text"],
                        "feedback_text": feedback_data["feedback_text"],
                        "score": feedback_data["score"],
                    }
                )

        except Exception as e:
            print(f"Error generating feedback: {e}")
            return json.dumps({"error": str(e)})

    def analyze_user_profile(self, aspect_to_analyze: str) -> str:
        """Real implementation making API calls"""
        missing_args = []
        if not aspect_to_analyze:
            missing_args.append("aspect_to_analyze")
        if missing_args:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Missing arguments: {', '.join(missing_args)}. Ask the user to provide them.",
                }
            )

        import httpx

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"http://localhost:8000/users/analysis/{self.memory.student_id}",
                    json={
                        "user_id": self.memory.student_id,
                        "chat_context": self.memory.chat_repr__no_tools(),
                        "current_profile": self.memory.user_profile,
                        "seen_within_profile": list(self.memory.seen_within_profile),
                        "aspect_to_analyze": aspect_to_analyze,
                    },
                )

                response.raise_for_status()
                analysis_data = response.json()

                # Update memory with new profile
                self.memory.user_profile = analysis_data["profile"]

                # Add analyzed homework IDs to seen set
                if "analyzed_homework_ids" in analysis_data:
                    self.memory.seen_within_profile.extend(
                        analysis_data["analyzed_homework_ids"]
                    )

                return json.dumps(
                    {
                        "updated_profile": analysis_data["profile"],
                        "growth_story": analysis_data["growth_story"],
                        "areas_of_improvement": analysis_data["areas_of_improvement"],
                        "specific_aspect_analysis": analysis_data[
                            "specific_aspect_analysis"
                        ],
                    }
                )

        except Exception as e:
            print(f"Error analyzing user: {e}")
            return json.dumps({"error": str(e)})

    def process_message(self, user_message: str) -> str:
        """Process a message from the user"""

        def log_messages(msgs, label="Messages"):
            print(f"\n=== {label} ===")
            print(json.dumps(msgs, indent=2))

        # Create the user message
        user_msg = {"role": "user", "content": user_message}

        # Add to memory
        self.memory.add_message(user_msg)

        # Construct messages
        messages = self.memory.chat_repr()

        log_messages(messages, "Initial messages")

        try:
            # Get initial completion
            completion = self.client.chat.completions.create(
                model="gpt-4o", messages=messages, tools=self.tools
            )

            assistant_message = completion.choices[0].message

            # Create assistant message dict with all metadata
            assistant_msg = {"role": "assistant", "content": assistant_message.content}

            if assistant_message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_message.tool_calls
                ]

                # Add assistant message to memory and messages array
                self.memory.add_message(assistant_msg)
                messages.append(assistant_msg)

                log_messages(messages, "After adding assistant message with tool calls")

                # Handle each tool call
                for tool_call in assistant_message.tool_calls:
                    args = json.loads(tool_call.function.arguments)
                    print(
                        f"\nExecuting tool {tool_call.function.name} with args:", args
                    )

                    # Execute the appropriate tool
                    if tool_call.function.name == "assign_homework":
                        result = self.assign_homework(
                            args.get("homework_topic", None),
                            args.get("language_level", None),
                            args.get("student_stress_level", None),
                        )
                    elif (
                        tool_call.function.name
                        == "get_submission_by_homework_title_without_final_feedback"
                    ):
                        result = self.get_submission_by_homework_title_without_final_feedback(
                            args.get("homework_title", None)
                        )
                    elif tool_call.function.name == "get_homework_by_title":
                        result = self.get_homework_by_title(
                            args.get("homework_title", None)
                        )
                    elif (
                        tool_call.function.name
                        == "give_final_feedback_for_submission_by_homework_title"
                    ):
                        result = (
                            self.give_final_feedback_for_submission_by_homework_title(
                                args.get("homework_title", None)
                            )
                        )
                    elif tool_call.function.name == "analyze_user_profile":
                        result = self.analyze_user_profile(
                            args.get("aspect_to_analyze", None)
                        )

                    # Create and add tool message
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": str(result),
                    }
                    self.memory.add_message(tool_msg)
                    messages.append(tool_msg)

                    log_messages(
                        messages, f"After adding {tool_call.function.name} response"
                    )

                # Get final response
                final_completion = self.client.chat.completions.create(
                    model="gpt-4o", messages=messages, tools=self.tools
                )

                print(
                    "\nFinal completion content:",
                    final_completion.choices[0].message.content,
                )

                final_msg = {
                    "role": "assistant",
                    "content": final_completion.choices[0].message.content,
                }
                self.memory.add_message(final_msg)
                response = final_msg["content"]

                log_messages(messages, "Final message state")
            else:
                # No tool calls, just add the assistant message
                self.memory.add_message(assistant_msg)
                response = assistant_message.content

            return response

        except Exception as e:
            print(f"Error processing message: {str(e)}")
            log_messages(messages, "Message state at error")
            raise
