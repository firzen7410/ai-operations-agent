from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.app.api.agent import router as agent_router
from backend.app.api.orders import router as orders_router
from backend.app.api.products import router as products_router
from backend.app.api.sales import router as sales_router
from backend.app.config import Settings
from backend.app.db import build_engine
from backend.app.services.errors import ConflictError, NotFoundError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    engine = build_engine(settings.database_url)
    app.state.db_engine = engine
    app.state.settings = settings
    try:
        with httpx.Client() as llm_client:
            app.state.llm_client = llm_client
            yield
    finally:
        engine.dispose()


app = FastAPI(title="AI Operations Agent", lifespan=lifespan)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(sales_router)
app.include_router(agent_router)


@app.exception_handler(NotFoundError)
def handle_not_found(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def handle_conflict(_request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok"}
