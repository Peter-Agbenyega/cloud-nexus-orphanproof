# Cloud Nexus OrphanProof

AWS detects idle resources. OrphanProof remembers why they exist and proves whether deleting them is safe.

Cloud teams often find AWS resources that look unused: unattached EBS volumes, idle Elastic IP addresses, or quiet RDS instances. The hard part is not detection. The hard part is knowing whether the resource is abandoned, reserved for disaster recovery, tied to a migration, or still needed for a business reason that is not visible in AWS metrics.

Cloud Nexus OrphanProof is a read-only FinOps and cloud safety assistant under active development. It is designed to combine synthetic AWS resource evidence with persistent operational memory, explain why a resource exists, compare current signals against historical context, and produce a human-reviewable verdict before any remediation decision is made.

Phase P1 is implemented and live-verified for the database schema foundation. Phase P2 synthetic persistent-memory data ingestion is implemented and live-verified. Phase P3 local read-only memory retrieval is implemented. Phase P4 agentic memory integration is implemented locally with unit-test fakes; live provider verification remains separate. Phase P5 local deterministic vector-memory fallback is implemented and has been live-verified against CockroachDB decision embeddings using `local.feature-hash-v1`.

## Implemented Phase P1 Foundation

- CockroachDB orphanproof schema
- Six persistent-memory tables
- VECTOR(1024) embedding column
- Cosine vector index
- Safe migration and verification runner
- Static contract tests
- GitHub Actions contract testing
- Gitleaks secret scanning

Phase P1 verification confirmed the schema foundation before application seed rows were loaded.

## Implemented Phase P2 Dataset

The development CockroachDB cluster now contains the Phase P2 synthetic persistent-memory dataset:

- 18 synthetic resources
- 6 EBS volumes
- 6 Elastic IP addresses
- 6 RDS instances
- 41 memory events
- 3 exceptions
- 8 historical seed decisions
- 2 human approvals
- 0 decision embeddings

The seed was run twice and remained idempotent. Live verification returned PASS.

This confirms the synthetic data foundation only. MCP integration, Amazon Bedrock reasoning, vector retrieval, the agent workflow, the dashboard, and AWS deployment remain planned or not yet implemented. The application and AI agent are not complete.

## Implemented Phase P3 API Foundation

The local Phase P3 API foundation is implemented for read-only memory retrieval:

- Read-only FastAPI memory retrieval service is implemented locally.
- Evidence response models are implemented.
- Dependency injection and fake-repository testing are implemented.
- Health, resource, memory-context, and demo endpoints are implemented.
- P3 has not yet been live-tested against CockroachDB during this coding step.
- MCP is still planned.
- Vector similarity retrieval is still planned.
- Bedrock reasoning is still planned.
- AWS deployment is still planned.
- The AI agent is not complete.
- No current AI verdict is generated.

Local API documentation is available in `docs/API.md`.

## Implemented Phase P4 Agentic Memory Foundation

Phase P4 adds the local application intelligence path:

- deterministic canonical memory text for historical decisions
- Amazon Bedrock Titan Text Embeddings V2 provider for `VECTOR(1024)` embeddings, with configurable Cohere Embed v4 fallback
- scoped `orphanproof.decision_embeddings` persistence
- CockroachDB cosine vector similarity search using `<=>`
- CockroachDB Cloud Managed MCP read-only client and memory-provider abstraction
- Amazon Bedrock Nova Lite structured reasoning provider
- strict Pydantic validation for current AI verdicts
- P4 orchestrator and `POST /api/v1/resources/{resource_key}/analyze`
- safe indexing, MCP verification, and two-story demo scripts

P4 preserves P3 evidence-only semantics. `/memory-context` still returns `analysis_mode = evidence_only` and does not generate a current AI verdict.

P4 does not automatically delete, stop, detach, release, terminate, resize, or otherwise mutate AWS resources. A `REMOVE` verdict is only a recommendation and always requires human review. P4 does not persist current AI decisions to `orphanproof.decisions`.

