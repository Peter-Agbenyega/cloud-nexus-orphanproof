SELECT EXISTS (
    SELECT 1
    FROM information_schema.schemata
    WHERE schema_name = 'orphanproof'
) AS schema_exists
\gset
\if :schema_exists
\echo ok: schema orphanproof exists
\else
\echo ERROR: missing required schema orphanproof
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'orphanproof'
      AND table_name = 'resources'
) AS table_resources_exists
\gset
\if :table_resources_exists
\echo ok: table orphanproof.resources exists
\else
\echo ERROR: missing required table orphanproof.resources
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'orphanproof'
      AND table_name = 'memory_events'
) AS table_memory_events_exists
\gset
\if :table_memory_events_exists
\echo ok: table orphanproof.memory_events exists
\else
\echo ERROR: missing required table orphanproof.memory_events
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'orphanproof'
      AND table_name = 'exceptions'
) AS table_exceptions_exists
\gset
\if :table_exceptions_exists
\echo ok: table orphanproof.exceptions exists
\else
\echo ERROR: missing required table orphanproof.exceptions
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'orphanproof'
      AND table_name = 'decisions'
) AS table_decisions_exists
\gset
\if :table_decisions_exists
\echo ok: table orphanproof.decisions exists
\else
\echo ERROR: missing required table orphanproof.decisions
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'orphanproof'
      AND table_name = 'decision_embeddings'
) AS table_decision_embeddings_exists
\gset
\if :table_decision_embeddings_exists
\echo ok: table orphanproof.decision_embeddings exists
\else
\echo ERROR: missing required table orphanproof.decision_embeddings
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'orphanproof'
      AND table_name = 'human_approvals'
) AS table_human_approvals_exists
\gset
\if :table_human_approvals_exists
\echo ok: table orphanproof.human_approvals exists
\else
\echo ERROR: missing required table orphanproof.human_approvals
SELECT 1 / 0;
\endif

SELECT
    "feature.vector_index.enabled"::BOOL AS enabled
FROM [SHOW CLUSTER SETTING feature.vector_index.enabled]
\gset vector_feature_
\if :vector_feature_enabled
\echo ok: feature.vector_index.enabled is true
\else
\echo ERROR: feature.vector_index.enabled is not true
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM [SHOW COLUMNS FROM orphanproof.decision_embeddings]
    WHERE column_name = 'embedding'
      AND upper(data_type) = 'VECTOR(1024)'
      AND is_nullable = false
) AS vector_column_valid
\gset
\if :vector_column_valid
\echo ok: vector column orphanproof.decision_embeddings.embedding is VECTOR(1024) NOT NULL
\else
\echo ERROR: vector column orphanproof.decision_embeddings.embedding must exist as VECTOR(1024) and must be NOT NULL
SELECT 1 / 0;
\endif

