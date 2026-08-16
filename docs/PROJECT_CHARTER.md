# Cloud Nexus OrphanProof Project Charter

Current status: Phase P1 database schema foundation is IMPLEMENTED AND LIVE-VERIFIED. Phase P2 synthetic data ingestion is IMPLEMENTED AND LIVE VERIFIED. Phase P3 local API foundation is implemented. Phase P4 agentic memory integration is implemented locally with unit-test fakes; live verification pending remains true for Bedrock reasoning and Managed MCP. Phase P5 deterministic local vector-memory fallback is implemented and live-verified against CockroachDB vector memory. Phase P6 AWS Lambda public-demo foundation is implemented. The overall application is still under active development.

Cloud Nexus OrphanProof is in an active build phase. This charter describes the intended product direction, safety principles, completed Phase P1 database foundation, implemented and live-verified Phase P2 synthetic data ingestion, implemented P3/P4 local application foundations, planned MVP scope, and demo plan. It does not claim that live P4 provider verification, AWS deployment, dashboard, or human approval interface are complete.

## Problem Statement

Cloud waste tools can identify resources that appear idle, unattached, underused, or expensive. Those signals are useful, but they are not enough to determine whether deleting a resource is safe.

An idle RDS instance might be a disaster-recovery standby. An unattached EBS volume might preserve rollback data from a migration. An Elastic IP address might be reserved for a customer allowlist. Without memory of why a resource exists, cleanup decisions can become risky manual investigations.

## Product Thesis

OrphanProof is planned as a read-only cloud safety assistant that adds memory and evidence to resource cleanup decisions. Instead of only asking whether a resource looks idle, it asks:

- Why did this resource exist?
- What evidence supports that reason?
- Has the context changed?
- What is the safest recommendation for a human reviewer?

The planned product produces explainable verdicts: KEEP, QUARANTINE, or REMOVE.

## Competition Requirement Mapping

The planned MVP is designed to map sponsor technologies to a concrete cloud operations workflow:

- CockroachDB Managed MCP integration: implemented locally; live verification pending local auth.
- CockroachDB Distributed Vector Indexing: Phase P1 schema support and Phase P4 retrieval integration implemented for historical context, incident notes, lifecycle explanations, and similar resource patterns.
- Amazon Bedrock reasoning: local Nova Lite structured reasoning provider implemented; live verification currently provider-throttled.
- AWS Lambda Function URL: implemented as the smallest public HTTPS demo surface.
- AWS API Gateway: planned only if the demo later needs richer routing or authorization.
- Amazon S3 Remediation Passports: planned storage layer for synthetic evidence snapshots, decision evidence, and human-reviewable remediation records.

All competition-facing demonstrations should use synthetic AWS resource evidence unless the user explicitly authorizes a different safe data source.

## Completed Phase P1 Work

Phase P1 database schema foundation is IMPLEMENTED AND LIVE-VERIFIED. Completed work includes:

- CockroachDB orphanproof schema.
- Six persistent-memory tables.
- VECTOR(1024) embedding column.
- Cosine vector index.
- Safe migration and verification runner.
- Static contract tests.
- GitHub Actions contract testing.
- Gitleaks secret scanning.

Phase P1 verification confirmed the schema foundation before application seed rows were loaded.

## Implemented Phase P2 Synthetic Data Ingestion

Phase P2 synthetic data ingestion is IMPLEMENTED AND LIVE VERIFIED. The development CockroachDB cluster contains:

- 18 synthetic resources
- 6 EBS volumes
- 6 Elastic IP addresses
- 6 RDS instances
- 41 memory events
- 3 exceptions
- 8 historical seed decisions
- 2 human approvals
- 0 decision embeddings

The two primary demo stories now exist in CockroachDB:

- RDS disaster-recovery standby evidence supporting KEEP.
- Abandoned EBS volume evidence supporting QUARANTINE.

`orphanproof.decision_embeddings` starts empty after P2 and is populated only by the explicit P4 indexing script.

## Planned Later Phases

- Phase P2 synthetic persistent-memory dataset: implemented and live-verified
- Phase P3 local API foundation: implemented locally
- Phase P4 agentic memory integration: implemented locally; live verification pending
- Phase P5 deterministic local vector-memory fallback: implemented and live-verified
- AWS Lambda Function URL demo: implemented
- AWS API Gateway: planned only if needed later
- Amazon S3 Remediation Passports: planned
- React dashboard: not yet implemented
- Human approval interface: not yet implemented

## MVP Scope

The MVP is planned to support three resource types:

- EBS volumes
- Elastic IP addresses
- RDS instances

The MVP is planned to support three verdicts:

- KEEP: evidence shows the resource likely serves a valid current purpose.
- QUARANTINE: evidence is incomplete, stale, or ambiguous; human review is required before removal.
- REMOVE: evidence indicates the resource is likely abandoned and safe to propose for deletion, subject to human approval.

The MVP should ingest synthetic resource records, attach explanatory memory, retrieve relevant context, and present a recommendation with supporting evidence.

## Explicit Non-Goals

- Automatically deleting AWS resources.
- Automatically modifying AWS infrastructure.
- Requesting, storing, or exposing secrets.
- Using real AWS account IDs, credentials, connection strings, private keys, certificates, or customer data in demos.
- Creating production AWS resources during development.
- Automatically creating CockroachDB resources outside approved migration workflows.
- Building a full cloud cost management platform.
- Supporting every AWS resource type in the MVP.
- Claiming integrations are complete before they are implemented and verified.

## Safety Principles

