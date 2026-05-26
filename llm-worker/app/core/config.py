from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    rabbitmq_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "voice-audio"
    minio_secure: bool = False
    voice_server_uri: str  # URL to connect to the voice-worker API (e.g. http://voice-worker:8000)
    llm_base_url: str
    llm_api_key: str
    llm_model: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
