# Cloud Nexus OrphanProof

AWS detects idle resources. OrphanProof remembers why they exist and proves whether deleting them is safe.

Cloud teams often find AWS resources that look unused: unattached EBS volumes, idle Elastic IP addresses, or quiet RDS instances. The hard part is not detection. The hard part is knowing whether the resource is abandoned, reserved for disaster recovery, tied to a migration, or still needed for a business reason that is not visible in AWS metrics.

Cloud Nexus OrphanProof is planned as a read-only FinOps and cloud safety assistant that combines synthetic AWS resource evidence with persistent operational memory. The goal is to explain why a resource exists, compare current signals against historical context, and produce a human-reviewable verdict before any remediation decision is made.

This project is currently in the initial build phase. The repository contains documentation foundations only; application code, cloud integrations, persistence, tests, and deployment are not yet implemented.

## Planned Sponsor Integrations

- CockroachDB Cloud Managed MCP Server
- CockroachDB Distributed Vector Indexing
- Amazon Bedrock
- AWS Lambda and API Gateway
- Amazon S3

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

## Safety Position

OrphanProof is designed around explainability and human approval. It should help a reviewer understand the evidence behind a resource decision, but it must not perform destructive AWS actions automatically.
