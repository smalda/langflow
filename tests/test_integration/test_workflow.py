from unittest.mock import patch

import pytest

from app.queue.notifications import (
    notify_feedback_provided,
    notify_homework_assigned,
    notify_submission_received,
)


@pytest.mark.integration
def test_complete_homework_workflow(client, session):
    """Test the complete workflow: Teacher assigns homework -> Student submits -> Teacher provides feedback"""

    # 1. Create teacher and student
    teacher_data = {
        "tg_handle": "integration_teacher",
        "telegram_id": "111000111",
        "role": "teacher",
        "meta": {"specialization": "ballet"},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    assert teacher_response.status_code == 200
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "integration_student",
        "telegram_id": "222000222",
        "role": "student",
        "meta": {"level": "intermediate"},
    }
    student_response = client.post("/users/", json=student_data)
    assert student_response.status_code == 200
    student_id = student_response.json()["id"]

    # 2. Teacher assigns homework
    with patch(
        "app.queue.notifications.producer.send_message", return_value=True
    ) as mock_notify:
        homework_data = {
            "teacher_id": teacher_id,
            "student_ids": [student_id],
            "content": {
                "title": "Integration Test Homework",
                "description": "Test the complete workflow",
            },
            "status": "pending",
        }
        homework_response = client.post("/homework/assign/", json=homework_data)
        assert homework_response.status_code == 200
        homework_id = homework_response.json()["id"]

        # Verify notification was sent
        mock_notify.assert_called_once()

    # 3. Student submits homework
    with patch(
        "app.queue.notifications.producer.send_message", return_value=True
    ) as mock_notify:
        submission_data = {
            "homework_task_id": homework_id,
            "student_id": student_id,
            "teacher_id": teacher_id,
            "content": {"text": "Integration test submission"},
            "status": "pending",
        }
        submission_response = client.post("/submissions/", json=submission_data)
        assert submission_response.status_code == 200
        submission_id = submission_response.json()["id"]

        # Verify notification was sent
        mock_notify.assert_called_once()

    # 4. Teacher provides feedback
    with patch(
        "app.queue.notifications.producer.send_message", return_value=True
    ) as mock_notify:
        feedback_data = {
            "submission_id": submission_id,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "content": {"text": "Great work on the integration test!"},
            "status": "completed",
        }
        feedback_response = client.post("/feedback/", json=feedback_data)
        assert feedback_response.status_code == 200

        # Verify notification was sent
        mock_notify.assert_called_once()

    # 5. Verify final states
    # Check homework status
    homework_response = client.get(f"/homework/{homework_id}")
    assert homework_response.status_code == 200
    assert homework_response.json()["status"] == "completed"

    # Check submission
    submission_response = client.get(f"/submissions/{submission_id}")
    assert submission_response.status_code == 200
    assert submission_response.json()["status"] == "completed"


