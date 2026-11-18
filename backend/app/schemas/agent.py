from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue, StringConstraints

from backend.app.models import AgentRunStatus, ToolExecutionStatus
from backend.app.schemas.common import UtcTimestamp


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ToolExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tool_name: str
    arguments: dict[str, JsonValue] | None
    result: dict[str, JsonValue] | None
    status: ToolExecutionStatus
    error_message: str | None
    created_at: UtcTimestamp


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_message: str
    status: AgentRunStatus
    response: str | None
    error_message: str | None
    created_at: UtcTimestamp
    completed_at: UtcTimestamp | None
    tool_executions: list[ToolExecutionRead]
