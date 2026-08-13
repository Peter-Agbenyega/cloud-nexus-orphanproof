# Cloud Nexus OrphanProof API

Phase P3 implements a local, read-only FastAPI memory retrieval service. Phase P4 adds an AI-assisted analysis endpoint that combines persistent memory, Titan embeddings, CockroachDB vector retrieval, and Nova reasoning when live providers are configured.

The P3 memory-context endpoint does not generate an AI verdict. Historical seed decisions are returned as historical evidence only.

## Implemented in Phase P3

- Read-only FastAPI service foundation
- Resource listing and detail endpoints
- Complete memory-context endpoint
- Demo links for the two primary synthetic resources
- Pydantic response models for evidence packages
- Dependency injection for fake-repository testing
- Local unittest coverage for models, repository contracts, service behavior, and API behavior

## Still Planned

- Live Managed MCP verification
- Live Bedrock verification
- Dashboard
- AWS deployment
- Human approval workflow UI

No automatic deletion, release, mutation, or remediation workflow exists in P3 or P4.

## Local Environment

Use Python 3.11 or newer. Create and use a local virtual environment:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

The project supports editable development installation through `pyproject.toml`.

## Safe Environment Variables

Use `.env.example` as the safe template. Never commit `.env`, and never paste credentials into documentation, tests, or source code.

Safe non-secret local examples:

```text
ORPHANPROOF_ENV=development
ORPHANPROOF_CORS_ORIGINS=http://localhost:5173
ORPHANPROOF_LOG_LEVEL=INFO
ORPHANPROOF_AWS_REGION=us-east-1
ORPHANPROOF_BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
ORPHANPROOF_BEDROCK_REASONING_MODEL=amazon.nova-lite-v1:0
ORPHANPROOF_MCP_ENABLED=false
ORPHANPROOF_MCP_URL=https://cockroachlabs.cloud/mcp
```

Live database use requires `DATABASE_URL`, but the value must be placed only in the ignored local `.env` file or a managed secret service. Obtain the connection value from the approved CockroachDB connection workflow. Never copy the value into source code, documentation, screenshots, logs, terminal output, or Git history.

Managed MCP live verification also requires local `ORPHANPROOF_MCP_CLUSTER_ID` and `ORPHANPROOF_MCP_BEARER_TOKEN` values. These are intentionally omitted from `.env.example` and must never be pasted into chat, source, documentation, logs, or test fixtures.

P3 tests use fake repositories and do not require `.env` or a live database connection.

Exception evidence uses effective status. A stored `ACTIVE` exception protects a resource only until its `expires_at` time is reached; after that instant it is treated as expired for evidence counts and signals. The stored historical `ResourceException` record is returned unchanged and is not mutated by the API.

## Local Run Command

Run the local API with:

```bash
.venv/bin/uvicorn orphanproof.api:app --reload --host 127.0.0.1 --port 8000
```

Do not run against a real database unless the local environment has been reviewed and intentionally configured.

## Endpoints

### `GET /health`

Returns service status and P3 mode:

```bash
curl http://127.0.0.1:8000/health
```

Expected P3 fields include:

- `phase`: `P3_MEMORY_RETRIEVAL`
- `database_mode`: `dependency_injected`
- `analysis_mode`: `evidence_only`
- `ai_verdict_generated`: `false`

### `GET /api/v1/resources`

Lists resources ordered by resource key.

Query parameters:

- `resource_type`: optional, one of `EBS_VOLUME`, `ELASTIC_IP`, `RDS_INSTANCE`
- `limit`: default `50`, minimum `1`, maximum `100`
- `offset`: default `0`, minimum `0`

Examples:

```bash
curl "http://127.0.0.1:8000/api/v1/resources?limit=50&offset=0"
curl "http://127.0.0.1:8000/api/v1/resources?resource_type=RDS_INSTANCE"
```

### `GET /api/v1/resources/{resource_key}`

Returns resource details without the full memory context.

```bash
curl http://127.0.0.1:8000/api/v1/resources/demo-rds-dr-standby-001
```

### `GET /api/v1/resources/{resource_key}/memory-context`

Returns the complete evidence package for a resource:

- Resource identity and current evidence
- Ordered memory events
- Active and expired exceptions
- Historical seed decisions
- Human approval records
- Evidence counts
- Evidence signals
- `analysis_mode = evidence_only`
- `ai_verdict_generated = false`

```bash
curl http://127.0.0.1:8000/api/v1/resources/demo-ebs-abandoned-001/memory-context
```

### `GET /api/v1/demo`

Returns links and descriptions for the two primary synthetic demo stories:

- `demo-rds-dr-standby-001`: disaster-recovery standby story
- `demo-ebs-abandoned-001`: abandoned-volume investigation story

```bash
curl http://127.0.0.1:8000/api/v1/demo
```

The demo endpoint states that records are synthetic, the API provides evidence only, and no new AI verdict has been generated.

### `POST /api/v1/resources/{resource_key}/analyze`

Runs the P4 AI-assisted analysis path for a known synthetic resource. This endpoint may invoke Bedrock and vector search when live providers are configured.

Required safety fields in successful responses:

- `analysis_mode`: `ai_assisted`
- `ai_verdict_generated`: `true`
- `decision_persisted`: `false`
- `automatic_action_taken`: `false`
- `human_review_required`: `true`

The response includes the current AI recommendation, similar historical decisions without raw embeddings, evidence signals, memory transport provenance, and configured model IDs. It does not perform remediation and does not persist a current decision.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/resources/demo-rds-dr-standby-001/analyze
```

Provider failures return sanitized errors and must not include database URLs, AWS credentials, MCP credentials, full embeddings, raw provider responses, or stack traces.
