from teacher_agent import MemoryBuffer, TeacherAgent

# Create mock memory buffer
mock_memory = MemoryBuffer()
mock_memory.student_id = "usr_test_student"
mock_memory.user_profile = """
Student Name: John Doe
Native Language: Spanish
Current English Level: B1
Learning Goals: Business English, Presentation Skills
Recent Topics: Email Writing, Meeting Minutes
"""

# Add some context messages
mock_memory.recent_context = [
    {"role": "user", "content": "Hi! I need help with my English homework."},
    {
        "role": "assistant",
        "content": "Hello! I'd be happy to help you with your English studies. What would you like to work on?",
    },
    {
        "role": "user",
        "content": "I need to practice business presentations. Can you create a homework for me?",
    },
]


import httpx

try:
    from httpx import Timeout

    timeout = Timeout(60.0, read=60.0)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            "http://localhost:8000/homework/generate/",
            json={
                "topic": "Business-relevant english",
                "language_level": "C2",
                "student_stress_level": "medium",
                "chat_context": mock_memory.chat_repr__no_tools(),
                "student_id": mock_memory.student_id,
            },
        )
    response.raise_for_status()

    generated_content = response.json()

except Exception as e:
    print(f"Error calling homework generation API: {e}")
generated_content["content"].keys()
# Fallback to mock in case of error
# error = {
#     "id": "hw_",
#     "teacher_id": "ai_teacher_01",
#     "content": {
#         "title": None,
#         "description": "Error generating homework content",
#         "language_level": language_level,
#         "stress_level": student_stress_level
#     },
#     "status": "error"
# }


from teacher_agent import MemoryBuffer, TeacherAgent

mock_memory = MemoryBuffer()
mock_memory.student_id = "usr_test_student"
mock_memory.user_profile = """Student name: John Smith
Language level: B2
Learning goals: Improve business English
Recent topics: Email writing, presentations
"""

# Add some conversation history
mock_memory.add_message(
    {"role": "user", "content": "Hi, I'm feeling great today! Not stressed at all."}
)
mock_memory.add_message(
    {
        "role": "assistant",
        "content": "Ohhh that's really good news! Wanna chat about your learning goals?",
    }
)
import os

import dotenv

dotenv.load_dotenv()
teacher = TeacherAgent(api_key=os.getenv("OPENAI_API_KEY"))
teacher.memory = mock_memory
response = teacher.process_message(
    'Sure! I actually wanted to ask you to score my submission for the homework "Business Email Writing Practice"'
)
print(response)
teacher.process_message("Sure! Please do")


from teacher_agent import MemoryBuffer, TeacherAgent

mock_memory = MemoryBuffer()
mock_memory.student_id = "usr_test_student"
mock_memory.user_profile = """Student name: John Smith
Language level: B2
Learning goals: Improve business English
Recent topics: Email writing, presentations
"""

# Add some conversation history
mock_memory.add_message(
    {"role": "user", "content": "Hi, I'm feeling great today! Not stressed at all."}
)
mock_memory.add_message(
    {
        "role": "assistant",
        "content": "Ohhh that's really good news! Wanna chat about your learning goals?",
    }
)
import os

import dotenv

dotenv.load_dotenv()
teacher = TeacherAgent(api_key=os.getenv("OPENAI_API_KEY"))
teacher.memory = mock_memory
response = teacher.process_message(
    'Sure! I actually wanted to ask you for some help on my homework on "Advanced Business Presentation Skills". I don\'t even know what I should begin with here...'
)
print(response)
response = teacher.process_message(
    "I mean yeah, okay, but how do I introduce myself..."
)
print(response)


import os

from dotenv import load_dotenv

from teacher_agent import MemoryBuffer, TeacherAgent

load_dotenv()

# Create mock memory with student context
mock_memory = MemoryBuffer()
teacher = TeacherAgent(api_key=os.getenv("OPENAI_API_KEY"))
mock_memory.student_id = "usr_test_student"
mock_memory.user_profile = """Student name: John Smith
Language level: B2
Learning goals: Improve business English
Recent topics: Email writing, presentations
"""

