# Synthetic Persistent-Memory Dataset

This document describes the Phase P2 synthetic persistent-memory dataset for Cloud Nexus OrphanProof.

## Purpose

The dataset gives the hackathon demo realistic operational memory without requiring a real AWS account, real infrastructure, or customer data. It is designed to show why idle-looking resources need context before a human approves remediation.

The dataset uses synthetic relative timelines only. It does not document live database endpoints or environment-specific identifiers.

## Dataset Shape

The seed creates exactly 18 synthetic resources:

- 6 EBS volumes
- 6 Elastic IP addresses
- 6 RDS instances

All resource keys begin with `demo-`, all resources have `is_synthetic = true`, and all identities use the reserved `example.invalid` email domain.

## Primary Demo Stories

### Demo Story A: RDS Disaster-Recovery Standby

`demo-rds-dr-standby-001` is an RDS instance that appears idle because it has no recent application connections and very low utilization. Persistent memory shows that it was created through Terraform as a disaster-recovery standby. A platform engineer documented the DR purpose, a dependency event says it supports regional recovery, and an active exception protects the standby during the synthetic review window.

The historical human-reviewed seed decision is `KEEP`. The risk of removal is loss of regional recovery capability.

### Demo Story B: Abandoned EBS Volume

`demo-ebs-abandoned-001` is an unattached EBS volume that has been idle for 120 days. It was created manually during a migration, its original owner is a fictional departed employee, it has no Terraform ownership, no active exception, and no known dependent workload.

The safest current verdict is `QUARANTINE`. The recommended action is to snapshot the volume, quarantine it for seven days, request human approval, and remove it only if no dependency appears. The dataset does not give it an approved removal decision.

## Other Scenario Categories

The seed also includes balanced synthetic scenarios:

- Elastic IP retained because a partner allowlist depends on it
- Elastic IP abandoned after a test environment was terminated
- RDS instance used only for month-end reporting
- RDS development database unused for 90 days
- EBS rollback volume whose documentation is stale
- EBS temporary scratch volume safe to remove
- Elastic IP reserved for disaster-recovery failover
- RDS compliance database used quarterly

## Tables Receiving Data

The seed writes deterministic rows to:

- `orphanproof.resources`
- `orphanproof.memory_events`
- `orphanproof.exceptions`
- `orphanproof.decisions`
- `orphanproof.human_approvals`

`orphanproof.decision_embeddings` remains empty until the later vector-memory phase. This coding step does not create decision embeddings.

## Safety Rules

The dataset is synthetic by default. It does not require a real AWS account, real AWS identifiers, AWS credentials, customer data, private hostnames, account IDs, ARNs, certificates, or connection strings.

Cloud Nexus OrphanProof remains read-only by default. The dataset contains recommendations and historical approval examples only; it does not perform remediation or create cloud resources. Any future remediation workflow must show evidence, risk context, and a recommended action for human approval before action is taken.

## Fictional Identity Policy

All seeded email identities use the `example.invalid` domain, including fictional owners such as `platform-team@example.invalid`, `security-team@example.invalid`, `finops-team@example.invalid`, and `former-engineer@example.invalid`.

## Loading Behavior

The SQL seed is idempotent and transaction-safe. It uses deterministic UUIDs and `UPSERT` statements so it can be run more than once without creating duplicate dataset rows. The seed only targets rows whose deterministic identifiers belong to this synthetic dataset.

The dataset was loaded into the development CockroachDB cluster and loaded twice to confirm idempotence. Both live verification runs returned:

```text
synthetic_seed_contract_status | PASS
```

Verified live counts:

- 18 synthetic resources
- 6 EBS volumes
- 6 Elastic IP addresses
- 6 RDS instances
- 41 memory events
- 3 exceptions
- 8 historical seed decisions
- 2 human approvals
- 0 decision embeddings

The commands used by the loader are:

```bash
python3 scripts/load_synthetic_seed.py load
python3 scripts/load_synthetic_seed.py verify
```

This confirms the development synthetic dataset only. It does not claim production readiness.
