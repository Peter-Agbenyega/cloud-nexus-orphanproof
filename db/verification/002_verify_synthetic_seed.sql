SELECT COUNT(*) = 18 AS synthetic_resource_count_valid
FROM orphanproof.resources
WHERE resource_key LIKE 'demo-%'
\gset
\if :synthetic_resource_count_valid
\echo ok: exactly 18 synthetic dataset resources exist
\else
\echo ERROR: expected exactly 18 synthetic dataset resources
SELECT 1 / 0;
\endif

SELECT COUNT(*) = 6 AS ebs_resource_count_valid
FROM orphanproof.resources
WHERE resource_key LIKE 'demo-%'
  AND resource_type = 'EBS_VOLUME'
\gset
\if :ebs_resource_count_valid
\echo ok: exactly 6 EBS_VOLUME records exist
\else
\echo ERROR: expected exactly 6 EBS_VOLUME records
SELECT 1 / 0;
\endif

SELECT COUNT(*) = 6 AS eip_resource_count_valid
FROM orphanproof.resources
WHERE resource_key LIKE 'demo-%'
  AND resource_type = 'ELASTIC_IP'
\gset
\if :eip_resource_count_valid
\echo ok: exactly 6 ELASTIC_IP records exist
\else
\echo ERROR: expected exactly 6 ELASTIC_IP records
SELECT 1 / 0;
\endif

SELECT COUNT(*) = 6 AS rds_resource_count_valid
FROM orphanproof.resources
WHERE resource_key LIKE 'demo-%'
  AND resource_type = 'RDS_INSTANCE'
\gset
\if :rds_resource_count_valid
\echo ok: exactly 6 RDS_INSTANCE records exist
\else
\echo ERROR: expected exactly 6 RDS_INSTANCE records
SELECT 1 / 0;
\endif

SELECT COUNT(*) = 18 AS all_resources_synthetic_valid
FROM orphanproof.resources
WHERE resource_key LIKE 'demo-%'
  AND is_synthetic = true
\gset
\if :all_resources_synthetic_valid
\echo ok: every dataset resource is synthetic
\else
\echo ERROR: every dataset resource must have is_synthetic true
SELECT 1 / 0;
\endif

SELECT COUNT(*) = 18 AS demo_key_prefix_valid
FROM orphanproof.resources
WHERE resource_key LIKE 'demo-%'
\gset
\if :demo_key_prefix_valid
\echo ok: every dataset resource key begins with demo-
\else
\echo ERROR: every dataset resource key must begin with demo-
SELECT 1 / 0;
\endif

SELECT COUNT(*) >= 40 AS memory_event_count_valid
FROM orphanproof.memory_events AS me
JOIN orphanproof.resources AS r ON r.id = me.resource_id
WHERE r.resource_key LIKE 'demo-%'
\gset
\if :memory_event_count_valid
\echo ok: at least 40 dataset memory events exist
\else
\echo ERROR: expected at least 40 dataset memory events
SELECT 1 / 0;
\endif

SELECT COUNT(*) = 18 AS every_resource_has_creation_valid
FROM orphanproof.resources AS r
WHERE r.resource_key LIKE 'demo-%'
  AND EXISTS (
      SELECT 1
      FROM orphanproof.memory_events AS me
      WHERE me.resource_id = r.id
        AND me.event_type = 'CREATION'
  )
\gset
\if :every_resource_has_creation_valid
\echo ok: every dataset resource has a CREATION event
\else
\echo ERROR: every dataset resource must have a CREATION event
SELECT 1 / 0;
\endif

SELECT COUNT(*) = 18 AS every_resource_has_two_events_valid
FROM orphanproof.resources AS r
WHERE r.resource_key LIKE 'demo-%'
  AND (
      SELECT COUNT(*)
      FROM orphanproof.memory_events AS me
      WHERE me.resource_id = r.id
  ) >= 2
\gset
\if :every_resource_has_two_events_valid
\echo ok: every dataset resource has at least two memory events
\else
\echo ERROR: every dataset resource must have at least two memory events
SELECT 1 / 0;
\endif

