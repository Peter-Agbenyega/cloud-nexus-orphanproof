"""FastAPI application factory for the Phase P3 memory retrieval API."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from orphanproof import __version__
from orphanproof.agent import OrphanProofAgent
from orphanproof.config import Settings, get_settings
from orphanproof.database import Database
from orphanproof.embeddings import build_current_resource_retrieval_text, create_embedding_provider
from orphanproof.mcp_integration import CockroachManagedMcpClient
from orphanproof.memory_provider import DirectMemoryContextProvider, ManagedMcpMemoryContextProvider
from orphanproof.models import (
    DemoResource,
    HealthResponse,
    MemoryContext,
    MemoryTransport,
    P4AnalysisResponse,
    ResourceDetail,
    ResourceSummary,
    VectorMemoryResponse,
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
    vector_repository: VectorMemoryRepository | None = None,
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

    def get_vector_repository() -> VectorMemoryRepository:
        if vector_repository is not None:
            return vector_repository
        return VectorMemoryRepository(Database(settings=app_settings))

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
            deployment_platform="aws_lambda"
            if app_settings.orphanproof_env == "production"
            else "local",
        )

    @app.get("/", response_class=HTMLResponse)
    def root() -> str:
        return _demo_page_html()

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

    @app.get(
        "/api/v1/resources/{resource_key}/vector-memory",
        response_model=VectorMemoryResponse,
    )
    def get_vector_memory(
        resource_key: str,
        service: MemoryService = Depends(get_service),
        vector_repository: VectorMemoryRepository = Depends(get_vector_repository),
    ) -> VectorMemoryResponse:
        context = service.get_memory_context(resource_key)
        provider = create_embedding_provider(
            model_id=app_settings.bedrock_embedding_model,
            region_name=app_settings.aws_region,
        )
        retrieval_text = build_current_resource_retrieval_text(context)
        query_embedding = provider.embed_query(retrieval_text)
        similar_decisions = vector_repository.find_similar_decisions(query_embedding)
        return service.build_vector_memory_response(
            resource_key=resource_key,
            embedding_model=provider.model_id,
            memory_transport=MemoryTransport.DIRECT_COCKROACHDB,
            similar_historical_decisions=similar_decisions,
        )

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
    app.state.get_vector_repository_dependency = get_vector_repository
    return app


app = create_app()


def _sanitize_api_error(exc: Exception) -> str:
    return "provider failure"


def _demo_page_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cloud Nexus OrphanProof</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17212b;
      --muted: #5d6b78;
      --line: #d9e0e6;
      --panel: #ffffff;
      --bg: #f5f7f8;
      --accent: #0f766e;
      --warn: #b45309;
      --keep: #166534;
      --quarantine: #854d0e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.5;
    }
    main { max-width: 1120px; margin: 0 auto; padding: 40px 20px 56px; }
    header { display: grid; gap: 18px; padding: 22px 0 26px; }
    h1 { margin: 0; font-size: clamp(2.1rem, 5vw, 4.8rem); line-height: 1; letter-spacing: 0; }
    h2 { margin: 0; font-size: 1.05rem; }
    p { margin: 0; }
    .tagline { font-size: clamp(1.2rem, 2vw, 1.55rem); color: var(--accent); font-weight: 700; }
    .subtitle { max-width: 760px; color: var(--muted); font-size: 1.06rem; }
    .safety {
      display: flex;
      flex-wrap: wrap;
      gap: 10px 16px;
      padding: 14px 16px;
      border: 1px solid #f2c48d;
      border-left: 5px solid var(--warn);
      background: #fff8ed;
      font-weight: 700;
    }
    .strip {
      display: grid;
      grid-template-columns: repeat(5, minmax(130px, 1fr));
      gap: 8px;
      margin: 22px 0 28px;
    }
    .strip span {
      border: 1px solid var(--line);
      background: #eef4f3;
      padding: 10px;
      min-height: 58px;
      display: flex;
      align-items: center;
      font-size: .88rem;
      font-weight: 700;
    }
    .cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      display: grid;
      gap: 14px;
      min-width: 0;
    }
    .key {
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: .9rem;
      overflow-wrap: anywhere;
    }
    .signals { display: flex; flex-wrap: wrap; gap: 8px; }
    .signals span {
      border: 1px solid var(--line);
      background: #f8fafb;
      padding: 5px 8px;
      border-radius: 4px;
      font-size: .84rem;
    }
    button {
      justify-self: start;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: white;
      padding: 10px 13px;
      font-weight: 800;
      cursor: pointer;
      min-height: 42px;
    }
    button:disabled { opacity: .7; cursor: wait; }
    .result {
      border-top: 1px solid var(--line);
      padding-top: 12px;
      min-height: 92px;
      color: var(--muted);
      overflow-wrap: anywhere;
    }
    .verdict { font-weight: 900; color: var(--ink); }
    .KEEP { color: var(--keep); }
    .QUARANTINE { color: var(--quarantine); }
    .note { margin-top: 22px; color: var(--muted); font-size: .94rem; }
    @media (max-width: 820px) {
      main { padding-top: 26px; }
      .cards, .strip { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Cloud Nexus OrphanProof</h1>
      <p class="tagline">Idle doesn't mean orphaned.</p>
      <p class="subtitle">
        AWS finds resources that look idle. OrphanProof remembers why they exist
        and proves whether removal is safe.
      </p>
    </header>
    <section class="safety" aria-label="Safety banner">
      <span>OrphanProof recommends and explains.</span>
      <span>It never deletes cloud resources automatically.</span>
      <span>Human review required.</span>
    </section>
    <section class="strip" aria-label="Architecture">
      <span>CockroachDB Persistent Memory</span>
      <span>CockroachDB Distributed Vector Indexing</span>
      <span>AWS Lambda</span>
      <span>Amazon Bedrock Integration</span>
      <span>Human Review Required</span>
    </section>
    <section class="cards">
      <article class="card">
        <div>
          <h2>Disaster Recovery RDS</h2>
          <p class="key">demo-rds-dr-standby-001</p>
        </div>
        <p>
          Looks idle, but memory shows DR purpose, dependency evidence,
          an active exception, and a historical KEEP decision.
        </p>
        <div class="signals">
          <span>looks idle</span><span>DR purpose</span>
          <span>dependency evidence</span><span>historical KEEP</span>
        </div>
        <button type="button" data-resource="demo-rds-dr-standby-001">Analyze Memory</button>
        <div class="result" id="result-demo-rds-dr-standby-001">Waiting for memory analysis.</div>
      </article>
      <article class="card">
        <div>
          <h2>Abandoned EBS Volume</h2>
          <p class="key">demo-ebs-abandoned-001</p>
        </div>
        <p>
          Unattached volume with departed fictional owner, no active exception,
          and a historical QUARANTINE decision.
        </p>
        <div class="signals">
          <span>unattached</span><span>departed owner</span>
          <span>no active exception</span><span>historical QUARANTINE</span>
        </div>
        <button type="button" data-resource="demo-ebs-abandoned-001">Analyze Memory</button>
        <div class="result" id="result-demo-ebs-abandoned-001">Waiting for memory analysis.</div>
      </article>
    </section>
    <p class="note">
      Bedrock integration available; live embedding/reasoning currently
      provider-throttled. This public demo uses truthful deterministic local
      vector embeddings against CockroachDB memory.
    </p>
  </main>
  <script>
    const labels = {
      active_exception_exists: "active exception",
      dependency_evidence_exists: "dependency evidence",
      ownership_evidence_exists: "ownership evidence",
      prior_keep_exists: "prior KEEP",
      prior_quarantine_exists: "prior QUARANTINE"
    };
    async function analyze(resourceKey, button) {
      const result = document.getElementById(`result-${resourceKey}`);
      button.disabled = true;
      result.textContent = "Querying CockroachDB vector memory...";
      try {
        const response = await fetch(`/api/v1/resources/${resourceKey}/vector-memory`);
        if (!response.ok) throw new Error("analysis unavailable");
        const payload = await response.json();
        const nearest = payload.similar_historical_decisions[0];
        const activeSignals = Object.entries(payload.evidence_signals)
          .filter(([, value]) => value)
          .map(([key]) => labels[key] || key.replaceAll("_", " "))
          .slice(0, 5)
          .join(", ");
        result.innerHTML = `
          <div>
            Nearest historical verdict:
            <span class="verdict ${nearest.historical_verdict}">
              ${nearest.historical_verdict}
            </span>
          </div>
          <div>Similarity: ${Number(nearest.similarity).toFixed(3)}</div>
          <div>Relevant evidence: ${activeSignals || "stored memory evidence"}</div>
          <div>Embedding provider: ${payload.embedding_model}</div>
          <div>
            Human review required.
            Automatic action taken: ${payload.automatic_action_taken}.
          </div>
        `;
      } catch (_error) {
        result.textContent = "Memory analysis is unavailable. No cloud action was taken.";
      } finally {
        button.disabled = false;
      }
    }
    document.querySelectorAll("button[data-resource]").forEach((button) => {
      button.addEventListener("click", () => analyze(button.dataset.resource, button));
    });
  </script>
</body>
</html>"""
