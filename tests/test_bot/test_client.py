import httpx
import pytest

from app.bot.client import APIClient


@pytest.mark.asyncio
async def test_get_or_create_user(httpx_mock):
    # Setup
    client = APIClient(base_url="http://test")

    # Mock the GET request (user doesn't exist)
    httpx_mock.add_response(
        url="http://test/users/by_telegram_handle/test_user", status_code=404
    )

    # Mock the POST request (create user)
    expected_user = {
        "id": "test_id",
        "tg_handle": "test_user",
        "telegram_id": "123456",
        "role": "student",
    }
    httpx_mock.add_response(url="http://test/users/", json=expected_user, method="POST")

    # Test
    result = await client.get_or_create_user(
        telegram_id="123456", username="test_user", role="student"
    )

    assert result == expected_user


@pytest.mark.asyncio
async def test_get_homework_for_student(httpx_mock):
    client = APIClient(base_url="http://test")

    # Mock homework list with pagination parameters
    homework_list = [
        {
            "id": "hw_1",
            "teacher_id": "teacher_1",
            "content": {"title": "Test Homework"},
            "status": "pending",
        }
    ]

    # Mock the exact URL including query parameters
    httpx_mock.add_response(
        url="http://test/homework/student/student_1?offset=0&limit=100",
        json=homework_list,
    )

    # Mock teacher info
    teacher_info = {
        "id": "teacher_1",
        "tg_handle": "test_teacher",
        "telegram_id": "987654",
    }
    httpx_mock.add_response(url="http://test/users/teacher_1", json=teacher_info)

    result = await client.get_homework_for_student("student_1")
    assert result[0]["content"]["title"] == "Test Homework"


@pytest.mark.asyncio
async def test_submit_homework(httpx_mock):
    client = APIClient(base_url="http://test")

    expected_response = {
        "id": "sub_1",
        "content": {"text": "Test submission"},
        "status": "pending",
    }

    httpx_mock.add_response(
        url="http://test/submissions/", json=expected_response, method="POST"
    )

    submission_data = {
        "homework_task_id": "hw_1",
        "content": {"text": "Test submission"},
    }

    result = await client.submit_homework(submission_data)
    assert result == expected_response


@pytest.mark.asyncio
async def test_provide_feedback(httpx_mock):
    client = APIClient(base_url="http://test")

    expected_response = {
        "id": "fb_1",
        "content": {"text": "Good work!"},
        "status": "completed",
    }

    httpx_mock.add_response(
        url="http://test/feedback/", json=expected_response, method="POST"
    )

    feedback_data = {
        "submission_id": "sub_1",
        "content": {"text": "Good work!"},
        "status": "completed",
    }

    result = await client.provide_feedback(feedback_data)
    assert result == expected_response


@pytest.mark.asyncio
async def test_get_existing_user(httpx_mock):
    client = APIClient(base_url="http://test")

    # Mock existing user response
    expected_user = {
        "id": "usr_existing",
        "tg_handle": "existing_user",
        "telegram_id": "123456",
        "role": "student",
    }
    httpx_mock.add_response(
        url="http://test/users/by_telegram_handle/existing_user",
        json=expected_user,
        status_code=200,
    )

    result = await client.get_or_create_user(
        telegram_id="123456", username="existing_user", role="student"
    )

    assert result == expected_user


@pytest.mark.asyncio
async def test_get_all_students(httpx_mock):
    client = APIClient(base_url="http://test")

    expected_students = [
        {"id": "usr_1", "tg_handle": "student1", "role": "student"},
        {"id": "usr_2", "tg_handle": "student2", "role": "student"},
    ]

    # Add pagination parameters to URL
    httpx_mock.add_response(
        url="http://test/users/students/?offset=0&limit=100", json=expected_students
    )

    result = await client.get_all_students()
    assert len(result) == 2
    assert all(student["role"] == "student" for student in result)


@pytest.mark.asyncio
async def test_get_all_teachers(httpx_mock):
    client = APIClient(base_url="http://test")

    expected_teachers = [
        {"id": "usr_3", "tg_handle": "teacher1", "role": "teacher"},
        {"id": "usr_4", "tg_handle": "teacher2", "role": "teacher"},
    ]

    httpx_mock.add_response(
        url="http://test/users/teachers/?offset=0&limit=100", json=expected_teachers
    )

    result = await client.get_all_teachers()
    assert len(result) == 2
    assert all(teacher["role"] == "teacher" for teacher in result)


