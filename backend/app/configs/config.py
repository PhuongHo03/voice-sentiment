from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    rabbitmq_url: str
    prometheus_url: str = "http://prometheus:9090"
    rabbitmq_queue_count: int = 1
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "voice-audio"
    minio_secure: bool = False
    cors_origins: str = "http://localhost:5173"
    jwt_secret: str = "supersecretkeychangeinproduction"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 1440

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