@pytest.mark.integration
def test_multiple_students_workflow(client, session):
    """Test workflow with multiple students"""

    # 1. Create teacher and multiple students
    teacher_data = {
        "tg_handle": "group_teacher",
        "telegram_id": "333000333",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    # Create multiple students
    student_ids = []
    for i in range(3):
        student_data = {
            "tg_handle": f"group_student_{i}",
            "telegram_id": f"44400044{i}",
            "role": "student",
            "meta": {},
        }
        student_response = client.post("/users/", json=student_data)
        student_ids.append(student_response.json()["id"])

    # 2. Teacher assigns group homework
    with patch(
        "app.queue.notifications.producer.send_message", return_value=True
    ) as mock_notify:
        homework_data = {
            "teacher_id": teacher_id,
            "student_ids": student_ids,
            "content": {
                "title": "Group Homework",
                "description": "Test multiple students workflow",
            },
            "status": "pending",
        }
        homework_response = client.post("/homework/assign/", json=homework_data)
        homework_id = homework_response.json()["id"]

        # Verify notifications were sent for each student
        assert mock_notify.call_count == len(student_ids)

    # 3. Each student submits homework
    submission_ids = []
    with patch(
        "app.queue.notifications.producer.send_message", return_value=True
    ) as mock_notify:
        for student_id in student_ids:
            submission_data = {
                "homework_task_id": homework_id,
                "student_id": student_id,
                "teacher_id": teacher_id,
                "content": {"text": f"Submission from student {student_id}"},
                "status": "pending",
            }
            submission_response = client.post("/submissions/", json=submission_data)
            submission_ids.append(submission_response.json()["id"])

        # Verify notifications were sent for each submission
        assert mock_notify.call_count == len(student_ids)

    # 4. Teacher provides feedback for each submission
    with patch(
        "app.queue.notifications.producer.send_message", return_value=True
    ) as mock_notify:
        for submission_id, student_id in zip(submission_ids, student_ids):
            feedback_data = {
                "submission_id": submission_id,
                "teacher_id": teacher_id,
                "student_id": student_id,
                "content": {"text": f"Feedback for student {student_id}"},
                "status": "completed",
            }
            feedback_response = client.post("/feedback/", json=feedback_data)
            assert feedback_response.status_code == 200

    # 5. Verify final states
    homework_response = client.get(f"/homework/{homework_id}")
    assert homework_response.json()["status"] == "completed"

    for submission_id in submission_ids:
        submission_response = client.get(f"/submissions/{submission_id}")
        assert submission_response.json()["status"] == "completed"


@pytest.mark.integration
def test_error_handling_workflow(client, session):
    """Test error handling in the workflow"""

    # 1. Setup users
    teacher_data = {
        "tg_handle": "error_teacher",
        "telegram_id": "555000555",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "error_student",
        "telegram_id": "666000666",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # 2. Test invalid homework assignment
    invalid_homework = {
        "teacher_id": student_id,  # Student trying to assign homework
        "student_ids": [student_id],
        "content": {"title": "Invalid Homework"},
        "status": "pending",
    }
    response = client.post("/homework/assign/", json=invalid_homework)
    assert response.status_code == 404

    # 3. Test invalid submission
    invalid_submission = {
        "homework_task_id": "nonexistent_id",
        "student_id": student_id,
        "teacher_id": teacher_id,
        "content": {"text": "Invalid submission"},
        "status": "pending",
    }
    response = client.post("/submissions/", json=invalid_submission)
    assert response.status_code == 404

    # 4. Test invalid feedback
    invalid_feedback = {
        "submission_id": "nonexistent_id",
        "teacher_id": teacher_id,
        "student_id": student_id,
        "content": {"text": "Invalid feedback"},
        "status": "completed",
    }
    response = client.post("/feedback/", json=invalid_feedback)
    assert response.status_code == 404


@pytest.mark.integration
def test_cancelled_homework_workflow(client, session):
    """Test workflow when homework is cancelled"""

    # 1. Setup users
    teacher_data = {
        "tg_handle": "cancel_teacher",
        "telegram_id": "777000777",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "cancel_student",
        "telegram_id": "888000888",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # 2. Create and then cancel homework
    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": [student_id],
        "content": {"title": "Homework to Cancel"},
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    homework_id = homework_response.json()["id"]

    # Update homework status to cancelled
    # cancelled_homework = homework_response.json()
    # cancelled_homework["status"] = "cancelled"
    response = client.patch(
        f"/homework/{homework_id}/status", params={"status": "cancelled"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    # 3. Try to submit to cancelled homework
    submission_data = {
        "homework_task_id": homework_id,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "content": {"text": "Submission to cancelled homework"},
        "status": "pending",
    }
    response = client.post("/submissions/", json=submission_data)
    assert response.status_code == 400


@pytest.mark.integration
def test_sequential_homework_workflow(client, session):
    """Test workflow with sequential homework assignments"""

    # 1. Setup users
    teacher_data = {
        "tg_handle": "seq_teacher",
        "telegram_id": "999000999",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    student_data = {
        "tg_handle": "seq_student",
        "telegram_id": "000999000",
        "role": "student",
        "meta": {},
    }
    student_response = client.post("/users/", json=student_data)
    student_id = student_response.json()["id"]

    # 2. Create sequence of homework assignments
    homework_ids = []
    for i in range(3):
        homework_data = {
            "teacher_id": teacher_id,
            "student_ids": [student_id],
            "content": {
                "title": f"Sequential Homework {i+1}",
                "sequence_number": i + 1,
            },
            "status": "pending",
        }
        response = client.post("/homework/assign/", json=homework_data)
        homework_ids.append(response.json()["id"])

    # 3. Complete homework in sequence
    for homework_id in homework_ids:
        # Submit homework
        submission_data = {
            "homework_task_id": homework_id,
            "student_id": student_id,
            "teacher_id": teacher_id,
            "content": {"text": f"Submission for {homework_id}"},
            "status": "pending",
        }
        submission_response = client.post("/submissions/", json=submission_data)
        submission_id = submission_response.json()["id"]

        # Provide feedback
        feedback_data = {
            "submission_id": submission_id,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "content": {"text": f"Feedback for {homework_id}"},
            "status": "completed",
        }
        client.post("/feedback/", json=feedback_data)

    # 4. Verify all homework assignments are completed in sequence
    for homework_id in homework_ids:
        response = client.get(f"/homework/{homework_id}")
        assert response.json()["status"] == "completed"


@pytest.mark.integration
def test_concurrent_submissions_workflow(client, session):
    """Test workflow with concurrent submissions from multiple students"""

    # 1. Setup teacher and multiple students
    teacher_data = {
        "tg_handle": "concurrent_teacher",
        "telegram_id": "111222333",
        "role": "teacher",
        "meta": {},
    }
    teacher_response = client.post("/users/", json=teacher_data)
    teacher_id = teacher_response.json()["id"]

    # Create multiple students
    student_ids = []
    for i in range(5):
        student_data = {
            "tg_handle": f"concurrent_student_{i}",
            "telegram_id": f"33322211{i}",
            "role": "student",
            "meta": {},
        }
        response = client.post("/users/", json=student_data)
        student_ids.append(response.json()["id"])

    # 2. Create group homework
    homework_data = {
        "teacher_id": teacher_id,
        "student_ids": student_ids,
        "content": {
            "title": "Concurrent Homework",
            "description": "Test concurrent submissions",
        },
        "status": "pending",
    }
    homework_response = client.post("/homework/assign/", json=homework_data)
    homework_id = homework_response.json()["id"]

    # 3. Submit homework concurrently
    submission_ids = []
    for student_id in student_ids:
        submission_data = {
            "homework_task_id": homework_id,
            "student_id": student_id,
            "teacher_id": teacher_id,
            "content": {"text": f"Concurrent submission from {student_id}"},
            "status": "pending",
        }
        response = client.post("/submissions/", json=submission_data)
        submission_ids.append(response.json()["id"])

    # 4. Verify all submissions are recorded
    for submission_id in submission_ids:
        response = client.get(f"/submissions/{submission_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    # 5. Provide feedback for all submissions
    for submission_id, student_id in zip(submission_ids, student_ids):
        feedback_data = {
            "submission_id": submission_id,
            "teacher_id": teacher_id,
            "student_id": student_id,
            "content": {"text": f"Feedback for concurrent submission {submission_id}"},
            "status": "completed",
        }
        response = client.post("/feedback/", json=feedback_data)
        assert response.status_code == 200

    # 6. Verify final state
    response = client.get(f"/homework/{homework_id}")
    assert response.json()["status"] == "completed"
