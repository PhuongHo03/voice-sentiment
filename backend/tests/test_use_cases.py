import pytest
from unittest.mock import MagicMock
from app.services.analysis_service import SubmitAudioAnalysis, SubmitTextAnalysis

def test_submit_text_analysis_success():
    # 1. Mock dependency objects
    mock_repo = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "text-job-uuid-123"
    mock_job.status = "pending"
    mock_repo.create_text_job.return_value = mock_job

    mock_publisher = MagicMock()

    # 2. Instantiate Use Case
    use_case = SubmitTextAnalysis(repository=mock_repo, publisher=mock_publisher)

    # 3. Execute
    result = use_case.execute(text="Xin chào đây là bài test", owner_id="user-123")

    # 4. Assertions
    assert result["job_id"] == "text-job-uuid-123"
    assert result["status"] == "pending"
    mock_repo.create_text_job.assert_called_once_with("Xin chào đây là bài test", name="Xin chào đây là bài test", owner_id="user-123")
    mock_publisher.publish.assert_called_once_with(
        {"job_id": "text-job-uuid-123", "input_type": "text", "text": "Xin chào đây là bài test", "owner_id": "user-123"},
        owner_id="user-123"
    )

def test_submit_audio_analysis_success():
    # 1. Mock dependency objects
    mock_storage = MagicMock()
    mock_storage.save.return_value = "uploads/user-123/call.webm"

    mock_repo = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "audio-job-uuid-456"
    mock_job.status = "pending"
    mock_repo.create_audio_job.return_value = mock_job

    mock_publisher = MagicMock()

    # 2. Instantiate Use Case
    use_case = SubmitAudioAnalysis(repository=mock_repo, storage=mock_storage, publisher=mock_publisher)

    # 3. Execute
    result = use_case.execute(
        filename="call.webm",
        content=b"webm_header_and_data_bytes",
        content_type="audio/webm",
        owner_id="user-123"
    )

    # 4. Assertions
    assert result["job_id"] == "audio-job-uuid-456"
    assert result["status"] == "pending"
    mock_storage.save.assert_called_once_with("call.webm", b"webm_header_and_data_bytes", "audio/webm", owner_id="user-123")
    mock_repo.create_audio_job.assert_called_once_with("uploads/user-123/call.webm", name="call.webm", owner_id="user-123")
    mock_publisher.publish.assert_called_once_with(
        {"job_id": "audio-job-uuid-456", "input_type": "audio", "audio_object_key": "uploads/user-123/call.webm", "owner_id": "user-123"},
        owner_id="user-123"
    )
