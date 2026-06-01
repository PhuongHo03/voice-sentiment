from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    voice_language_code: str = "vi-VN"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