SELECT (
    EXISTS (
        SELECT 1
        FROM [SHOW INDEX FROM orphanproof.decision_embeddings]
        WHERE index_name = 'decision_embeddings_cosine_idx'
          AND column_name = 'embedding'
    )
    AND EXISTS (
        SELECT 1
        FROM [SHOW CREATE TABLE orphanproof.decision_embeddings]
        WHERE strpos(lower(create_statement), 'decision_embeddings_cosine_idx') > 0
          AND strpos(lower(create_statement), 'embedding') > 0
          AND strpos(lower(create_statement), 'vector_cosine_ops') > 0
    )
) AS vector_index_valid
\gset
\if :vector_index_valid
\echo ok: vector index decision_embeddings_cosine_idx is valid
\else
\echo ERROR: required vector index decision_embeddings_cosine_idx is missing or incorrect
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM [SHOW INDEX FROM orphanproof.resources]
    WHERE index_name = 'resources_type_state_idx'
) AS index_resources_type_state_exists
\gset
\if :index_resources_type_state_exists
\echo ok: index resources_type_state_idx exists
\else
\echo ERROR: missing required index orphanproof.resources.resources_type_state_idx
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM [SHOW INDEX FROM orphanproof.memory_events]
    WHERE index_name = 'memory_events_resource_occurred_idx'
) AS index_memory_events_resource_occurred_exists
\gset
\if :index_memory_events_resource_occurred_exists
\echo ok: index memory_events_resource_occurred_idx exists
\else
\echo ERROR: missing required index orphanproof.memory_events.memory_events_resource_occurred_idx
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM [SHOW INDEX FROM orphanproof.exceptions]
    WHERE index_name = 'exceptions_resource_status_idx'
) AS index_exceptions_resource_status_exists
\gset
\if :index_exceptions_resource_status_exists
\echo ok: index exceptions_resource_status_idx exists
\else
\echo ERROR: missing required index orphanproof.exceptions.exceptions_resource_status_idx
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM [SHOW INDEX FROM orphanproof.decisions]
    WHERE index_name = 'decisions_resource_decided_idx'
) AS index_decisions_resource_decided_exists
\gset
\if :index_decisions_resource_decided_exists
\echo ok: index decisions_resource_decided_idx exists
\else
\echo ERROR: missing required index orphanproof.decisions.decisions_resource_decided_idx
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM [SHOW INDEX FROM orphanproof.decisions]
    WHERE index_name = 'decisions_verdict_human_status_idx'
) AS index_decisions_verdict_human_status_exists
\gset
\if :index_decisions_verdict_human_status_exists
\echo ok: index decisions_verdict_human_status_idx exists
\else
\echo ERROR: missing required index orphanproof.decisions.decisions_verdict_human_status_idx
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'resources'
      AND constraint_name = 'resources_resource_type_check'
      AND constraint_type = 'CHECK'
) AS check_resources_resource_type_exists
\gset
\if :check_resources_resource_type_exists
\echo ok: check resources_resource_type_check exists
\else
\echo ERROR: missing required check constraint orphanproof.resources.resources_resource_type_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'resources'
      AND constraint_name = 'resources_created_via_check'
      AND constraint_type = 'CHECK'
) AS check_resources_created_via_exists
\gset
\if :check_resources_created_via_exists
\echo ok: check resources_created_via_check exists
\else
\echo ERROR: missing required check constraint orphanproof.resources.resources_created_via_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'resources'
      AND constraint_name = 'resources_monthly_cost_estimate_check'
      AND constraint_type = 'CHECK'
) AS check_resources_monthly_cost_estimate_exists
\gset
\if :check_resources_monthly_cost_estimate_exists
\echo ok: check resources_monthly_cost_estimate_check exists
\else
\echo ERROR: missing required check constraint orphanproof.resources.resources_monthly_cost_estimate_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'memory_events'
      AND constraint_name = 'memory_events_event_type_check'
      AND constraint_type = 'CHECK'
) AS check_memory_events_event_type_exists
\gset
\if :check_memory_events_event_type_exists
\echo ok: check memory_events_event_type_check exists
\else
\echo ERROR: missing required check constraint orphanproof.memory_events.memory_events_event_type_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'exceptions'
      AND constraint_name = 'exceptions_status_check'
      AND constraint_type = 'CHECK'
) AS check_exceptions_status_exists
\gset
\if :check_exceptions_status_exists
\echo ok: check exceptions_status_check exists
\else
\echo ERROR: missing required check constraint orphanproof.exceptions.exceptions_status_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'decisions'
      AND constraint_name = 'decisions_verdict_check'
      AND constraint_type = 'CHECK'
) AS check_decisions_verdict_exists
\gset
\if :check_decisions_verdict_exists
\echo ok: check decisions_verdict_check exists
\else
\echo ERROR: missing required check constraint orphanproof.decisions.decisions_verdict_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'decisions'
      AND constraint_name = 'decisions_confidence_score_check'
      AND constraint_type = 'CHECK'
) AS check_decisions_confidence_score_exists
\gset
\if :check_decisions_confidence_score_exists
\echo ok: check decisions_confidence_score_check exists
\else
\echo ERROR: missing required check constraint orphanproof.decisions.decisions_confidence_score_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'decisions'
      AND constraint_name = 'decisions_human_status_check'
      AND constraint_type = 'CHECK'
) AS check_decisions_human_status_exists
\gset
\if :check_decisions_human_status_exists
\echo ok: check decisions_human_status_check exists
\else
\echo ERROR: missing required check constraint orphanproof.decisions.decisions_human_status_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'decisions'
      AND constraint_name = 'decisions_decision_source_check'
      AND constraint_type = 'CHECK'
) AS check_decisions_decision_source_exists
\gset
\if :check_decisions_decision_source_exists
\echo ok: check decisions_decision_source_check exists
\else
\echo ERROR: missing required check constraint orphanproof.decisions.decisions_decision_source_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'human_approvals'
      AND constraint_name = 'human_approvals_status_check'
      AND constraint_type = 'CHECK'
) AS check_human_approvals_status_exists
\gset
\if :check_human_approvals_status_exists
\echo ok: check human_approvals_status_check exists
\else
\echo ERROR: missing required check constraint orphanproof.human_approvals.human_approvals_status_check
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'resources'
      AND constraint_type = 'PRIMARY KEY'
) AS pk_resources_exists
\gset
\if :pk_resources_exists
\echo ok: primary key exists on orphanproof.resources
\else
\echo ERROR: missing required primary key on orphanproof.resources
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'memory_events'
      AND constraint_type = 'PRIMARY KEY'
) AS pk_memory_events_exists
\gset
\if :pk_memory_events_exists
\echo ok: primary key exists on orphanproof.memory_events
\else
\echo ERROR: missing required primary key on orphanproof.memory_events
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'exceptions'
      AND constraint_type = 'PRIMARY KEY'
) AS pk_exceptions_exists
\gset
\if :pk_exceptions_exists
\echo ok: primary key exists on orphanproof.exceptions
\else
\echo ERROR: missing required primary key on orphanproof.exceptions
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'decisions'
      AND constraint_type = 'PRIMARY KEY'
) AS pk_decisions_exists
\gset
\if :pk_decisions_exists
\echo ok: primary key exists on orphanproof.decisions
\else
\echo ERROR: missing required primary key on orphanproof.decisions
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'decision_embeddings'
      AND constraint_type = 'PRIMARY KEY'
) AS pk_decision_embeddings_exists
\gset
\if :pk_decision_embeddings_exists
\echo ok: primary key exists on orphanproof.decision_embeddings
\else
\echo ERROR: missing required primary key on orphanproof.decision_embeddings
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = 'orphanproof'
      AND table_name = 'human_approvals'
      AND constraint_type = 'PRIMARY KEY'
) AS pk_human_approvals_exists
\gset
\if :pk_human_approvals_exists
\echo ok: primary key exists on orphanproof.human_approvals
\else
\echo ERROR: missing required primary key on orphanproof.human_approvals
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_schema = kcu.constraint_schema
     AND tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
     AND tc.table_name = kcu.table_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON tc.constraint_schema = ccu.constraint_schema
     AND tc.constraint_name = ccu.constraint_name
    WHERE tc.table_schema = 'orphanproof'
      AND tc.table_name = 'memory_events'
      AND tc.constraint_type = 'FOREIGN KEY'
      AND kcu.column_name = 'resource_id'
      AND ccu.table_schema = 'orphanproof'
      AND ccu.table_name = 'resources'
      AND ccu.column_name = 'id'
) AS fk_memory_events_resource_exists
\gset
\if :fk_memory_events_resource_exists
\echo ok: foreign key orphanproof.memory_events.resource_id to orphanproof.resources.id exists
\else
\echo ERROR: missing required foreign key orphanproof.memory_events.resource_id to orphanproof.resources.id
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_schema = kcu.constraint_schema
     AND tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
     AND tc.table_name = kcu.table_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON tc.constraint_schema = ccu.constraint_schema
     AND tc.constraint_name = ccu.constraint_name
    WHERE tc.table_schema = 'orphanproof'
      AND tc.table_name = 'exceptions'
      AND tc.constraint_type = 'FOREIGN KEY'
      AND kcu.column_name = 'resource_id'
      AND ccu.table_schema = 'orphanproof'
      AND ccu.table_name = 'resources'
      AND ccu.column_name = 'id'
) AS fk_exceptions_resource_exists
\gset
\if :fk_exceptions_resource_exists
\echo ok: foreign key orphanproof.exceptions.resource_id to orphanproof.resources.id exists
\else
\echo ERROR: missing required foreign key orphanproof.exceptions.resource_id to orphanproof.resources.id
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_schema = kcu.constraint_schema
     AND tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
     AND tc.table_name = kcu.table_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON tc.constraint_schema = ccu.constraint_schema
     AND tc.constraint_name = ccu.constraint_name
    WHERE tc.table_schema = 'orphanproof'
      AND tc.table_name = 'decisions'
      AND tc.constraint_type = 'FOREIGN KEY'
      AND kcu.column_name = 'resource_id'
      AND ccu.table_schema = 'orphanproof'
      AND ccu.table_name = 'resources'
      AND ccu.column_name = 'id'
) AS fk_decisions_resource_exists
\gset
\if :fk_decisions_resource_exists
\echo ok: foreign key orphanproof.decisions.resource_id to orphanproof.resources.id exists
\else
\echo ERROR: missing required foreign key orphanproof.decisions.resource_id to orphanproof.resources.id
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_schema = kcu.constraint_schema
     AND tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
     AND tc.table_name = kcu.table_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON tc.constraint_schema = ccu.constraint_schema
     AND tc.constraint_name = ccu.constraint_name
    WHERE tc.table_schema = 'orphanproof'
      AND tc.table_name = 'decision_embeddings'
      AND tc.constraint_type = 'FOREIGN KEY'
      AND kcu.column_name = 'decision_id'
      AND ccu.table_schema = 'orphanproof'
      AND ccu.table_name = 'decisions'
      AND ccu.column_name = 'id'
) AS fk_decision_embeddings_decision_exists
\gset
\if :fk_decision_embeddings_decision_exists
\echo ok: foreign key orphanproof.decision_embeddings.decision_id to orphanproof.decisions.id exists
\else
\echo ERROR: missing required foreign key orphanproof.decision_embeddings.decision_id to orphanproof.decisions.id
SELECT 1 / 0;
\endif

