from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Voice-Driven Clinical AI"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(default="change-me-in-production", min_length=16)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/clinical_ai"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
    ]

    asr_provider: str = "faster_whisper"
    sarvam_api_key: str | None = None
    sarvam_asr_model: str = "saaras:v3"
    sarvam_asr_mode: str = "translate"
    sarvam_asr_timeout_seconds: int = 900
    sarvam_asr_poll_interval_seconds: int = 5
    whisper_model_size: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_whisper_model: str = "whisper-1"
    embedding_provider: str = "local"
    embedding_model: str = "all-MiniLM-L6-v2"

    faiss_index_path: str = "/app/data/faiss/clinical.index"
    faiss_metadata_path: str = "/app/data/faiss/clinical-meta.json"

    seed_demo_data: bool = True
    demo_doctor_username: str = "doctor"
    demo_doctor_password: str = "doctor123"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def faiss_index_dir(self) -> Path:
        return Path(self.faiss_index_path).parent


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
