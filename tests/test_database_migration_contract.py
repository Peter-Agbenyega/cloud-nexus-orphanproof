import unittest
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "db" / "migrations" / "001_initial_memory_schema.sql"
VERIFICATION_PATH = REPO_ROOT / "db" / "verification" / "001_verify_memory_schema.sql"
RUNNER_PATH = REPO_ROOT / "scripts" / "apply_database_migrations.py"


class DatabaseMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")
        cls.migration_upper = cls.migration_sql.upper()
        cls.verification_sql = VERIFICATION_PATH.read_text(encoding="utf-8")
        cls.verification_upper = cls.verification_sql.upper()
        cls.runner_source = RUNNER_PATH.read_text(encoding="utf-8")

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
        )
        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertIsNone(
                    re.search(rf"\b{token}\b", self.verification_upper)
                )
        self.assertIsNone(
            re.search(r"\bCREATE\b(?!\s+TABLE\b)", self.verification_upper)
        )

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


if __name__ == "__main__":
    unittest.main()