SELECT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_schema = kcu.constraint_schema
     AND tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
     AND tc.table_name = kcu.table_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON tc.constraint_schema = ccu.constraint_schema
     AND tc.constraint_name = ccu.constraint_name
    WHERE tc.table_schema = 'orphanproof'
      AND tc.table_name = 'human_approvals'
      AND tc.constraint_type = 'FOREIGN KEY'
      AND kcu.column_name = 'decision_id'
      AND ccu.table_schema = 'orphanproof'
      AND ccu.table_name = 'decisions'
      AND ccu.column_name = 'id'
) AS fk_human_approvals_decision_exists
\gset
\if :fk_human_approvals_decision_exists
\echo ok: foreign key orphanproof.human_approvals.decision_id to orphanproof.decisions.id exists
\else
\echo ERROR: missing required foreign key orphanproof.human_approvals.decision_id to orphanproof.decisions.id
SELECT 1 / 0;
\endif

SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema = 'orphanproof'
  AND table_name IN (
      'resources',
      'memory_events',
      'exceptions',
      'decisions',
      'decision_embeddings',
      'human_approvals'
  )
ORDER BY table_name;

SHOW CLUSTER SETTING feature.vector_index.enabled;

SHOW COLUMNS FROM orphanproof.resources;
SHOW COLUMNS FROM orphanproof.memory_events;
SHOW COLUMNS FROM orphanproof.exceptions;
SHOW COLUMNS FROM orphanproof.decisions;
SHOW COLUMNS FROM orphanproof.decision_embeddings;
SHOW COLUMNS FROM orphanproof.human_approvals;

