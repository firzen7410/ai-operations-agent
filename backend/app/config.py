from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def local_database_url() -> str:
    return URL.create("sqlite", database=str(PROJECT_ROOT / "operations.db")).render_as_string()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = Field(default_factory=local_database_url)
    groq_api_key: SecretStr | None = None
    groq_model: str = Field(default="openai/gpt-oss-20b", min_length=1)

    @field_validator("database_url")
    @classmethod
    def resolve_sqlite_path(cls, value: str) -> str:
        url = make_url(value)
        database = url.database
        if url.get_backend_name() != "sqlite" or not database or database == ":memory:":
            return value
        if database.startswith("file:") and url.query.get("uri") == "true":
            return value
        path = Path(database)
        if path.is_absolute():
            return value
        return url.set(database=str((PROJECT_ROOT / path).resolve())).render_as_string()
