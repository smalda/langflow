import json
import logging
import os
from typing import Dict, List, Optional

from openai import AsyncOpenAI

from app.bot.memory import MemoryBuffer
from app.bot.retrying_httpx_client import AsyncRetryingClient

logger = logging.getLogger(__name__)


class AITeacher:
    def __init__(self, api_key: str, client: AsyncRetryingClient):
        self.client = AsyncOpenAI(api_key=api_key)
        self.api_client = client
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

    async def process_message(self, message: str, memory: MemoryBuffer) -> str:
        """Process a message using the given memory buffer"""

        def log_messages(msgs, label="Messages"):
            logger.info(f"\n=== {label} ===")
            logger.info(json.dumps(msgs, indent=2))

        user_msg = {"role": "user", "content": message}
        memory.add_message(user_msg)

        messages = memory.chat_repr()
        log_messages(messages, "Initial messages")

        try:
            # Get initial completion
            completion = await self.client.chat.completions.create(
                model="gpt-4", messages=messages, tools=self.tools
            )

            assistant_message = completion.choices[0].message
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

                memory.add_message(assistant_msg)
                messages.append(assistant_msg)
                log_messages(messages, "After adding assistant message with tool calls")

                # Handle each tool call
                for tool_call in assistant_message.tool_calls:
                    result = await self._execute_tool(tool_call, memory)

                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": result,
                    }
                    memory.add_message(tool_msg)
                    messages.append(tool_msg)

                    log_messages(
                        messages, f"After adding {tool_call.function.name} response"
                    )

                # Get final response
                final_completion = await self.client.chat.completions.create(
                    model="gpt-4", messages=messages, tools=self.tools
                )

                final_msg = {
                    "role": "assistant",
                    "content": final_completion.choices[0].message.content,
                }

                logger.info(f"===TOOL CALL1===: {tool_msg}")
                logger.info(f"===FINAL RESPONSE===: {final_msg}")

                if tool_call.function.name == "analyze_user_profile":
                    memory.update(
                        json.loads(tool_msg["content"])["updated_profile"],
                        user_msg,
                        final_msg,
                    )

                else:
                    memory.add_message(final_msg)
                return final_msg["content"]
            else:
                memory.add_message(assistant_msg)
                return assistant_msg["content"]

        except Exception as e:
            logger.info(f"Error processing message: {str(e)}")
            log_messages(messages, "Message state at error")
            raise

    async def close(self):
        """Properly close the async client when done with the AITeacher instance"""
        await self.api_client.aclose()

    async def _execute_tool(self, tool_call: Dict, memory: MemoryBuffer) -> str:
        """Execute the appropriate tool based on the tool call"""
        args = json.loads(tool_call.function.arguments)

        if tool_call.function.name == "assign_homework":
            return await self._assign_homework(
                args.get("homework_topic"),
                args.get("language_level"),
                args.get("student_stress_level"),
                memory,
            )
        elif tool_call.function.name == "get_homework_by_title":
            return await self._get_homework_by_title(args.get("homework_title"), memory)
        elif (
            tool_call.function.name
            == "get_submission_by_homework_title_without_final_feedback"
        ):
            return await self._get_submission(args.get("homework_title"), memory)
        elif (
            tool_call.function.name
            == "give_final_feedback_for_submission_by_homework_title"
        ):
            return await self._give_feedback(args.get("homework_title"), memory)
        elif tool_call.function.name == "analyze_user_profile":
            return await self._analyze_user(args.get("aspect_to_analyze"), memory)
        else:
            raise ValueError(f"Unknown tool: {tool_call.function.name}")

    async def _assign_homework(
        self,
        homework_topic: Optional[str],
        language_level: Optional[str],
        student_stress_level: Optional[str],
        memory: MemoryBuffer,
    ) -> str:
        """Generate and assign homework through API"""
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

        try:
            response = await self.api_client.post(
                "/homework/generate/",
                json={
                    "homework_topic": homework_topic,
                    "language_level": language_level,
                    "student_stress_level": student_stress_level,
                    "chat_context": memory.chat_repr__no_tools(),
                    "student_id": memory.student_id,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return json.dumps(response.json())

        except Exception as e:
            logger.info(f"Error calling homework generation API: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    async def _get_homework_by_title(
        self, homework_title: Optional[str], memory: MemoryBuffer
    ) -> str:
        """Retrieve homework information by title"""
        if not homework_title:
            return json.dumps(
                {"error": "Missing homework_title. Ask the user to provide it."}
            )

        try:
            # Get all student's homework
            response = await self.api_client.get(
                f"/homework/student/{memory.student_id}", timeout=10.0
            )
            response.raise_for_status()
            all_homework = response.json()

            # Find matching homework
            for homework in all_homework:
                if (
                    homework_title.lower()
                    in homework.get("content", {}).get("title", "").lower()
                ):
                    return json.dumps(
                        {
                            "homework_task_title": homework.get("content", {}).get(
                                "title", ""
                            ),
                            "homework_task_description": homework.get(
                                "content", {}
                            ).get("description", ""),
                        }
                    )

            return json.dumps(
                {
                    "homework_task_title": None,
                    "homework_task_description": None,
                }
            )

        except Exception as e:
            logger.info(f"Error searching homework: {e}")
            return json.dumps(
                {
                    "error": str(e),
                    "homework_task_title": None,
                    "homework_task_description": None,
                }
            )

    async def _get_submission(
        self, homework_title: Optional[str], memory: MemoryBuffer
    ) -> str:
        """Get submission for a homework task"""
        if not homework_title:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Missing homework_title. Ask the user to provide it.",
                }
            )

        try:
            # Get all student's submissions
            response = await self.api_client.get(
                f"/submissions/student/{memory.student_id}", timeout=10.0
            )
            response.raise_for_status()
            all_submissions = response.json()

            # For each submission, get its homework task and check the title
            for submission in all_submissions:
                homework_task_id = submission["homework_task_id"]

                if homework_task_id not in memory.seen_info_buffer:
                    homework_response = await self.api_client.get(
                        f"/homework/{homework_task_id}"
                    )
                    homework_task = homework_response.json()
                    # Add to memory
                    homework_submission_pair = memory.add_seen_info(
                        homework_task, submission
                    )
                else:
                    homework_submission_pair = memory.get_homework_submission_pair(
                        homework_task_id
                    )

                logger.info(
                    f"AI TEACHER Checking submission for homework task {homework_task_id}: {homework_submission_pair}"
                )
                if (
                    homework_title.lower()
                    in homework_submission_pair.get("homework_task_title", "").lower()
                ):
                    return json.dumps(
                        {
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
                    )

            return json.dumps(
                {
                    "homework_task_title": None,
                    "homework_task_description": None,
                    "submission_text": None,
                    "submission_id": None,
                }
            )

        except Exception as e:
            logger.info(f"Error searching submissions: {e}")
            return json.dumps(
                {
                    "error": str(e),
                    "homework_task_title": None,
                    "homework_task_description": None,
                    "submission_text": None,
                    "submission_id": None,
                }
            )

    async def _give_feedback(
        self, homework_title: Optional[str], memory: MemoryBuffer
    ) -> str:
        """Generate feedback for a submission"""
        if not homework_title:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Missing homework_title. Ask the user to provide it.",
                }
            )

        try:
            # First get the submission info
            submission_info = json.loads(
                await self._get_submission(homework_title, memory)
            )

            if not submission_info.get("homework_task_title"):
                return json.dumps(
                    {"error": f"No submission found for homework: {homework_title}"}
                )

            # Generate feedback
            response = await self.api_client.post(
                "/feedback/generate/",
                json={
                    "homework_title": submission_info["homework_task_title"],
                    "homework_description": submission_info[
                        "homework_task_description"
                    ],
                    "submission_text": submission_info["submission_text"],
                    "chat_context": memory.chat_repr__no_tools(),
                    "student_id": memory.student_id,
                    "submission_id": submission_info["submission_id"],
                },
                timeout=60.0,
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
            logger.info(f"Error generating feedback: {e}")
            return json.dumps({"error": str(e)})

    async def _analyze_user(
        self, aspect_to_analyze: Optional[str], memory: MemoryBuffer
    ) -> str:
        """Analyze user profile and progress"""
        if not aspect_to_analyze:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Missing aspect_to_analyze. Ask the user what aspect of their learning they want to analyze.",
                }
            )

        try:
            response = await self.api_client.post(
                f"/users/analysis/{memory.student_id}",
                json={
                    "user_id": memory.student_id,
                    "chat_context": memory.chat_repr__no_tools(),
                    "current_profile": memory.user_profile,
                    "seen_within_profile": memory.seen_within_profile,
                    "aspect_to_analyze": aspect_to_analyze,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            analysis_data = response.json()

            # Update memory with new profile and seen homework
            memory.user_profile = analysis_data["profile"]
            if "analyzed_homework_ids" in analysis_data:
                memory.seen_within_profile.extend(
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
            logger.info(f"Error analyzing user: {e}")
            return json.dumps({"error": str(e)})
