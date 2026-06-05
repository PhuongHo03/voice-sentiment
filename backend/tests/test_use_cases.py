import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.services.analysis_service import SubmitAudioAnalysis, SubmitTextAnalysis
from app.services.file_service import FileService

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

def test_delete_file_success():
    # 1. Mock dependency objects
    mock_repo = MagicMock()
    mock_repo.has_job_referencing_key.return_value = False

    # 2. Instantiate FileService and mock _get_minio_client
    file_service = FileService(repository=mock_repo)
    mock_minio = MagicMock()
    file_service._get_minio_client = MagicMock(return_value=mock_minio)

    # 3. Execute
    result = file_service.delete("uploads/user-123/call.webm", "user-123")

    # 4. Assertions
    assert result == {"message": "File deleted successfully"}
    mock_repo.has_job_referencing_key.assert_called_once_with("uploads/user-123/call.webm")
    mock_minio.remove_object.assert_called_once_with("voice-audio", "uploads/user-123/call.webm")

def test_delete_file_active_job_conflict():
    # 1. Mock repository to simulate active job
    mock_repo = MagicMock()
    mock_repo.has_job_referencing_key.return_value = True
    mock_repo.has_active_job_for_key.return_value = True

    file_service = FileService(repository=mock_repo)

    # 2. Execute & Assert conflict
    with pytest.raises(HTTPException) as exc_info:
        file_service.delete("uploads/user-123/call.webm", "user-123")

    assert exc_info.value.status_code == 409
    assert "đang có job phân tích" in exc_info.value.detail
    mock_repo.has_job_referencing_key.assert_called_once_with("uploads/user-123/call.webm")
    mock_repo.has_active_job_for_key.assert_called_once_with("uploads/user-123/call.webm")

def test_delete_file_completed_job_conflict():
    # 1. Mock repository to simulate completed/failed job (referenced but not active)
    mock_repo = MagicMock()
    mock_repo.has_job_referencing_key.return_value = True
    mock_repo.has_active_job_for_key.return_value = False

    file_service = FileService(repository=mock_repo)

    # 2. Execute & Assert conflict
    with pytest.raises(HTTPException) as exc_info:
        file_service.delete("uploads/user-123/call.webm", "user-123")

    assert exc_info.value.status_code == 409
    assert "vui lòng xóa phiên phân tích" in exc_info.value.detail.lower()
    mock_repo.has_job_referencing_key.assert_called_once_with("uploads/user-123/call.webm")
    mock_repo.has_active_job_for_key.assert_called_once_with("uploads/user-123/call.webm")
