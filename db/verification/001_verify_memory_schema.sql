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