SELECT
    tc.table_schema,
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    cc.check_clause
FROM information_schema.table_constraints AS tc
LEFT JOIN information_schema.check_constraints AS cc
    ON tc.constraint_schema = cc.constraint_schema
   AND tc.constraint_name = cc.constraint_name
WHERE tc.table_schema = 'orphanproof'
ORDER BY tc.table_name, tc.constraint_name;

SHOW INDEX FROM orphanproof.resources;
SHOW INDEX FROM orphanproof.memory_events;
SHOW INDEX FROM orphanproof.exceptions;
SHOW INDEX FROM orphanproof.decisions;
SHOW INDEX FROM orphanproof.decision_embeddings;
SHOW INDEX FROM orphanproof.human_approvals;

SHOW CREATE TABLE orphanproof.decision_embeddings;

SELECT 'resources' AS table_name, count(*) AS row_count FROM orphanproof.resources
UNION ALL
SELECT 'memory_events' AS table_name, count(*) AS row_count FROM orphanproof.memory_events
UNION ALL
SELECT 'exceptions' AS table_name, count(*) AS row_count FROM orphanproof.exceptions
UNION ALL
SELECT 'decisions' AS table_name, count(*) AS row_count FROM orphanproof.decisions
UNION ALL
SELECT 'decision_embeddings' AS table_name, count(*) AS row_count FROM orphanproof.decision_embeddings
UNION ALL
SELECT 'human_approvals' AS table_name, count(*) AS row_count FROM orphanproof.human_approvals
ORDER BY table_name;

SELECT
    'schema_contract_status' AS schema_contract_status,
    'PASS' AS result;
