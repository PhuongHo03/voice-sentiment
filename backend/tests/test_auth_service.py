import pytest
from app.services.auth_service import AuthService
from datetime import timedelta

def test_password_hashing():
    auth_service = AuthService()
    password = "MySecurePassword123"
    
    hashed = auth_service.hash_password(password)
    assert hashed != password
    assert auth_service.verify_password(password, hashed) is True
    assert auth_service.verify_password("wrong_password", hashed) is False

def test_jwt_creation_and_decoding():
    auth_service = AuthService()
    payload = {"sub": "user_id_123", "role": "employee"}
    
    token = auth_service.create_access_token(payload, expires_delta=timedelta(minutes=5))
    assert isinstance(token, str)
    
    decoded = auth_service.decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user_id_123"
    assert decoded["role"] == "employee"

def test_decode_invalid_jwt():
    auth_service = AuthService()
    assert auth_service.decode_access_token("invalid_token_string") is None
