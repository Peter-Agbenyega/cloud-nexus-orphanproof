"""FastAPI application factory for the Phase P3 memory retrieval API."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orphanproof import __version__
from orphanproof.config import Settings, get_settings
from orphanproof.database import Database
from orphanproof.models import (
    DemoResource,
    HealthResponse,
    MemoryContext,
    ResourceDetail,
    ResourceSummary,
)
from orphanproof.repository import MemoryRepository, MemoryRepositoryProtocol
from orphanproof.service import InvalidPaginationError, MemoryService, ResourceNotFoundError

SERVICE_NAME = "cloud-nexus-orphanproof"
PHASE = "P3_MEMORY_RETRIEVAL"


def _build_live_repository(settings: Settings) -> MemoryRepository:
    return MemoryRepository(Database(settings=settings))


def create_app(
    repository: MemoryRepositoryProtocol | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title="Cloud Nexus OrphanProof API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    def get_repository() -> MemoryRepositoryProtocol:
        if repository is not None:
            return repository
        return _build_live_repository(app_settings)

    def get_service(repo: MemoryRepositoryProtocol = Depends(get_repository)) -> MemoryService:
        return MemoryService(repo)

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
            content={"detail": {"message": "service is not configured for live database access"}},
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
    return app


app = create_app()