SELECT COUNT(*) = 3 AS exception_count_valid
FROM orphanproof.exceptions AS e
JOIN orphanproof.resources AS r ON r.id = e.resource_id
WHERE r.resource_key LIKE 'demo-%'
\gset
\if :exception_count_valid
\echo ok: exactly 3 dataset exceptions exist
\else
\echo ERROR: expected exactly 3 dataset exceptions
SELECT 1 / 0;
\endif

SELECT COUNT(*) >= 2 AS active_exception_count_valid
FROM orphanproof.exceptions AS e
JOIN orphanproof.resources AS r ON r.id = e.resource_id
WHERE r.resource_key LIKE 'demo-%'
  AND e.status = 'ACTIVE'
\gset
\if :active_exception_count_valid
\echo ok: at least 2 ACTIVE dataset exceptions exist
\else
\echo ERROR: expected at least 2 ACTIVE dataset exceptions
SELECT 1 / 0;
\endif

SELECT COUNT(*) >= 1 AS expired_exception_count_valid
FROM orphanproof.exceptions AS e
JOIN orphanproof.resources AS r ON r.id = e.resource_id
WHERE r.resource_key LIKE 'demo-%'
  AND e.status = 'EXPIRED'
\gset
\if :expired_exception_count_valid
\echo ok: at least 1 EXPIRED dataset exception exists
\else
\echo ERROR: expected at least 1 EXPIRED dataset exception
SELECT 1 / 0;
\endif

SELECT COUNT(*) >= 6 AS seed_decision_count_valid
FROM orphanproof.decisions AS d
JOIN orphanproof.resources AS r ON r.id = d.resource_id
WHERE r.resource_key LIKE 'demo-%'
  AND d.decision_source = 'SEED'
\gset
\if :seed_decision_count_valid
\echo ok: at least 6 SEED decisions exist
\else
\echo ERROR: expected at least 6 SEED decisions
SELECT 1 / 0;
\endif

SELECT COUNT(*) >= 2 AS keep_seed_decision_count_valid
FROM orphanproof.decisions AS d
JOIN orphanproof.resources AS r ON r.id = d.resource_id
WHERE r.resource_key LIKE 'demo-%'
  AND d.decision_source = 'SEED'
  AND d.verdict = 'KEEP'
\gset
\if :keep_seed_decision_count_valid
\echo ok: at least 2 KEEP SEED decisions exist
\else
\echo ERROR: expected at least 2 KEEP SEED decisions
SELECT 1 / 0;
\endif

SELECT COUNT(*) >= 2 AS quarantine_seed_decision_count_valid
FROM orphanproof.decisions AS d
JOIN orphanproof.resources AS r ON r.id = d.resource_id
WHERE r.resource_key LIKE 'demo-%'
  AND d.decision_source = 'SEED'
  AND d.verdict = 'QUARANTINE'
\gset
\if :quarantine_seed_decision_count_valid
\echo ok: at least 2 QUARANTINE SEED decisions exist
\else
\echo ERROR: expected at least 2 QUARANTINE SEED decisions
SELECT 1 / 0;
\endif

SELECT COUNT(*) >= 2 AS remove_seed_decision_count_valid
FROM orphanproof.decisions AS d
JOIN orphanproof.resources AS r ON r.id = d.resource_id
WHERE r.resource_key LIKE 'demo-%'
  AND d.decision_source = 'SEED'
  AND d.verdict = 'REMOVE'
\gset
\if :remove_seed_decision_count_valid
\echo ok: at least 2 REMOVE SEED decisions exist
\else
\echo ERROR: expected at least 2 REMOVE SEED decisions
SELECT 1 / 0;
\endif

SELECT COUNT(*) >= 2 AS human_approval_count_valid
FROM orphanproof.human_approvals AS ha
JOIN orphanproof.decisions AS d ON d.id = ha.decision_id
JOIN orphanproof.resources AS r ON r.id = d.resource_id
WHERE r.resource_key LIKE 'demo-%'
\gset
\if :human_approval_count_valid
\echo ok: at least 2 human approvals exist
\else
\echo ERROR: expected at least 2 human approvals
SELECT 1 / 0;
\endif

SELECT COUNT(*) = 0 AS no_decision_embeddings_valid
FROM orphanproof.decision_embeddings AS de
JOIN orphanproof.decisions AS d ON d.id = de.decision_id
JOIN orphanproof.resources AS r ON r.id = d.resource_id
WHERE r.resource_key LIKE 'demo-%'
  AND d.decision_source = 'SEED'