# Add conversation leading to homework assignment
mock_memory.add_message(
    {
        "role": "user",
        "content": "Hi! Can you give me some homework about discursive essays on big data?",
    }
)
mock_memory.add_message(
    {
        "role": "assistant",
        "content": "I'd be happy to create a homework assignment for a discursive essay on big data. "
        "Since you're at B2 level, I'll make it appropriately challenging. "
        "How stressed are you with other work right now?",
    }
)
mock_memory.add_message(
    {"role": "user", "content": "Not stressed at all, I have plenty of time!"}
)

# Initialize teacher with mock memory
teacher.memory = mock_memory

# Step 1: Get homework assignment
print("\n=== Step 1: Getting Homework Assignment ===")
response = teacher.process_message("Great! Then please assign me that homework.")
print("Response:", response)

teacher.memory

import json
from dataclasses import asdict


def save_to_json(data, filename):
    with open(filename, "w") as f:
        # asdict() converts dataclass to dictionary
        json.dump(asdict(data), f)


def load_from_json(filename, dataclass_type):
    with open(filename, "r") as f:
        data = json.load(f)
        return dataclass_type(**data)


save_to_json(teacher.memory, "memory.json")

# Load from JSON
mock_memory = load_from_json("memory.json", MemoryBuffer)
teacher.memory = mock_memory


# Step 2: Get feedback on the submission
print("\n=== Step 2: Getting Feedback ===")
response = teacher.process_message(
    "Could you please check my submission and give me a score? I mean, the one for the homework that u gave me just now. I already submitted it."
)
print("Response:", response)
teacher.memory

save_to_json(teacher.memory, "memory_complete.json")

mock_memory = load_from_json("memory_complete.json", MemoryBuffer)
teacher.memory = mock_memory

response = teacher.process_message(
    "Can you analyze my progress and tell me how I'm doing?"
)
print(response)
teacher.memory


from ai_teacher_copy_async import AITeacher as _AITeacher_async

test_teacher = _AITeacher_async(api_key=os.getenv("OPENAI_API_KEY"))
from app.bot.memory import MemoryBuffer as _MemoryBuffer

mock_memory = load_from_json("memory_complete.json", _MemoryBuffer)
response = await test_teacher.process_message(
    "Could you please check my submission and give me a score? I mean, the one for the homework that u gave me just now. I already submitted it.",
    memory=mock_memory,
)
test_teacher.api_client

print("Response:", response)
mock_memory


import json

import httpx

result = None
with httpx.Client(timeout=30.0) as client:
    # First get all student's submissions
    response = client.get(
        f"http://localhost:8000/submissions/student/{mock_memory.student_id}"
    )

response.json()
try:
    with httpx.Client(timeout=30.0) as client:
        # First get all student's submissions
        response = client.get(
            f"http://localhost:8000/submissions/student/{mock_memory.student_id}"
        )
        response.raise_for_status()
        all_submissions = response.json()

        # For each submission, get its homework task and check the title
        for submission in all_submissions:
            homework_task_id = submission["homework_task_id"]
            if homework_task_id not in mock_memory.seen_info_buffer:
                homework_response = client.get(
                    f"http://localhost:8000/homework/{homework_task_id}"
                )
                homework_task = homework_response.json()

                # Add to memory
                homework_submission_pair = mock_memory.add_seen_info(
                    homework_task, submission
                )
            else:
                homework_submission_pair = mock_memory.get_homework_submission_pair(
                    homework_task_id
                )

            # Check if this homework's title matches what we're looking for
            if (
                homework_title.lower()
                in homework_submission_pair.get("homework_task_title", "").lower()
            ):
                result = {
                    "homework_task_title": homework_submission_pair[
                        "homework_task_title"
                    ],
                    "homework_task_description": homework_submission_pair[
                        "homework_task_description"
                    ],
                    "submission_text": homework_submission_pair["submission_text"],
                }

                result = json.dumps(result)

        result = json.dumps(
            {
                "homework_task_title": None,
                "homework_task_description": None,
                "submission_text": None,
            }
        )
