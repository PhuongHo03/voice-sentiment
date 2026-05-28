import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "voice-worker"}

@patch("app.main.stt_client")
def test_transcribe_audio_success(mock_stt_client):
    # Mock return value of transcribe
    mock_stt_client.transcribe.return_value = [
        {"speaker": "Speaker 0", "text": "Chào bạn", "start_seconds": 0.0, "end_seconds": 1.5},
        {"speaker": "Speaker 1", "text": "Chào tôi có thể giúp gì", "start_seconds": 1.6, "end_seconds": 4.0}
    ]

    # Create dummy audio file payload
    files = {"file": ("test.webm", b"webm_binary_bytes_here", "audio/webm")}
    
    response = client.post("/api/transcribe", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.webm"
    assert len(data["turns"]) == 2
    assert data["turns"][0]["speaker"] == "Speaker 0"
    assert data["turns"][0]["text"] == "Chào bạn"
    mock_stt_client.transcribe.assert_called_once_with(b"webm_binary_bytes_here")

@patch("app.main.stt_client")
def test_transcribe_audio_failure(mock_stt_client):
    # Mock transcribe to raise an exception
    mock_stt_client.transcribe.side_effect = RuntimeError("Whisper ASR failed")

    files = {"file": ("test.webm", b"bad_bytes", "audio/webm")}
    response = client.post("/api/transcribe", files=files)
    
    assert response.status_code == 500
    assert response.json()["detail"] == "Whisper ASR failed"
