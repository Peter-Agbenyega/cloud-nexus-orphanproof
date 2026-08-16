"""FastAPI application factory for the Phase P3 memory retrieval API."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orphanproof import __version__
from orphanproof.agent import OrphanProofAgent
from orphanproof.config import Settings, get_settings
from orphanproof.database import Database
from orphanproof.embeddings import create_embedding_provider
from orphanproof.mcp_integration import CockroachManagedMcpClient
from orphanproof.memory_provider import DirectMemoryContextProvider, ManagedMcpMemoryContextProvider
from orphanproof.models import (
    DemoResource,
    HealthResponse,
    MemoryContext,
    P4AnalysisResponse,
    ResourceDetail,
    ResourceSummary,
)
from orphanproof.reasoning import BedrockReasoningProvider
from orphanproof.repository import MemoryRepository, MemoryRepositoryProtocol
from orphanproof.service import InvalidPaginationError, MemoryService, ResourceNotFoundError
from orphanproof.vector_memory import VectorMemoryRepository

SERVICE_NAME = "cloud-nexus-orphanproof"
PHASE = "P3_MEMORY_RETRIEVAL"


def _build_live_repository(settings: Settings) -> MemoryRepository:
    return MemoryRepository(Database(settings=settings))


def create_app(
    repository: MemoryRepositoryProtocol | None = None,
    agent: OrphanProofAgent | None = None,
    settings: Settings | None = None,
    now_provider: Callable[[], datetime] | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title="Cloud Nexus OrphanProof API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    def get_repository() -> MemoryRepositoryProtocol:
        if repository is not None:
            return repository
        return _build_live_repository(app_settings)

    def get_service(repo: MemoryRepositoryProtocol = Depends(get_repository)) -> MemoryService:
        return MemoryService(repo, now_provider=now_provider)

    def get_agent(repo: MemoryRepositoryProtocol = Depends(get_repository)) -> OrphanProofAgent:
        if agent is not None:
            return agent
        database = Database(settings=app_settings)
        if app_settings.mcp_enabled:
            if not app_settings.mcp_is_configured():
                raise RuntimeError("MCP mode is enabled but MCP runtime auth is not configured")
            memory_provider = ManagedMcpMemoryContextProvider(
                CockroachManagedMcpClient(app_settings),
                now_provider=now_provider,
            )
        else:
            memory_provider = DirectMemoryContextProvider(repo, now_provider=now_provider)
        return OrphanProofAgent(
            memory_provider=memory_provider,
            embedding_provider=create_embedding_provider(
                model_id=app_settings.bedrock_embedding_model,
                region_name=app_settings.aws_region,
            ),
            vector_repository=VectorMemoryRepository(database),
            reasoning_provider=BedrockReasoningProvider(
                model_id=app_settings.bedrock_reasoning_model,
                region_name=app_settings.aws_region,
            ),
        )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(_request: Any, exc: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": {"message": "resource not found", "resource_key": str(exc)}},
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(_request: Any, _exc: RuntimeError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": {"message": "service provider is not configured or unavailable"}},
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=SERVICE_NAME,
            version=__version__,
            phase=PHASE,
            environment=app_settings.orphanproof_env,
            database_mode="dependency_injected",
        )

    @app.get("/api/v1/resources", response_model=list[ResourceSummary])
    def list_resources(
        resource_type: str | None = Query(
            default=None,
            pattern="^(EBS_VOLUME|ELASTIC_IP|RDS_INSTANCE)$",
        ),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        service: MemoryService = Depends(get_service),
    ) -> list[ResourceSummary]:
        try:
            return service.list_resources(resource_type=resource_type, limit=limit, offset=offset)
        except InvalidPaginationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/v1/resources/{resource_key}", response_model=ResourceDetail)
    def get_resource(
        resource_key: str,
        service: MemoryService = Depends(get_service),
    ) -> ResourceDetail:
        return service.get_resource(resource_key)

    @app.get("/api/v1/resources/{resource_key}/memory-context", response_model=MemoryContext)
    def get_memory_context(
        resource_key: str,
        service: MemoryService = Depends(get_service),
    ) -> MemoryContext:
        return service.get_memory_context(resource_key)

    @app.post("/api/v1/resources/{resource_key}/analyze", response_model=P4AnalysisResponse)
    def analyze_resource(
        resource_key: str,
        analysis_agent: OrphanProofAgent = Depends(get_agent),
    ) -> P4AnalysisResponse:
        try:
            return analysis_agent.analyze_resource(resource_key)
        except ResourceNotFoundError:
            raise
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail={"message": _sanitize_api_error(exc)},
            ) from exc

    @app.get("/api/v1/demo")
    def get_demo(service: MemoryService = Depends(get_service)) -> dict[str, Any]:
        demo = service.get_demo_links()
        demo["resources"] = [
            DemoResource.model_validate(resource).model_dump(mode="json")
            for resource in demo["resources"]
        ]
        return demo

    app.dependency_overrides_provider = app
    app.state.get_repository_dependency = get_repository
    app.state.get_service_dependency = get_service
    app.state.get_agent_dependency = get_agent
    return app


app = create_app()


def _sanitize_api_error(exc: Exception) -> str:
    return "provider failure"