except Exception as e:
    print(f"Error searching submissions: {e}")
    result = json.dumps(
        {
            "error": str(e),
            "homework_task_title": None,
            "homework_task_description": None,
            "submission_text": None,
        }
    )


generation_base = [
    {
        "role": "system",
        "content": "You are an AI English teacher. This is student's profile, gathered from previous interactions:\n",
    },
    {
        "role": "user",
        "content": "Hiyyaa\nPlease review my submission for the homework titled \"Exploring the Shadows: An Analysis of Informal Economic Practices\"!\nThis is the detailed info on the homework task and submission.\n\nHomework Task:\nTitle: Exploring the Shadows: An Analysis of Informal Economic Practices\nDescription: In this assignment, you'll delve into various informal economic activities and their implications in a global context. Research different types of 'shady' economic practices such as money laundering, tax evasion, or shadow banking systems. Choose one specific practice to focus on.\n\n1. Provide a detailed explanation of how this practice operates, including key mechanisms and strategies used.\n2. Analyze the socio-economic impacts of this practice on both local and international scales.\n3. Discuss any regulatory challenges and approaches to mitigate these activities.\n4. Deliver your findings in a 1500-word essay structured with a clear introduction, body sections addressing the points above, and a conclusion summarizing your analysis.\n\nFocus on polishing your advanced vocabulary and complex sentence structures that reflect proficiency at the C2 level. Ensure your arguments are nuanced and supported by credible, up-to-date sources.\n\nSubmission:\nImma gonna rollllll!\n\nPlease analyze the submission carefully and provide:\n1. Detailed, constructive feedback highlighting both strengths and areas for improvement\n2. A numerical score (0-100) based on how well the submission meets the homework requirements\n",
    },
]

{}.clear()


from pydantic import BaseModel, Field


class FeedbackGenerationModel(BaseModel):
    feedback_text: str = Field(
        ..., description="Detailed, constructive feedback on the submission"
    )
    score: int = Field(..., description="Score between 0 and 100")


completion = client.beta.chat.completions.parse(
    model="gpt-4o", messages=generation_base, response_format=FeedbackGenerationModel
)


completion.choices[0].message.parsed


from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


a = {
    "role": "tool",
    "tool_call_id": "call_VRz2RqP6X3b9CLcsPiMIthXj",
    "name": "analyze_user_profile",
    "content": '{"updated_profile": "The user is an intermediate English learner with a good grasp of basic grammar and vocabulary. They have been focusing on expanding their lexical resource, trying to include more complex sentence structures, and enhancing their listening and speaking skills. They engage actively in conversational practice to improve fluency.", "growth_story": "Over the past few months, the user has shown notable progress in their English language journey. Initially, they primarily used simple sentences and had a limited vocabulary. Through consistent practice and exposure to diverse language materials, they have started incorporating more complex sentences and nuanced vocabulary into their speaking and writing. Their understanding of idiomatic expressions has improved, and they have become more adept at participating in discussions on various topics.", "areas_of_improvement": "1. Enhance the use of idiomatic expressions in writing.\\n2. Expand vocabulary in specific areas such as business English.\\n3. Increase practice in listening comprehension, particularly with native speakers.\\n4. Focus on consistent pronunciation practice to refine accent clarity.", "specific_aspect_analysis": "Overall, the user\'s progress in English learning is commendable. They have successfully moved from basic sentence construction to more complex and diverse language use. They exhibit a keen interest in mastering the nuances of the language, as evidenced by their attempt to use idiomatic expressions and engage with varied topics. While they are on a solid path, continued focus on speaking fluently and diversifying vocabulary will further enhance their language proficiency. Regular engagement in real-life communication scenarios and exposure to native speech will be beneficial in reaching their learning goals."}',
}
json.loads(a["content"])["updated_profile"]