\gset
\if :no_decision_embeddings_valid
\echo ok: no decision embeddings exist for seeded decisions
\else
\echo ERROR: seeded decisions must not have decision embeddings
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM orphanproof.resources
    WHERE resource_key = 'demo-rds-dr-standby-001'
) AS rds_demo_exists_valid
\gset
\if :rds_demo_exists_valid
\echo ok: demo-rds-dr-standby-001 exists
\else
\echo ERROR: demo-rds-dr-standby-001 is missing
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM orphanproof.resources AS r
    WHERE r.resource_key = 'demo-rds-dr-standby-001'
      AND r.created_via = 'TERRAFORM'
      AND EXISTS (
          SELECT 1
          FROM orphanproof.exceptions AS e
          WHERE e.resource_id = r.id
            AND e.status = 'ACTIVE'
      )
      AND EXISTS (
          SELECT 1
          FROM orphanproof.memory_events AS me
          WHERE me.resource_id = r.id
            AND me.event_type = 'DEPENDENCY'
      )
      AND EXISTS (
          SELECT 1
          FROM orphanproof.decisions AS d
          WHERE d.resource_id = r.id
            AND d.decision_source = 'SEED'
            AND d.verdict = 'KEEP'
      )
) AS rds_demo_story_valid
\gset
\if :rds_demo_story_valid
\echo ok: RDS demo story has active exception, dependency memory, KEEP seed decision, and Terraform evidence
\else
\echo ERROR: RDS demo story is incomplete
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM orphanproof.resources
    WHERE resource_key = 'demo-ebs-abandoned-001'
) AS ebs_demo_exists_valid
\gset
\if :ebs_demo_exists_valid
\echo ok: demo-ebs-abandoned-001 exists
\else
\echo ERROR: demo-ebs-abandoned-001 is missing
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM orphanproof.resources AS r
    WHERE r.resource_key = 'demo-ebs-abandoned-001'
      AND NOT EXISTS (
          SELECT 1
          FROM orphanproof.exceptions AS e
          WHERE e.resource_id = r.id
            AND e.status = 'ACTIVE'
      )
      AND EXISTS (
          SELECT 1
          FROM orphanproof.memory_events AS me
          WHERE me.resource_id = r.id
            AND me.event_type = 'OWNERSHIP'
            AND me.summary LIKE '%departed fictional owner%'
      )
      AND EXISTS (
          SELECT 1
          FROM orphanproof.decisions AS d
          WHERE d.resource_id = r.id
            AND d.decision_source = 'SEED'
            AND d.verdict = 'QUARANTINE'
      )
) AS ebs_demo_story_valid
\gset
\if :ebs_demo_story_valid
\echo ok: EBS demo story has no active exception, departed owner memory, and QUARANTINE seed decision
\else
\echo ERROR: EBS demo story is incomplete
SELECT 1 / 0;
\endif

SELECT NOT EXISTS (
    SELECT 1
    FROM (
        SELECT created_by AS email
        FROM orphanproof.resources
        WHERE resource_key LIKE 'demo-%'
        UNION ALL
        SELECT approved_by AS email
        FROM orphanproof.exceptions AS e
        JOIN orphanproof.resources AS r ON r.id = e.resource_id
        WHERE r.resource_key LIKE 'demo-%'
        UNION ALL
        SELECT reviewer AS email
        FROM orphanproof.human_approvals AS ha
        JOIN orphanproof.decisions AS d ON d.id = ha.decision_id
        JOIN orphanproof.resources AS r ON r.id = d.resource_id
        WHERE r.resource_key LIKE 'demo-%'
    ) AS emails
    WHERE email IS NOT NULL
      AND email NOT LIKE '%@example.invalid'
) AS email_domain_valid
\gset
\if :email_domain_valid
\echo ok: dataset email addresses use example.invalid
\else
\echo ERROR: dataset email addresses must use example.invalid
SELECT 1 / 0;
\endif

SELECT 'synthetic_seed_contract_status' AS synthetic_seed_contract_status, 'PASS' AS result;
