from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from asterum.data.asset_audit import AssetAuditReport, audit_assets

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MAPPING_PATH = PROJECT_ROOT / "assets/asterum/mapping/asterum.mapping.v1.json"


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(HealthResponse):
    mapping_version: str | None = None
    character_count: int = 0
    issues: list[str] = Field(default_factory=list)


def resolve_mapping_path() -> Path:
    configured_path = os.getenv("ASTERUM_MAPPING_PATH")
    if configured_path is None:
        return DEFAULT_MAPPING_PATH

    path = Path(configured_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def create_app(mapping_path: Path | None = None) -> FastAPI:
    selected_mapping_path = mapping_path or resolve_mapping_path()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.asset_audit = audit_assets(selected_mapping_path)
        yield

    application = FastAPI(
        title="Asterum Interpreter API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/health/live", response_model=HealthResponse)
    def live() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.get(
        "/health/ready",
        response_model=ReadinessResponse,
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
    )
    def ready(request: Request) -> ReadinessResponse | JSONResponse:
        report: AssetAuditReport = request.app.state.asset_audit
        payload = ReadinessResponse(
            status="ready" if report.ok else "not_ready",
            mapping_version=report.mapping_version,
            character_count=report.character_count,
            issues=[issue.code for issue in report.issues],
        )
        if report.ok:
            return payload
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    return application


app = create_app()


def run() -> None:
    uvicorn.run("asterum.api.main:app", host="127.0.0.1", port=8000, reload=False)
