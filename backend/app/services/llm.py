from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field, field_validator

CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"
REQUEST_TIMEOUT = 15.0


class LlmError(Exception):
    """A provider error with a message safe to show to the user."""


class ToolFunction(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    arguments: str = Field(max_length=8192)


class ToolCall(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    type: Literal["function"]
    function: ToolFunction


class AssistantReply(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)

    @field_validator("tool_calls", mode="before")
    @classmethod
    def allow_null_tool_calls(cls, value: object) -> object:
        return [] if value is None else value

    def as_message(self) -> dict[str, Any]:
        return {"role": "assistant", **self.model_dump(exclude_none=True)}


class LlmProvider(Protocol):
    def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], *, timeout: float
    ) -> AssistantReply: ...


class GroqProvider:
    def __init__(self, client: httpx.Client, api_key: str, model: str = DEFAULT_MODEL):
        self.client = client
        self.api_key = api_key.strip()
        self.model = model

    def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], *, timeout: float
    ) -> AssistantReply:
        if not self.api_key:
            raise LlmError("請在 .env 或環境變數中設定 GROQ_API_KEY。")

        payload: dict[str, Any] = {
            "model": self.model, "messages": messages, "max_completion_tokens": 2048,
        }
        if self.model in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}:
            payload["include_reasoning"] = False
        if tools:
            payload.update(tools=tools, tool_choice="auto")

        try:
            response = self.client.post(
                CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            message = f"Groq API 請求失敗（HTTP {status}）。"
            if status in (401, 403):
                message += " 請確認 GROQ_API_KEY 有效且專案具有模型存取權。"
            raise LlmError(message) from None
        except httpx.RequestError:
            raise LlmError("Groq API 連線失敗或逾時。") from None

        try:
            choice = response.json()["choices"][0]
            reply = AssistantReply.model_validate(choice["message"])
        except (ValueError, KeyError, IndexError, TypeError):
            raise LlmError("Groq API 回傳了無法解析的回覆。") from None
        if choice.get("finish_reason") in {"length", "content_filter"}:
            raise LlmError("Groq API 未能完成回覆。")
        return reply