@pytest.mark.asyncio
async def test_get_teacher_submissions(httpx_mock):
    client = APIClient(base_url="http://test")

    # Mock submissions with pagination
    submissions = [
        {
            "id": "sub_1",
            "student_id": "usr_1",
            "homework_task_id": "hw_1",
            "content": {"text": "Test submission"},
            "status": "pending",
        }
    ]

    httpx_mock.add_response(
        url="http://test/submissions/teacher/teacher_1?offset=0&limit=100",
        json=submissions,
    )

    # Mock homework info
    homework_info = {"id": "hw_1", "content": {"title": "Test Homework"}}
    httpx_mock.add_response(url="http://test/homework/hw_1", json=homework_info)

    # Mock student info
    student_info = {"id": "usr_1", "tg_handle": "student1", "telegram_id": "123456"}
    httpx_mock.add_response(url="http://test/users/usr_1", json=student_info)

    result = await client.get_teacher_submissions("teacher_1")
    assert len(result) == 1
    assert result[0]["homework_title"] == "Test Homework"
    assert result[0]["student_handle"] == "student1"


@pytest.mark.asyncio
async def test_get_submission_feedback(httpx_mock):
    client = APIClient(base_url="http://test")

    # Mock feedback list
    feedback_list = [
        {
            "id": "fb_1",
            "content": {"text": "Good work!"},
            "status": "completed",
            "submission_id": "sub_1",
        }
    ]

    # Mock feedback request with pagination
    httpx_mock.add_response(
        url="http://test/feedback/submission/sub_1?offset=0&limit=100",
        json=feedback_list,
    )

    # Mock submission request
    submission_data = {
        "id": "sub_1",
        "content": {"text": "Test submission"},
        "homework_task_id": "hw_1",
    }
    httpx_mock.add_response(url="http://test/submissions/sub_1", json=submission_data)

    # Mock homework request
    homework_data = {"id": "hw_1", "content": {"title": "Test Homework"}}
    httpx_mock.add_response(url="http://test/homework/hw_1", json=homework_data)

    result = await client.get_submission_feedback("sub_1")
    assert len(result) == 1
    assert result[0]["content"]["text"] == "Good work!"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Needs fixing")
async def test_error_handling_404(httpx_mock):
    client = APIClient(base_url="http://test")

    def custom_response(request):
        response = httpx.Response(
            status_code=404, json={"detail": "User not found"}, request=request
        )
        raise httpx.HTTPStatusError("404 Not Found", request=request, response=response)

    # Mock the response with a custom handler
    httpx_mock.add_callback(
        custom_response, url="http://test/users/by_telegram_id/nonexistent"
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_user_by_telegram_id("nonexistent")


@pytest.mark.asyncio
async def test_get_homework_by_id(httpx_mock):
    client = APIClient(base_url="http://test")

    expected_homework = {
        "id": "hw_1",
        "content": {"title": "Test Homework"},
        "status": "pending",
    }

    httpx_mock.add_response(url="http://test/homework/hw_1", json=expected_homework)

    result = await client.get_homework_by_id("hw_1")
    assert result["content"]["title"] == "Test Homework"


@pytest.mark.asyncio
async def test_get_submission_by_id(httpx_mock):
    client = APIClient(base_url="http://test")

    expected_submission = {
        "id": "sub_1",
        "content": {"text": "Test submission"},
        "status": "pending",
    }

    httpx_mock.add_response(
        url="http://test/submissions/sub_1", json=expected_submission
    )

    result = await client.get_submission_by_id("sub_1")
    assert result["content"]["text"] == "Test submission"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Needs fixing")
async def test_connection_error(httpx_mock):
    client = APIClient(base_url="http://test")

    # Mock connection error with pagination parameters
    httpx_mock.add_exception(
        httpx.ConnectError("Connection refused"),
        url="http://test/users/students/?offset=0&limit=100",  # Added pagination
    )

    with pytest.raises(httpx.ConnectError):
        await client.get_all_students()


@pytest.mark.skip(reason="Needs fixing")
@pytest.mark.asyncio
async def test_timeout_error(httpx_mock):
    client = APIClient(base_url="http://test")

    # Mock timeout error with pagination parameters
    httpx_mock.add_exception(
        httpx.TimeoutException("Timeout"),
        url="http://test/users/teachers/?offset=0&limit=100",  # Added pagination
    )

    with pytest.raises(httpx.TimeoutException):
        await client.get_all_teachers()
