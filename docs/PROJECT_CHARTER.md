# Cloud Nexus OrphanProof Project Charter

Current status: PLANNED / NOT YET IMPLEMENTED

Cloud Nexus OrphanProof is in the initial build phase. This charter describes the intended product direction, safety principles, MVP scope, and demo plan. It does not claim that application features, cloud integrations, persistence, tests, or deployment are already implemented.

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

- CockroachDB Cloud Managed MCP Server: planned interface for managed operational memory and structured resource evidence.
- CockroachDB Distributed Vector Indexing: planned retrieval layer for historical context, incident notes, lifecycle explanations, and similar resource patterns.
- Amazon Bedrock: planned reasoning layer for summarizing evidence and producing explainable recommendations.
- AWS Lambda and API Gateway: planned serverless API surface for demo workflows.
- Amazon S3: planned storage layer for synthetic evidence snapshots and demo artifacts.

All competition-facing demonstrations should use synthetic AWS resource evidence unless the user explicitly authorizes a different safe data source.

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
- Creating production AWS resources during the documentation phase.
- Creating CockroachDB resources during the documentation phase.
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
- Memory layer: CockroachDB is planned to store resource history, annotations, evidence events, and durable context.
- Retrieval layer: CockroachDB Distributed Vector Indexing is planned to retrieve similar records and historical explanations.
- Reasoning layer: Amazon Bedrock is planned to summarize evidence and generate human-reviewable verdict explanations.

This architecture is not yet implemented.

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

The demo presents a quiet RDS instance with low recent utilization. A traditional idle-resource report might flag it for cleanup. OrphanProof retrieves synthetic memory showing that the instance is a disaster-recovery standby for a critical service and has a recent review note confirming its purpose.

Planned verdict: KEEP

Reason: The resource appears idle, but historical context proves it has a valid resilience role.

### 2. Unattached Abandoned EBS Volume -> QUARANTINE

The demo presents an unattached EBS volume with no recent attachment activity. OrphanProof retrieves synthetic memory showing that it was created during a migration, but the latest review note is stale and there is not enough evidence to prove it is still needed.

Planned verdict: QUARANTINE

Reason: The resource may be abandoned, but the evidence is incomplete. A human should review before removal.

## Definition of Success for the First Phase

The first phase is successful when the repository has a truthful documentation foundation that:

- Describes the product problem and planned solution clearly.
- Defines MVP resource types and verdicts.
- Documents safety principles and non-goals.
- Maps planned sponsor integrations to product responsibilities.
- Establishes agent working rules.
- Avoids secrets, fake implementation claims, fake deployment links, fake test results, and fake setup instructions.

## Current Status

PLANNED / NOT YET IMPLEMENTED

The project currently contains documentation foundations only. Application code, AWS integrations, CockroachDB integrations, Bedrock reasoning, vector indexing, tests, security checks, and deployment are not yet implemented.
