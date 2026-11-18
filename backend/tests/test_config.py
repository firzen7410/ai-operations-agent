from pathlib import Path

import pytest
from sqlalchemy.engine import URL, make_url

from backend.app.config import PROJECT_ROOT, Settings


def test_default_database_is_independent_of_working_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)

    assert Path(make_url(Settings(_env_file=None).database_url).database) == PROJECT_ROOT / "operations.db"


def test_relative_sqlite_url_is_resolved_from_project_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./operations.db?timeout=5")

    url = make_url(Settings(_env_file=None).database_url)
    assert Path(url.database) == PROJECT_ROOT / "operations.db"
    assert url.query["timeout"] == "5"


@pytest.mark.parametrize("url", ["sqlite:///:memory:", "sqlite:///file:shared?mode=memory&uri=true"])
def test_memory_sqlite_urls_are_preserved(url):
    assert Settings(database_url=url, _env_file=None).database_url == url


def test_absolute_sqlite_url_is_preserved(tmp_path):
    url = URL.create("sqlite", database=str(tmp_path / "custom.db")).render_as_string()

    assert Settings(database_url=url, _env_file=None).database_url == url
