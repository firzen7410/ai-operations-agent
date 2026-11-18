import json
from functools import partial
from unittest.mock import Mock

import httpx
import pytest

from backend.scripts import test_groq
from backend.app.config import Settings


@pytest.fixture
def request_handler(monkeypatch, tmp_path):
    monkeypatch.setattr(test_groq, "Settings", partial(Settings, _env_file=tmp_path / ".env"))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "old-provider-key")
    monkeypatch.setattr("sys.argv", ["test_groq"])

    handler = Mock()
    transport = httpx.MockTransport(handler)
    client_class = httpx.Client

    def create_client(**options):
        return client_class(transport=transport, **options)

    monkeypatch.setattr(test_groq.httpx, "Client", create_client)
    return handler


@pytest.mark.parametrize("model", [None, "another-model"])
def test_smoke_sends_prompt_and_prints_reply(request_handler, tmp_path, capsys, monkeypatch, model):
    (tmp_path / ".env").write_text("GROQ_API_KEY=test-value\n", encoding="utf-8")
    if model is not None:
        monkeypatch.setattr("sys.argv", ["test_groq", "--model", model])
    request_handler.return_value = httpx.Response(
        200, json={"choices": [{"message": {"content": "我是 AI 助手。"}}]}
    )

    test_groq.main()

    request, = request_handler.call_args.args
    assert request.method == "POST"
    assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-value"
    assert request.extensions["timeout"]["read"] == 15.0
    expected = {
        "model": model or "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": "請用一句話介紹你自己。"}],
        "max_completion_tokens": 2048,
    }
    if model is None:
        expected["include_reasoning"] = False
    assert json.loads(request.content) == expected
    assert capsys.readouterr().out == "我是 AI 助手。\n"


def test_smoke_requires_groq_key(request_handler):
    with pytest.raises(SystemExit, match="GROQ_API_KEY"):
        test_groq.main()

    request_handler.assert_not_called()


def test_smoke_reports_timeout(request_handler, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-value")
    request_handler.side_effect = httpx.ReadTimeout("internal details")

    with pytest.raises(SystemExit, match="連線失敗或逾時") as exc:
        test_groq.main()

    assert "internal details" not in str(exc.value)


@pytest.mark.parametrize("status", [401, 403])
def test_smoke_reports_access_failure(request_handler, monkeypatch, status):
    monkeypatch.setenv("GROQ_API_KEY", "test-value")
    request_handler.return_value = httpx.Response(status, text="internal details")

    with pytest.raises(SystemExit, match=f"HTTP {status}.*GROQ_API_KEY") as exc:
        test_groq.main()

    assert "internal details" not in str(exc.value)


@pytest.mark.parametrize(
    ("payload", "message"),
    [({"choices": []}, "無法解析"), ({"choices": [{"message": {"content": None}}]}, "沒有回傳文字")],
)
def test_smoke_handles_invalid_reply(request_handler, monkeypatch, payload, message):
    monkeypatch.setenv("GROQ_API_KEY", "test-value")
    request_handler.return_value = httpx.Response(200, json=payload)

    with pytest.raises(SystemExit, match=message):
        test_groq.main()