- Read-only by default.
- Synthetic data by default.
- No hardcoded credentials or secrets.
- No automatic destructive AWS actions.
- Human approval is required for remediation decisions.
- Recommendations must include evidence and uncertainty.
- Documentation must distinguish implemented functionality from planned functionality.
- Demo data must not contain real account identifiers, private infrastructure details, or sensitive customer information.

## Planned Architecture

The planned architecture has five conceptual layers:

- Synthetic evidence layer: demo-safe AWS-like resource records for EBS volumes, Elastic IP addresses, and RDS instances.
- API layer: AWS Lambda and API Gateway are planned to expose read-only evaluation workflows.
- Memory layer: the Phase P1 CockroachDB schema foundation is implemented and live-verified for storing resource history, annotations, evidence events, and durable context.
- Retrieval layer: CockroachDB Distributed Vector Indexing is implemented locally to retrieve similar records and historical explanations.
- Reasoning layer: Amazon Bedrock providers are implemented locally to summarize evidence and generate human-reviewable verdict explanations.

The Phase P1 memory schema foundation, P4 local agentic memory path, P5 local vector fallback, and P6 Lambda demo foundation are implemented. The public Lambda demo is restricted to the two synthetic judge stories and disables public AI-assisted analyze calls. Live Bedrock reasoning verification remains separate because provider throttling prevented a successful Nova pass.

## Implemented Phase P3 Local API Foundation

Phase P3 adds a local read-only FastAPI memory retrieval service. It implements health, resource listing, resource detail, memory-context, and demo endpoints; typed evidence response models; and dependency-injected fake-repository testing.

P3 returns evidence only. It does not generate a current AI verdict, does not use MCP, does not use vector retrieval, does not call Amazon Bedrock, does not deploy to AWS, and does not implement the dashboard.

The safety principles remain unchanged: read-only by default, synthetic data by default, no hardcoded secrets, no automatic destructive AWS actions, and human approval required for any remediation decision.

## Implemented Phase P4 Agentic Memory Foundation

Phase P4 adds the local AI-assisted recommendation path:

- persistent P3 memory context retrieval
- deterministic canonical text for historical decision embeddings
- Amazon Bedrock Titan Text Embeddings V2 provider configured for normalized 1024-dimensional vectors
- idempotent persistence into `orphanproof.decision_embeddings`
- read-only CockroachDB vector similarity search with cosine distance `<=>`
- CockroachDB Cloud Managed MCP read-only client and memory-provider abstraction
- Amazon Bedrock Nova Lite reasoning provider through Converse
- strict JSON parsing and Pydantic validation for current AI verdicts
- P4 agent orchestration and `POST /api/v1/resources/{resource_key}/analyze`
- safe P4 scripts for indexing, MCP verification, and the two primary demo stories

P4 does not persist current AI decisions, does not perform remediation, and does not enumerate real AWS resources. The only AWS client allowed in P4 source is `bedrock-runtime`.

## Persistent-Memory Model

The planned persistent-memory model treats each cloud resource as a timeline of evidence rather than a single current metric.

Planned memory records may include:

- Resource identity using synthetic identifiers.
- Resource type.
- Observed lifecycle events.
- Cost and utilization signals.
- Owner or service annotations when available in synthetic data.
- Historical explanations.
- Prior human review notes.
- Recommendation history.
- Confidence and uncertainty notes.

The goal is to preserve why a resource existed, not only whether it appears idle today.

## Winning Demo Stories

### 1. Idle RDS Disaster-Recovery Standby -> KEEP

This implemented Phase P2 demo story exists in CockroachDB. It presents a quiet RDS instance with low recent utilization. A traditional idle-resource report might flag it for cleanup. OrphanProof stores synthetic memory showing that the instance is a disaster-recovery standby for a critical service and has a recent review note confirming its purpose.

Seed verdict: KEEP

Reason: The resource appears idle, but historical context proves it has a valid resilience role.

### 2. Unattached Abandoned EBS Volume -> QUARANTINE

This implemented Phase P2 demo story exists in CockroachDB. It presents an unattached EBS volume with no recent attachment activity. OrphanProof stores synthetic memory showing that it was created during a migration, but the latest review note is stale and there is not enough evidence to prove it is still needed.

Seed verdict: QUARANTINE

Reason: The resource may be abandoned, but the evidence is incomplete. A human should review before removal.

## Definition of Success for the First Phase

The first phase is successful when the repository has a truthful documentation and database foundation that:

- Describes the product problem and planned solution clearly.
- Defines MVP resource types and verdicts.
- Documents safety principles and non-goals.
- Maps planned sponsor integrations to product responsibilities.
- Establishes agent working rules.
- Implements and live-verifies the Phase P1 CockroachDB schema foundation.
- Adds static contract tests and CI secret scanning.
- Avoids secrets, fake implementation claims, fake deployment links, fake test results, and fake setup instructions.

## Current Status

Phase P1 database schema foundation: IMPLEMENTED AND LIVE-VERIFIED
Phase P2 synthetic data ingestion: IMPLEMENTED AND LIVE VERIFIED
Phase P3 local API foundation: IMPLEMENTED LOCALLY
Phase P4 agentic memory integration: IMPLEMENTED LOCALLY; LIVE INTEGRATION VERIFICATION PENDING
Phase P5 deterministic vector memory: IMPLEMENTED AND LIVE-VERIFIED
Phase P6 Lambda public-demo foundation: IMPLEMENTED

The overall application is still under active development. Local P4 Managed MCP and Bedrock reasoning are implemented but not live-verified in this coding step. AWS API Gateway, Amazon S3 Remediation Passports, the React dashboard, and the human approval interface remain planned or not yet implemented.
