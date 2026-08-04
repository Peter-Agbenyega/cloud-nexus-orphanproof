# Cloud Nexus OrphanProof

AWS detects idle resources. OrphanProof remembers why they exist and proves whether deleting them is safe.

Cloud teams often find AWS resources that look unused: unattached EBS volumes, idle Elastic IP addresses, or quiet RDS instances. The hard part is not detection. The hard part is knowing whether the resource is abandoned, reserved for disaster recovery, tied to a migration, or still needed for a business reason that is not visible in AWS metrics.

Cloud Nexus OrphanProof is a read-only FinOps and cloud safety assistant under active development. It is designed to combine synthetic AWS resource evidence with persistent operational memory, explain why a resource exists, compare current signals against historical context, and produce a human-reviewable verdict before any remediation decision is made.

Phase P1 is implemented and live-verified for the database schema foundation. Phase P2 synthetic persistent-memory data ingestion is implemented and live-verified. The broader application, cloud integrations, reasoning workflow, dashboard, and human approval interface are still planned or not yet implemented.

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

## Planned Sponsor Integrations

- CockroachDB Managed MCP integration: planned
- Amazon Bedrock reasoning: planned
- AWS Lambda and API Gateway: planned
- Amazon S3 Remediation Passports: planned
- CockroachDB Distributed Vector Indexing: Phase P1 schema support is implemented; retrieval integration is planned

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
- Synthetic AWS sample dataset: planned for post-P2 expansion
- Agent verdict workflow: not yet implemented
- React dashboard: not yet implemented
- Human approval interface: not yet implemented

## Safety Position

OrphanProof is designed around explainability and human approval. It should help a reviewer understand the evidence behind a resource decision, but it must not perform destructive AWS actions automatically.
