from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = None
    redis_url: str | None = None
    rabbitmq_url: str | None = None

    # Dynamic building variables
    postgres_db: str = "voice_sentiment"
    postgres_user: str = "voice"
    postgres_password: str = "voice"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_host: str = "redis"
    redis_port_internal: int = 6379

    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port_internal: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"

    rabbitmq_queue_count: int = 1
    minio_endpoint: str = "minio:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "voice-audio"
    minio_secure: bool = False
    voice_server_url: str  # URL to connect to the voice-worker API (e.g. http://voice-worker:8000)
    llm_base_url: str
    llm_api_key: str
    llm_model: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def build_urls(self) -> "Settings":
        if not self.database_url:
            self.database_url = f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        if not self.redis_url:
            self.redis_url = f"redis://{self.redis_host}:{self.redis_port_internal}/0"
        if not self.rabbitmq_url:
            self.rabbitmq_url = f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port_internal}/%2F"
        return self


settings = Settings()
