from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the LLM application."""

    MDEBERTA_PATH: str
    QWEN_PATH: str
    REDIS_HOST: str
    REDIS_PORT: int

    model_config = SettingsConfigDict(env_file=".env")

    _instance: ClassVar[Settings | None] = None

    @classmethod
    def get(cls) -> Settings:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
