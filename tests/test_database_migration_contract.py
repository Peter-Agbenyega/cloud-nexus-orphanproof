import unittest
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "db" / "migrations" / "001_initial_memory_schema.sql"
VERIFICATION_PATH = REPO_ROOT / "db" / "verification" / "001_verify_memory_schema.sql"
RUNNER_PATH = REPO_ROOT / "scripts" / "apply_database_migrations.py"
README_PATH = REPO_ROOT / "README.md"
CHARTER_PATH = REPO_ROOT / "docs" / "PROJECT_CHARTER.md"


class DatabaseMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
        cls.migration_upper = cls.migration_sql.upper()
        cls.verification_sql = VERIFICATION_PATH.read_text(encoding="utf-8")
        cls.verification_upper = cls.verification_sql.upper()
        cls.runner_source = RUNNER_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")
        cls.readme_upper = cls.readme.upper()
        cls.charter = CHARTER_PATH.read_text(encoding="utf-8")
        cls.charter_upper = cls.charter.upper()

    def test_migration_file_exists(self):
        self.assertTrue(MIGRATION_PATH.exists())

    def test_required_table_names_exist(self):
        for table_name in (
            "orphanproof.resources",
            "orphanproof.memory_events",
            "orphanproof.exceptions",
            "orphanproof.decisions",
            "orphanproof.decision_embeddings",
            "orphanproof.human_approvals",
        ):
            with self.subTest(table_name=table_name):
                self.assertIn(table_name, self.migration_sql)

    def test_vector_contract_exists(self):
        self.assertIn("VECTOR(1024)", self.migration_upper)
        self.assertIn("CREATE VECTOR INDEX", self.migration_upper)
        self.assertIn("VECTOR_COSINE_OPS", self.migration_upper)

    def test_titan_model_id_exists(self):
        self.assertIn("amazon.titan-embed-text-v2:0", self.migration_sql)

    def test_verdicts_exist(self):
        for verdict in ("KEEP", "QUARANTINE", "REMOVE"):
            with self.subTest(verdict=verdict):
                self.assertIn(verdict, self.migration_upper)

    def test_migration_has_no_forbidden_destructive_sql(self):
        forbidden_phrases = (
            "DROP TABLE",
            "DROP DATABASE",
            "TRUNCATE",
            "DELETE FROM",
        )
        for phrase in forbidden_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.migration_upper)

    def test_verification_sql_is_read_only(self):
        forbidden_tokens = (
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "TRUNCATE",
            "ALTER",
            "UPSERT",
            "SET",
        )
        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertIsNone(
                    re.search(rf"\b{token}\b", self.verification_upper)
                )
        self.assertIsNone(
            re.search(r"\bCREATE\b(?!\s+TABLE\b)", self.verification_upper)
        )
        self.assertNotIn("crdb_internal", self.verification_sql.lower())
        self.assertNotIn(r"\!", self.verification_sql)

    def test_verification_sql_contains_vector_checks(self):
        self.assertIn(
            "SHOW CLUSTER SETTING feature.vector_index.enabled",
            self.verification_sql,
        )
        self.assertIn(
            "SHOW CREATE TABLE orphanproof.decision_embeddings",
            self.verification_sql,
        )
        self.assertIn(
            "SHOW INDEX FROM orphanproof.decision_embeddings",
            self.verification_sql,
        )

    def test_verification_sql_has_explicit_fail_closed_logic(self):
        self.assertNotIn("DO $$", self.verification_sql)
        self.assertNotIn("RAISE EXCEPTION", self.verification_upper)
        self.assertIn(r"\gset", self.verification_sql)
        self.assertIn(r"\if", self.verification_sql)
        self.assertIn(r"\else", self.verification_sql)
        self.assertIn(r"\endif", self.verification_sql)
        self.assertIn("SELECT 1 / 0", self.verification_sql)
        self.assertIn("schema_contract_status", self.verification_sql)
        self.assertIn("'PASS'", self.verification_sql)

    def test_verification_sql_has_no_function_or_procedure_body(self):
        forbidden_patterns = (
            r"\bDO\s+\$\$",
            r"\bDECLARE\b",
            r"\bBEGIN\b",
            r"\bEND\s+\$\$",
            r"\bRAISE\s+EXCEPTION\b",
            r"\bFOR\b[\s\S]*?\bIN\b",
            r"^\s*LOOP\b",
            r"^\s*END\s+LOOP\b",
        )
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(
                    re.search(pattern, self.verification_upper, re.MULTILINE)
                )

    def test_verification_sql_uses_psql_assertion_commands(self):
        if_count = len(re.findall(r"^\\if\b", self.verification_sql, re.MULTILINE))
        else_count = len(re.findall(r"^\\else\b", self.verification_sql, re.MULTILINE))
        endif_count = len(re.findall(r"^\\endif\b", self.verification_sql, re.MULTILINE))
        failure_count = self.verification_sql.count("SELECT 1 / 0")

        self.assertGreater(if_count, 0)
        self.assertEqual(if_count, else_count)
        self.assertEqual(if_count, endif_count)
        self.assertEqual(if_count, failure_count)

    def test_verification_sql_has_one_final_pass_marker(self):
        self.assertEqual(self.verification_sql.count("'PASS'"), 1)
        self.assertRegex(
            self.verification_sql.strip(),
            r"SELECT\s+'schema_contract_status'\s+AS\s+schema_contract_status,\s+'PASS'\s+AS\s+result;$",
        )

    def test_verification_sql_asserts_required_tables(self):
        self.assertIn("information_schema.schemata", self.verification_sql)
        for table_name in (
            "resources",
            "memory_events",
            "exceptions",
            "decisions",
            "decision_embeddings",
            "human_approvals",
        ):
            with self.subTest(table_name=table_name):
                self.assertIn(f"table_name = '{table_name}'", self.verification_sql)
                self.assertIn(
                    f"missing required table orphanproof.{table_name}",
                    self.verification_sql,
                )

    def test_verification_sql_asserts_vector_feature_enabled(self):
        self.assertIn(
            "SHOW CLUSTER SETTING feature.vector_index.enabled",
            self.verification_sql,
        )
        self.assertIn('"feature.vector_index.enabled"::BOOL AS enabled', self.verification_sql)
        self.assertIn(r"\gset vector_feature_", self.verification_sql)
        self.assertIn(r"\if :vector_feature_enabled", self.verification_sql)
        self.assertIn("feature.vector_index.enabled is not true", self.verification_sql)
        self.assertNotIn("vector_feature_feature.vector_index.enabled", self.verification_sql)

    def test_verification_sql_asserts_vector_column_contract(self):
        self.assertIn(
            "SHOW COLUMNS FROM orphanproof.decision_embeddings",
            self.verification_sql,
        )
        self.assertIn("column_name = 'embedding'", self.verification_sql)
        self.assertIn("VECTOR(1024)", self.verification_upper)
        self.assertIn("must be NOT NULL", self.verification_sql)

    def test_verification_sql_asserts_vector_index_contract(self):
        self.assertIn(
            "SHOW CREATE TABLE orphanproof.decision_embeddings",
            self.verification_sql,
        )
        self.assertIn("decision_embeddings_cosine_idx", self.verification_sql)
        self.assertIn("vector_cosine_ops", self.verification_sql)

    def test_verification_sql_asserts_required_normal_indexes(self):
        for index_name in (
            "resources_type_state_idx",
            "memory_events_resource_occurred_idx",
            "exceptions_resource_status_idx",
            "decisions_resource_decided_idx",
            "decisions_verdict_human_status_idx",
        ):
            with self.subTest(index_name=index_name):
                self.assertIn(index_name, self.verification_sql)
        for table_name in (
            "orphanproof.resources",
            "orphanproof.memory_events",
            "orphanproof.exceptions",
            "orphanproof.decisions",
        ):
            with self.subTest(table_name=table_name):
                self.assertIn(f"SHOW INDEX FROM {table_name}", self.verification_sql)

    def test_verification_sql_asserts_required_check_constraints(self):
        for constraint_name in (
            "resources_resource_type_check",
            "resources_created_via_check",
            "resources_monthly_cost_estimate_check",
            "memory_events_event_type_check",
            "exceptions_status_check",
            "decisions_verdict_check",
            "decisions_confidence_score_check",
            "decisions_human_status_check",
            "decisions_decision_source_check",
            "human_approvals_status_check",
        ):
            with self.subTest(constraint_name=constraint_name):
                self.assertIn(constraint_name, self.verification_sql)
        self.assertIn("constraint_type = 'CHECK'", self.verification_sql)

    def test_verification_sql_asserts_primary_and_foreign_keys(self):
        self.assertIn("constraint_type = 'PRIMARY KEY'", self.verification_sql)
        self.assertIn("constraint_type = 'FOREIGN KEY'", self.verification_sql)
        for relationship in (
            ("memory_events", "resource_id", "resources", "id"),
            ("exceptions", "resource_id", "resources", "id"),
            ("decisions", "resource_id", "resources", "id"),
            ("decision_embeddings", "decision_id", "decisions", "id"),
            ("human_approvals", "decision_id", "decisions", "id"),
        ):
            with self.subTest(relationship=relationship):
                for item in relationship:
                    self.assertIn(f"'{item}'", self.verification_sql)

    def test_verification_sql_does_not_wrap_show_in_cte(self):
        self.assertIsNone(
            re.search(
                r"\bWITH\b[\s\S]*?\(\s*SHOW\s+COLUMNS\b",
                self.verification_upper,
            )
        )
        self.assertIsNone(
            re.search(
                r"\bWITH\b[\s\S]*?\(\s*SHOW\s+INDEX\b",
                self.verification_upper,
            )
        )

    def test_runner_never_prints_database_url(self):
        for line in self.runner_source.splitlines():
            stripped = line.strip()
            if stripped.startswith("print("):
                self.assertNotIn("DATABASE_URL", stripped)

    def test_runner_supports_only_migrate_and_verify(self):
        self.assertIn('"migrate": MIGRATION_SQL', self.runner_source)
        self.assertIn('"verify": VERIFICATION_SQL', self.runner_source)
        self.assertIn('argv[1] not in COMMANDS', self.runner_source)
        self.assertNotIn('"seed"', self.runner_source)
        self.assertNotIn('"rollback"', self.runner_source)

    def test_runner_references_root_certificate_path(self):
        self.assertIn('".postgresql"', self.runner_source)
        self.assertIn('"root.crt"', self.runner_source)

    def test_runner_disables_psql_pagers(self):
        self.assertIn('"PSQL_PAGER": "cat"', self.runner_source)
        self.assertIn('"PAGER": "cat"', self.runner_source)
        self.assertIn('"-P", "pager=off", "-f"', self.runner_source)

    def test_runner_keeps_psql_safety_flags(self):
        self.assertIn('"-X"', self.runner_source)
        self.assertIn('"-v", "ON_ERROR_STOP=1"', self.runner_source)

    def test_runner_progress_messages_are_flushed(self):
        expected_prints = (
            'print(f"starting database {command}", flush=True)',
            'print(f"database {command} completed successfully", flush=True)',
            'print(f"database {command} failed", file=sys.stderr, flush=True)',
        )
        for expected_print in expected_prints:
            with self.subTest(expected_print=expected_print):
                self.assertIn(expected_print, self.runner_source)

    def test_readme_no_longer_says_repository_contains_documentation_only(self):
        self.assertNotIn("contains documentation foundations only", self.readme)

    def test_readme_identifies_phase_p1_database_work_as_implemented(self):
        self.assertIn("Phase P1", self.readme)
        self.assertIn("implemented and live-verified", self.readme)
        for completed_item in (
            "CockroachDB orphanproof schema",
            "Six persistent-memory tables",
            "VECTOR(1024) embedding column",
            "Cosine vector index",
            "Safe migration and verification runner",
            "Static contract tests",
            "GitHub Actions contract testing",
            "Gitleaks secret scanning",
        ):
            with self.subTest(completed_item=completed_item):
                self.assertIn(completed_item, self.readme)

    def test_project_charter_identifies_phase_p1_as_implemented_and_live_verified(self):
        self.assertIn("Phase P1", self.charter)
        self.assertIn("IMPLEMENTED AND LIVE-VERIFIED", self.charter)
        self.assertIn("overall application is still under active development", self.charter)

    def test_integration_status_remains_clearly_marked(self):
        implemented_items = (
            "CockroachDB Managed MCP integration",
            "CockroachDB Distributed Vector Indexing",
            "Amazon Bedrock reasoning",
        )
        for item in implemented_items:
            with self.subTest(item=item):
                self.assertIn(item, self.readme)
                self.assertIn(item, self.charter)
        self.assertIn("Phase P4 agentic memory integration", self.charter)
        self.assertIn("implemented locally", self.readme.lower())
        self.assertIn("live verification pending", self.charter.lower())

        planned_items = (
            "AWS Lambda and API Gateway",
            "Amazon S3 Remediation Passports",
            "React dashboard",
            "Human approval interface",
        )
        for item in planned_items:
            with self.subTest(item=item):
                self.assertIn(item, self.readme)
                self.assertIn(item, self.charter)


if __name__ == "__main__":
    unittest.main()