Live verification status for P4 is not claimed until the local live scripts complete successfully.

## Implemented Phase P5 Local Vector-Memory Fallback

Phase P5 adds a truthful deterministic embedding provider for deadline-safe demos:

- `local.feature-hash-v1` produces 1024-dimensional normalized embeddings without network calls.
- The same provider can embed historical decision documents and current resource queries.
- CockroachDB vector retrieval remains read-only and returns historical decisions as evidence.
- Live verification confirmed eight historical decisions and eight decision embeddings.
- The demo RDS story retrieved historical `KEEP`; the demo EBS story retrieved historical `QUARANTINE`.

This local provider exists because live Bedrock embedding and reasoning calls were provider-throttled during deadline testing. Titan, Cohere Embed v4, and Nova Lite support remains implemented, but this repository does not claim live Bedrock reasoning passed.

## Implemented Phase P6 Lambda Demo Foundation

Phase P6 adds the smallest serverless public-demo path for judges:

- FastAPI runs on AWS Lambda through `Mangum`.
- A Lambda Function URL can expose the public HTTPS demo without API Gateway.
- `GET /` serves a dependency-light HTML demo page.
- `GET /api/v1/resources/{resource_key}/vector-memory` runs a deterministic vector-memory demonstration without Nova, Titan, or Cohere calls.
- The public demo is configured to use `ORPHANPROOF_BEDROCK_EMBEDDING_MODEL=local.feature-hash-v1`.
- The Lambda reads the database URL from AWS Systems Manager Parameter Store SecureString by parameter name; the connection string is not stored in source, Git, tests, or docs.

P6 does not add automatic remediation. It does not create EC2, ECS, EKS, NAT Gateway, RDS, OpenSearch, SageMaker, or CloudFront resources. It remains read-only by default and requires human review for remediation decisions.

## Sponsor Integrations

- CockroachDB Managed MCP integration: implemented locally; live verification pending local auth
- Amazon Bedrock Titan Text Embeddings V2: implemented locally; live invocation currently provider-throttled
- Amazon Bedrock Cohere Embed v4 fallback: implemented locally; live invocation currently provider-throttled
- Amazon Bedrock Nova Lite reasoning: implemented locally; live invocation currently provider-throttled
- AWS Lambda and API Gateway: Lambda Function URL foundation implemented for the current public demo; API Gateway remains planned only if later routing or authorization needs justify it
- AWS Lambda Function URL: deployment foundation implemented
- AWS API Gateway: not required for the current smallest public demo
- Amazon S3 Remediation Passports: planned
- CockroachDB Distributed Vector Indexing: schema and retrieval integration implemented; local deterministic vector memory live-verified

## Supported MVP Resource Types

The MVP is planned to evaluate three AWS resource types:

- EBS volumes
- Elastic IP addresses
- RDS instances

## Planned Verdicts

OrphanProof is planned to produce one of three verdicts:

- KEEP
- QUARANTINE
- REMOVE

These verdicts are recommendations for human review. The system is read-only and never automatically deletes AWS resources.

## Demonstration Data

For hackathon demonstrations, OrphanProof uses synthetic AWS resource evidence by default. Synthetic evidence keeps the demo safe, repeatable, and free from real account identifiers, credentials, customer data, or production infrastructure details.

Current data status:

- Phase P2 synthetic persistent-memory dataset: implemented and live-verified
- Phase P4 agent verdict workflow: implemented locally; live Bedrock verification currently throttled
- Phase P5 deterministic CockroachDB vector-memory demo: implemented and live-verified
- Phase P6 AWS Lambda public-demo foundation: implemented
- React dashboard: not yet implemented
- Human approval interface: not yet implemented

## Safety Position

OrphanProof is designed around explainability and human approval. It should help a reviewer understand the evidence behind a resource decision, but it must not perform destructive AWS actions automatically.
