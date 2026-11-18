from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request, status

from backend.app.agent.orchestrator import get_run, run_agent
from backend.app.db import DbSession
from backend.app.models import AgentRun
from backend.app.schemas.agent import AgentRequest, AgentRunRead
from backend.app.services.llm import GroqProvider, LlmProvider

router = APIRouter(prefix="/agent/runs", tags=["Agent"])


def get_provider(request: Request) -> LlmProvider:
    settings = request.app.state.settings
    client: httpx.Client = request.app.state.llm_client
    key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else ""
    return GroqProvider(client, key, settings.groq_model)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AgentRunRead)
def create_run(
    payload: AgentRequest, session: DbSession, provider: Annotated[LlmProvider, Depends(get_provider)]
) -> AgentRun:
    return run_agent(session, payload.message, provider)


@router.get("/{run_id}", response_model=AgentRunRead)
def read_run(run_id: UUID, session: DbSession) -> AgentRun:
    return get_run(session, run_id)
