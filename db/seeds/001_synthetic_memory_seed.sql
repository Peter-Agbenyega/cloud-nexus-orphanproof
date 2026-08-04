BEGIN;

-- Synthetic reference date: 2026-08-01.

UPSERT INTO orphanproof.resources (
    id,
    resource_key,
    resource_type,
    region,
    created_by,
    created_via,
    first_seen,
    last_activity,
    monthly_cost_estimate,
    lifecycle_state,
    current_evidence,
    is_synthetic,
    created_at,
    updated_at
) VALUES
    ('10000000-0000-4000-8000-000000000001', 'demo-ebs-abandoned-001', 'EBS_VOLUME', 'us-east-1', 'former-engineer@example.invalid', 'MANUAL', '2026-03-15T10:00:00Z', '2026-04-03T12:00:00Z', 38.40, 'UNATTACHED', '{"attached": false, "unattached_days": 120, "terraform_managed": false, "known_dependency": false, "recommended_current_verdict": "QUARANTINE", "recommended_action": "snapshot, quarantine for seven days, request human approval, then remove if no dependency appears"}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000002', 'demo-ebs-rollback-stale-001', 'EBS_VOLUME', 'us-west-2', 'platform-team@example.invalid', 'TERRAFORM', '2026-01-20T09:00:00Z', '2026-05-02T18:00:00Z', 64.00, 'UNATTACHED', '{"attached": false, "documentation_age_days": 94, "purpose": "migration rollback copy", "stale_documentation": true}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000003', 'demo-ebs-scratch-temp-001', 'EBS_VOLUME', 'eu-west-1', 'platform-team@example.invalid', 'MANUAL', '2026-06-01T11:00:00Z', '2026-06-05T11:00:00Z', 12.80, 'UNATTACHED', '{"attached": false, "purpose": "temporary load-test scratch", "cleanup_ticket": "synthetic-ticket-ebs-003", "known_dependency": false}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000004', 'demo-ebs-backup-retained-001', 'EBS_VOLUME', 'us-east-1', 'security-team@example.invalid', 'SERVICE', '2026-02-11T08:30:00Z', '2026-07-15T08:30:00Z', 44.20, 'RETAINED', '{"attached": false, "purpose": "forensic backup hold", "retention_review": "active synthetic security review"}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000005', 'demo-ebs-build-cache-001', 'EBS_VOLUME', 'us-west-2', 'platform-team@example.invalid', 'CLOUDFORMATION', '2026-05-10T16:00:00Z', '2026-05-21T16:00:00Z', 18.60, 'UNATTACHED', '{"attached": false, "purpose": "obsolete build cache", "replacement": "ephemeral runner cache", "known_dependency": false}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000006', 'demo-ebs-finops-review-001', 'EBS_VOLUME', 'eu-west-1', 'finops-team@example.invalid', 'UNKNOWN', '2026-04-07T14:15:00Z', '2026-06-18T14:15:00Z', 28.75, 'REVIEW_REQUIRED', '{"attached": false, "owner_uncertain": true, "budget_tag": "synthetic-finops", "recommended_current_verdict": "QUARANTINE"}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000007', 'demo-eip-partner-allowlist-001', 'ELASTIC_IP', 'us-east-1', 'security-team@example.invalid', 'TERRAFORM', '2026-02-01T13:00:00Z', '2026-07-29T13:00:00Z', 3.65, 'ALLOCATED', '{"associated": false, "partner_allowlist": true, "allowlist_owner": "security-team@example.invalid", "idle_signal": true}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000008', 'demo-eip-test-terminated-001', 'ELASTIC_IP', 'us-west-2', 'platform-team@example.invalid', 'MANUAL', '2026-06-10T15:00:00Z', '2026-06-12T15:00:00Z', 3.65, 'UNASSOCIATED', '{"associated": false, "test_environment_terminated": true, "known_dependency": false}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000009', 'demo-eip-dr-failover-001', 'ELASTIC_IP', 'eu-west-1', 'platform-team@example.invalid', 'TERRAFORM', '2026-03-01T10:30:00Z', '2026-07-20T10:30:00Z', 3.65, 'RESERVED', '{"associated": false, "purpose": "disaster recovery failover", "runbook": "synthetic-dr-network-runbook"}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000010', 'demo-eip-old-nat-001', 'ELASTIC_IP', 'us-east-1', 'platform-team@example.invalid', 'CLOUDFORMATION', '2026-01-08T12:00:00Z', '2026-05-01T12:00:00Z', 3.65, 'UNASSOCIATED', '{"associated": false, "former_nat_gateway": true, "replacement_confirmed": true}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000011', 'demo-eip-security-scan-001', 'ELASTIC_IP', 'us-west-2', 'security-team@example.invalid', 'SERVICE', '2026-04-18T17:00:00Z', '2026-07-18T17:00:00Z', 3.65, 'ALLOCATED', '{"associated": false, "scanner_allowlist": true, "review_window_days": 30}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000012', 'demo-eip-unknown-owner-001', 'ELASTIC_IP', 'eu-west-1', 'finops-team@example.invalid', 'UNKNOWN', '2026-05-05T09:45:00Z', '2026-06-01T09:45:00Z', 3.65, 'REVIEW_REQUIRED', '{"associated": false, "owner_uncertain": true, "dependency_unknown": true}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000013', 'demo-rds-dr-standby-001', 'RDS_INSTANCE', 'us-east-1', 'platform-team@example.invalid', 'TERRAFORM', '2025-11-01T07:00:00Z', '2026-07-02T07:00:00Z', 412.30, 'STANDBY', '{"application_connections_last_30_days": 0, "cpu_average_percent": 1.4, "appears_idle": true, "purpose": "regional disaster-recovery standby", "terraform_managed": true, "risk_of_removal": "loss of regional recovery capability"}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000014', 'demo-rds-month-end-reporting-001', 'RDS_INSTANCE', 'us-west-2', 'finops-team@example.invalid', 'TERRAFORM', '2026-01-05T06:00:00Z', '2026-07-31T06:00:00Z', 186.90, 'SCHEDULED_USE', '{"usage_pattern": "month-end reporting", "daily_idle_signal": true, "last_report_run": "2026-07-31"}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000015', 'demo-rds-dev-unused-001', 'RDS_INSTANCE', 'eu-west-1', 'platform-team@example.invalid', 'MANUAL', '2026-02-15T10:00:00Z', '2026-05-03T10:00:00Z', 97.40, 'IDLE', '{"application_connections_last_90_days": 0, "development_database": true, "known_dependency": false}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000016', 'demo-rds-compliance-quarterly-001', 'RDS_INSTANCE', 'us-east-1', 'security-team@example.invalid', 'CLOUDFORMATION', '2025-12-12T05:00:00Z', '2026-06-30T05:00:00Z', 244.10, 'SCHEDULED_USE', '{"usage_pattern": "quarterly compliance evidence", "last_quarterly_run": "2026-06-30", "idle_between_runs": true}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000017', 'demo-rds-legacy-staging-001', 'RDS_INSTANCE', 'us-west-2', 'former-engineer@example.invalid', 'UNKNOWN', '2026-03-22T04:00:00Z', '2026-06-05T04:00:00Z', 128.50, 'REVIEW_REQUIRED', '{"legacy_staging": true, "owner_uncertain": true, "recent_activity": "none since synthetic cutover"}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('10000000-0000-4000-8000-000000000018', 'demo-rds-migration-leftover-001', 'RDS_INSTANCE', 'eu-west-1', 'platform-team@example.invalid', 'SERVICE', '2026-04-01T04:30:00Z', '2026-04-29T04:30:00Z', 151.75, 'IDLE', '{"migration_complete": true, "replacement_database": "demo-rds-month-end-reporting-001", "known_dependency": false}'::JSONB, true, '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z');

UPSERT INTO orphanproof.memory_events (
    id,
    resource_id,
    event_type,
    summary,
    evidence,
    source,
    occurred_at,
    recorded_at
) VALUES
    ('20000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', 'CREATION', 'Synthetic EBS volume created manually during a migration.', '{"migration": "demo-core-data-move", "synthetic": true}'::JSONB, 'SEED', '2026-03-15T10:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', 'OWNERSHIP', 'Original owner former-engineer@example.invalid is a departed fictional owner; no active owner confirmed.', '{"owner_status": "departed fictional owner", "owner_email": "former-engineer@example.invalid"}'::JSONB, 'SEED', '2026-06-01T12:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000001', 'NOTE', 'No Terraform ownership and no dependent workload is known; quarantine is safer than immediate removal.', '{"terraform_managed": false, "known_dependency": false}'::JSONB, 'SEED', '2026-07-30T12:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000002', 'CREATION', 'Rollback EBS volume created by Terraform for a migration safety window.', '{"purpose": "rollback"}'::JSONB, 'SEED', '2026-01-20T09:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000002', 'EXCEPTION', 'Prior rollback exception expired after migration stabilization.', '{"status": "EXPIRED"}'::JSONB, 'SEED', '2026-06-01T09:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000006', '10000000-0000-4000-8000-000000000003', 'CREATION', 'Temporary EBS scratch volume created for synthetic load testing.', '{"purpose": "scratch"}'::JSONB, 'SEED', '2026-06-01T11:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000007', '10000000-0000-4000-8000-000000000003', 'ACTIVITY', 'Synthetic scratch workload ended and no later attachment activity was observed.', '{"last_attachment": "2026-06-05"}'::JSONB, 'SEED', '2026-06-05T11:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000008', '10000000-0000-4000-8000-000000000004', 'CREATION', 'Forensic backup EBS volume retained by a synthetic security workflow.', '{"retention": "security hold"}'::JSONB, 'SEED', '2026-02-11T08:30:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000009', '10000000-0000-4000-8000-000000000004', 'NOTE', 'Security team documented that this backup should remain available for review.', '{"owner_email": "security-team@example.invalid"}'::JSONB, 'SEED', '2026-07-15T08:30:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000010', '10000000-0000-4000-8000-000000000005', 'CREATION', 'Build cache volume created from a CloudFormation test stack.', '{"stack": "demo-build-cache"}'::JSONB, 'SEED', '2026-05-10T16:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000011', '10000000-0000-4000-8000-000000000005', 'REJECTION', 'Build team rejected ongoing need after moving cache to ephemeral workers.', '{"replacement": "ephemeral workers"}'::JSONB, 'SEED', '2026-07-10T16:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000012', '10000000-0000-4000-8000-000000000006', 'CREATION', 'FinOps review volume discovered without a reliable creation path.', '{"owner_uncertain": true}'::JSONB, 'SEED', '2026-04-07T14:15:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000013', '10000000-0000-4000-8000-000000000006', 'OWNERSHIP', 'FinOps team owns the review workflow but not the workload dependency.', '{"owner_email": "finops-team@example.invalid"}'::JSONB, 'SEED', '2026-07-01T14:15:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000014', '10000000-0000-4000-8000-000000000007', 'CREATION', 'Elastic IP reserved in Terraform for a synthetic partner allowlist.', '{"partner_allowlist": true}'::JSONB, 'SEED', '2026-02-01T13:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000015', '10000000-0000-4000-8000-000000000007', 'DEPENDENCY', 'Partner allowlist depends on this stable address even when no instance is attached.', '{"dependency": "partner allowlist"}'::JSONB, 'SEED', '2026-07-29T13:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000016', '10000000-0000-4000-8000-000000000008', 'CREATION', 'Elastic IP allocated manually for a short-lived synthetic test environment.', '{"environment": "terminated test"}'::JSONB, 'SEED', '2026-06-10T15:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000017', '10000000-0000-4000-8000-000000000008', 'ACTIVITY', 'Test environment was terminated and no dependent service remains.', '{"test_environment_terminated": true}'::JSONB, 'SEED', '2026-06-12T15:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000018', '10000000-0000-4000-8000-000000000009', 'CREATION', 'Elastic IP reserved by Terraform for disaster-recovery network failover.', '{"purpose": "dr failover"}'::JSONB, 'SEED', '2026-03-01T10:30:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000019', '10000000-0000-4000-8000-000000000009', 'DEPENDENCY', 'Failover runbook expects this reserved address during regional recovery.', '{"runbook": "synthetic-dr-network-runbook"}'::JSONB, 'SEED', '2026-07-20T10:30:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000020', '10000000-0000-4000-8000-000000000010', 'CREATION', 'Elastic IP created with an old synthetic NAT gateway stack.', '{"former_nat_gateway": true}'::JSONB, 'SEED', '2026-01-08T12:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000021', '10000000-0000-4000-8000-000000000010', 'REJECTION', 'Platform team confirmed the NAT replacement no longer requires the address.', '{"replacement_confirmed": true}'::JSONB, 'SEED', '2026-07-02T12:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000022', '10000000-0000-4000-8000-000000000011', 'CREATION', 'Elastic IP allocated by a service workflow for synthetic security scanning.', '{"scanner_allowlist": true}'::JSONB, 'SEED', '2026-04-18T17:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000023', '10000000-0000-4000-8000-000000000011', 'NOTE', 'Security scanner allowlist should be reviewed before any release action.', '{"review_required": true}'::JSONB, 'SEED', '2026-07-18T17:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000024', '10000000-0000-4000-8000-000000000012', 'CREATION', 'Elastic IP discovered with unknown creation details.', '{"owner_uncertain": true}'::JSONB, 'SEED', '2026-05-05T09:45:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000025', '10000000-0000-4000-8000-000000000012', 'OWNERSHIP', 'FinOps review could not identify a workload owner.', '{"owner_email": "finops-team@example.invalid", "owner_confirmed": false}'::JSONB, 'SEED', '2026-07-25T09:45:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000026', '10000000-0000-4000-8000-000000000013', 'CREATION', 'RDS disaster-recovery standby was created through Terraform.', '{"created_via": "TERRAFORM", "terraform_managed": true}'::JSONB, 'SEED', '2025-11-01T07:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000027', '10000000-0000-4000-8000-000000000013', 'ACTIVITY', 'No application connections were observed for 30 days and utilization appears idle.', '{"application_connections_last_30_days": 0, "cpu_average_percent": 1.4}'::JSONB, 'SEED', '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000028', '10000000-0000-4000-8000-000000000013', 'NOTE', 'Platform engineer documented the disaster-recovery purpose and removal risk.', '{"author": "platform-team@example.invalid", "risk_of_removal": "loss of regional recovery capability"}'::JSONB, 'SEED', '2026-07-25T07:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000029', '10000000-0000-4000-8000-000000000013', 'DEPENDENCY', 'Resource supports regional recovery for the synthetic customer API.', '{"dependency": "regional recovery capability"}'::JSONB, 'SEED', '2026-07-25T07:05:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000030', '10000000-0000-4000-8000-000000000013', 'EXCEPTION', 'Active exception protects the DR standby until 2026-09-30.', '{"status": "ACTIVE", "expires_at": "2026-09-30"}'::JSONB, 'SEED', '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000031', '10000000-0000-4000-8000-000000000014', 'CREATION', 'RDS reporting instance created for month-end finance reports.', '{"usage_pattern": "month-end"}'::JSONB, 'SEED', '2026-01-05T06:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000032', '10000000-0000-4000-8000-000000000014', 'ACTIVITY', 'Month-end synthetic reporting activity completed on 2026-07-31.', '{"last_report_run": "2026-07-31"}'::JSONB, 'SEED', '2026-07-31T06:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000033', '10000000-0000-4000-8000-000000000015', 'CREATION', 'Development RDS database created manually for a synthetic feature branch.', '{"development_database": true}'::JSONB, 'SEED', '2026-02-15T10:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000034', '10000000-0000-4000-8000-000000000015', 'ACTIVITY', 'No development database connections were observed for 90 days.', '{"application_connections_last_90_days": 0}'::JSONB, 'SEED', '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000035', '10000000-0000-4000-8000-000000000016', 'CREATION', 'Compliance RDS database created for quarterly evidence retention.', '{"usage_pattern": "quarterly compliance"}'::JSONB, 'SEED', '2025-12-12T05:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000036', '10000000-0000-4000-8000-000000000016', 'ACTIVITY', 'Quarterly compliance evidence job last ran on 2026-06-30.', '{"last_quarterly_run": "2026-06-30"}'::JSONB, 'SEED', '2026-06-30T05:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000037', '10000000-0000-4000-8000-000000000016', 'EXCEPTION', 'Active exception protects quarterly compliance evidence until review.', '{"status": "ACTIVE"}'::JSONB, 'SEED', '2026-07-01T05:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000038', '10000000-0000-4000-8000-000000000017', 'CREATION', 'Legacy staging RDS instance was found with unknown automation ownership.', '{"legacy_staging": true}'::JSONB, 'SEED', '2026-03-22T04:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000039', '10000000-0000-4000-8000-000000000017', 'OWNERSHIP', 'Former fictional engineer was listed as the owner; current owner is uncertain.', '{"owner_email": "former-engineer@example.invalid", "owner_confirmed": false}'::JSONB, 'SEED', '2026-07-21T04:00:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000040', '10000000-0000-4000-8000-000000000018', 'CREATION', 'Migration leftover RDS instance was created by a service workflow.', '{"migration": "demo-reporting-cutover"}'::JSONB, 'SEED', '2026-04-01T04:30:00Z', '2026-08-01T00:00:00Z'),
    ('20000000-0000-4000-8000-000000000041', '10000000-0000-4000-8000-000000000018', 'REJECTION', 'Migration team rejected ongoing need after replacement validation.', '{"replacement_database": "demo-rds-month-end-reporting-001"}'::JSONB, 'SEED', '2026-07-22T04:30:00Z', '2026-08-01T00:00:00Z');

UPSERT INTO orphanproof.exceptions (
    id,
    resource_id,
    reason,
    approved_by,
    approved_at,
    expires_at,
    status,
    created_at
) VALUES
    ('30000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000013', 'Synthetic DR standby exception; removal would risk loss of regional recovery capability.', 'platform-team@example.invalid', '2026-08-01T00:00:00Z', '2026-09-30T00:00:00Z', 'ACTIVE', '2026-08-01T00:00:00Z'),
    ('30000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000016', 'Synthetic quarterly compliance retention exception.', 'security-team@example.invalid', '2026-07-01T00:00:00Z', '2026-10-01T00:00:00Z', 'ACTIVE', '2026-07-01T00:00:00Z'),
    ('30000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000002', 'Synthetic rollback safety window expired after migration stabilization.', 'platform-team@example.invalid', '2026-04-01T00:00:00Z', '2026-06-01T00:00:00Z', 'EXPIRED', '2026-04-01T00:00:00Z');

UPSERT INTO orphanproof.decisions (
    id,
    resource_id,
    verdict,
    confidence_score,
    blast_radius,
    evidence_summary,
    recommended_action,
    rollback_plan,
    human_status,
    decision_source,
    decided_at
) VALUES
    ('40000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000013', 'KEEP', 94.00, 'High: removal could reduce synthetic regional recovery capability.', 'Idle utilization is overridden by Terraform ownership, DR documentation, dependency memory, and an active exception.', 'Keep the standby and renew DR exception during the next resilience review.', 'Restore from latest synthetic snapshot and reapply Terraform if accidentally removed.', 'APPROVED', 'SEED', '2026-08-01T00:00:00Z'),
    ('40000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', 'QUARANTINE', 82.00, 'Medium: removal could affect unknown migration rollback data.', 'Volume is unattached for 120 days, manual, owned by a departed fictional owner, and has no known dependency.', 'Snapshot, quarantine for seven days, request human approval, then remove if no dependency appears.', 'Reattach the snapshot to a synthetic recovery host if a dependency appears.', 'PENDING', 'SEED', '2026-08-01T00:00:00Z'),
    ('40000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000008', 'REMOVE', 91.00, 'Low: terminated test environment has no known dependency.', 'Elastic IP remained unassociated after test termination.', 'Request human approval to release the synthetic address allocation.', 'Allocate a new synthetic address if the test environment is recreated.', 'APPROVED', 'SEED', '2026-07-20T00:00:00Z'),
    ('40000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000007', 'KEEP', 88.00, 'Medium: partner connectivity may fail if the allowlisted address changes.', 'Partner allowlist dependency exists despite idle allocation signals.', 'Keep until partner allowlist migration is explicitly completed.', 'Restore connectivity by re-adding the stable address to the synthetic allowlist.', 'PENDING', 'SEED', '2026-07-29T00:00:00Z'),
    ('40000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000015', 'REMOVE', 86.00, 'Low: development database has no connections or dependency for 90 days.', 'Development RDS database is unused and no active owner or dependency is known.', 'Request human approval to snapshot and remove the idle development database.', 'Restore from synthetic final snapshot if a developer dependency is found.', 'REJECTED', 'SEED', '2026-07-25T00:00:00Z'),
    ('40000000-0000-4000-8000-000000000006', '10000000-0000-4000-8000-000000000006', 'QUARANTINE', 73.00, 'Medium: owner and dependency evidence are incomplete.', 'FinOps review volume has uncertain ownership and no confirmed workload dependency.', 'Quarantine while requesting owner confirmation from finops-team@example.invalid.', 'Reattach volume to the prior synthetic workload if an owner confirms dependency.', 'PENDING', 'SEED', '2026-07-26T00:00:00Z'),
    ('40000000-0000-4000-8000-000000000007', '10000000-0000-4000-8000-000000000018', 'REMOVE', 89.00, 'Low: migration replacement is validated and no dependency remains.', 'Migration leftover RDS instance is idle after replacement validation.', 'Request human approval to snapshot and remove after final owner notice.', 'Restore from synthetic snapshot and redirect clients if unexpected usage appears.', 'PENDING', 'SEED', '2026-07-27T00:00:00Z'),
    ('40000000-0000-4000-8000-000000000008', '10000000-0000-4000-8000-000000000017', 'QUARANTINE', 69.00, 'Medium: legacy staging ownership remains uncertain.', 'Legacy staging RDS has stale ownership evidence from a departed fictional owner.', 'Quarantine and require platform-team@example.invalid to confirm ownership before removal.', 'Resume the instance if a synthetic staging dependency is identified.', 'PENDING', 'SEED', '2026-07-28T00:00:00Z');

UPSERT INTO orphanproof.human_approvals (
    id,
    decision_id,
    status,
    reviewer,
    rationale,
    reviewed_at
) VALUES
    ('50000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', 'APPROVED', 'platform-team@example.invalid', 'Approved KEEP because synthetic DR evidence and active exception support retention.', '2026-08-01T01:00:00Z'),
    ('50000000-0000-4000-8000-000000000002', '40000000-0000-4000-8000-000000000005', 'REJECTED', 'security-team@example.invalid', 'Rejected immediate removal pending one more synthetic development-owner notice.', '2026-07-26T01:00:00Z');

COMMIT;
