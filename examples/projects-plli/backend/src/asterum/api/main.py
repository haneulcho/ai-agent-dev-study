"""아스테룸 API 애플리케이션과 현재 제공하는 상태 확인 endpoint."""

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
    """환경변수에 매핑 경로가 있으면 사용하고, 없으면 프로젝트 기본값을 반환한다."""

    configured_path = os.getenv("ASTERUM_MAPPING_PATH")
    if configured_path is None:
        return DEFAULT_MAPPING_PATH

    path = Path(configured_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def create_app(mapping_path: Path | None = None) -> FastAPI:
    """테스트와 실행 환경에서 원하는 매핑 파일을 주입할 수 있는 FastAPI 앱을 만든다."""

    selected_mapping_path = mapping_path or resolve_mapping_path()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # 서버 시작 시 한 번만 자산을 검사해 모든 요청마다 SVG를 다시 읽지 않게 한다.
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
        # 매핑이나 SVG가 잘못되면 트래픽을 받지 않도록 503으로 준비 실패를 알린다.
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
    """``uv run asterum-api`` 명령이 호출하는 로컬 개발 서버 진입점."""

    uvicorn.run("asterum.api.main:app", host="127.0.0.1", port=8000, reload=False)
