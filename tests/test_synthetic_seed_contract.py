import ast
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = REPO_ROOT / "db" / "seeds" / "001_synthetic_memory_seed.sql"
VERIFICATION_PATH = REPO_ROOT / "db" / "verification" / "002_verify_synthetic_seed.sql"
LOADER_PATH = REPO_ROOT / "scripts" / "load_synthetic_seed.py"
DOC_PATH = REPO_ROOT / "docs" / "SYNTHETIC_DATASET.md"
README_PATH = REPO_ROOT / "README.md"
PROJECT_CHARTER_PATH = REPO_ROOT / "docs" / "PROJECT_CHARTER.md"
P1_TEST_PATH = REPO_ROOT / "tests" / "test_database_migration_contract.py"
EXPECTED_FILES = (
    SEED_PATH,
    VERIFICATION_PATH,
    LOADER_PATH,
    REPO_ROOT / "tests" / "test_synthetic_seed_contract.py",
    DOC_PATH,
)


def extract_values_block(sql: str, table_name: str) -> str:
    start_match = re.search(
        rf"UPSERT INTO {re.escape(table_name)}\b", sql, re.IGNORECASE
    )
    if not start_match:
        raise AssertionError(f"missing values block for {table_name}")

    values_match = re.search(r"\bVALUES\b", sql[start_match.end() :], re.IGNORECASE)
    if not values_match:
        raise AssertionError(f"missing VALUES keyword for {table_name}")

    values_start = start_match.end() + values_match.end()
    in_string = False
    index = values_start
    while index < len(sql):
        char = sql[index]
        if char == "'":
            if in_string and index + 1 < len(sql) and sql[index + 1] == "'":
                index += 2
                continue
            in_string = not in_string
        elif char == ";" and not in_string:
            return sql[values_start:index]
        index += 1

    raise AssertionError(f"missing statement terminator for {table_name}")


def split_top_level_rows(values_block: str) -> list[str]:
    rows = []
    depth = 0
    start = None
    in_string = False
    index = 0
    while index < len(values_block):
        char = values_block[index]
        if char == "'":
            if in_string and index + 1 < len(values_block) and values_block[index + 1] == "'":
                index += 2
                continue
            in_string = not in_string
        elif not in_string:
            if char == "(":
                if depth == 0:
                    start = index
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and start is not None:
                    rows.append(values_block[start : index + 1])
                    start = None
        index += 1
    return rows


class SyntheticSeedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme_text = README_PATH.read_text(encoding="utf-8")
        cls.project_charter_text = PROJECT_CHARTER_PATH.read_text(encoding="utf-8")
        cls.dataset_doc_text = DOC_PATH.read_text(encoding="utf-8")
        cls.seed_sql = SEED_PATH.read_text(encoding="utf-8")
        cls.seed_upper = cls.seed_sql.upper()
        cls.verification_sql = VERIFICATION_PATH.read_text(encoding="utf-8")
        cls.verification_upper = cls.verification_sql.upper()
        cls.loader_source = LOADER_PATH.read_text(encoding="utf-8")
        cls.p1_test_source = P1_TEST_PATH.read_text(encoding="utf-8")
        cls.resource_rows = split_top_level_rows(
            extract_values_block(cls.seed_sql, "orphanproof.resources")
        )
        cls.memory_event_rows = split_top_level_rows(
            extract_values_block(cls.seed_sql, "orphanproof.memory_events")
        )
        cls.exception_rows = split_top_level_rows(
            extract_values_block(cls.seed_sql, "orphanproof.exceptions")
        )
        cls.decision_rows = split_top_level_rows(
            extract_values_block(cls.seed_sql, "orphanproof.decisions")
        )
        cls.approval_rows = split_top_level_rows(
            extract_values_block(cls.seed_sql, "orphanproof.human_approvals")
        )

    def test_all_new_files_exist(self):
        for path in EXPECTED_FILES:
            with self.subTest(path=path):
                self.assertTrue(path.exists())

    def test_seed_resource_counts(self):
        self.assertEqual(len(self.resource_rows), 18)
        self.assertEqual(sum("'EBS_VOLUME'" in row for row in self.resource_rows), 6)
        self.assertEqual(sum("'ELASTIC_IP'" in row for row in self.resource_rows), 6)
        self.assertEqual(sum("'RDS_INSTANCE'" in row for row in self.resource_rows), 6)

    def test_seed_related_record_counts(self):
        self.assertGreaterEqual(len(self.memory_event_rows), 40)
        self.assertEqual(len(self.exception_rows), 3)
        self.assertGreaterEqual(len(self.decision_rows), 6)
        self.assertGreaterEqual(sum("'KEEP'" in row for row in self.decision_rows), 2)
        self.assertGreaterEqual(sum("'QUARANTINE'" in row for row in self.decision_rows), 2)
        self.assertGreaterEqual(sum("'REMOVE'" in row for row in self.decision_rows), 2)
        self.assertGreaterEqual(len(self.approval_rows), 2)

    def test_required_demo_resources_exist(self):
        self.assertIn("demo-rds-dr-standby-001", self.seed_sql)
        self.assertIn("demo-ebs-abandoned-001", self.seed_sql)

    def test_seed_email_addresses_are_fictional(self):
        emails = re.findall(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            self.seed_sql,
        )
        self.assertGreater(len(emails), 0)
        for email in emails:
            with self.subTest(email=email):
                self.assertTrue(email.endswith("@example.invalid"))

    def test_seed_has_no_aws_identifiers_or_destructive_sql(self):
        self.assertIsNone(re.search(r"\barn:aws[a-z-]*:", self.seed_sql, re.IGNORECASE))
        seed_without_uuids = re.sub(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            "",
            self.seed_sql,
            flags=re.IGNORECASE,
        )
        self.assertIsNone(re.search(r"\b\d{12}\b", seed_without_uuids))
        for phrase in ("DROP", "TRUNCATE", "DELETE FROM"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.seed_upper)

    def test_seed_does_not_insert_decision_embeddings(self):
        self.assertIsNone(
            re.search(
                r"\b(INSERT|UPSERT)\s+INTO\s+orphanproof\.decision_embeddings\b",
                self.seed_sql,
                re.IGNORECASE,
            )
        )

    def test_verification_sql_remains_read_only(self):
        for token in ("INSERT", "UPDATE", "UPSERT", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"):
            with self.subTest(token=token):
                self.assertIsNone(re.search(rf"\b{token}\b", self.verification_upper))
        self.assertNotIn(r"\!", self.verification_sql)

    def test_verification_sql_checks_required_counts_and_stories(self):
        required_fragments = (
            "COUNT(*) = 18",
            "resource_type = 'EBS_VOLUME'",
            "resource_type = 'ELASTIC_IP'",
            "resource_type = 'RDS_INSTANCE'",
            "COUNT(*) >= 40",
            "COUNT(*) = 3",
            "status = 'ACTIVE'",
            "status = 'EXPIRED'",
            "decision_source = 'SEED'",
            "verdict = 'KEEP'",
            "verdict = 'QUARANTINE'",
            "verdict = 'REMOVE'",
            "orphanproof.human_approvals",
            "orphanproof.decision_embeddings",
            "demo-rds-dr-standby-001",
            "event_type = 'DEPENDENCY'",
            "created_via = 'TERRAFORM'",
            "demo-ebs-abandoned-001",
            "event_type = 'OWNERSHIP'",
            "departed fictional owner",
            "email NOT LIKE '%@example.invalid'",
            "synthetic_seed_contract_status",
            "'PASS'",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.verification_sql)
        self.assertIn("SELECT 1 / 0", self.verification_sql)
        self.assertIn(r"\gset", self.verification_sql)
        self.assertIn(r"\if", self.verification_sql)

    def test_loader_supports_only_load_and_verify(self):
        module = ast.parse(self.loader_source)
        commands = None
        for node in module.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "COMMANDS":
                        commands = [
                            key.value
                            for key in node.value.keys
                            if isinstance(key, ast.Constant)
                        ]
        self.assertEqual(set(commands), {"load", "verify"})
        self.assertNotIn("reset", self.loader_source)
        self.assertNotIn("rollback", self.loader_source)
        self.assertNotIn("cleanup", self.loader_source)

    def test_loader_does_not_print_database_url_or_secrets(self):
        forbidden = ("DATABASE_URL", "PGHOST", "PGPASSWORD", "connection string", "connection strings")
        for line in self.loader_source.splitlines():
            if "print(" not in line:
                continue
            for phrase in forbidden:
                with self.subTest(line=line, phrase=phrase):
                    self.assertNotIn(phrase, line)

    def test_loader_uses_safe_psql_settings(self):
        self.assertIn('"PSQL_PAGER": "cat"', self.loader_source)
        self.assertIn('"PAGER": "cat"', self.loader_source)
        self.assertIn('"-P", "pager=off"', self.loader_source)
        self.assertIn('"-X"', self.loader_source)
        self.assertIn('"-v", "ON_ERROR_STOP=1"', self.loader_source)
        self.assertIn("PGSSLROOTCERT.exists()", self.loader_source)
        self.assertIn("flush=True", self.loader_source)

    def test_existing_phase_p1_tests_remain_unchanged(self):
        self.assertIn("class DatabaseMigrationContractTests", self.p1_test_source)
        self.assertIn("MIGRATION_PATH", self.p1_test_source)
        self.assertIn("VERIFICATION_PATH", self.p1_test_source)

    def test_readme_identifies_phase_p2_as_implemented_and_live_verified(self):
        self.assertIn("## Implemented Phase P2 Dataset", self.readme_text)
        self.assertIn(
            "Phase P2 synthetic persistent-memory data ingestion is implemented and live-verified",
            self.readme_text,
        )
        self.assertIn("Live verification returned PASS", self.readme_text)
        self.assertIn("The application and AI agent are not complete", self.readme_text)

    def test_readme_contains_phase_p2_verified_counts(self):
        required_counts = (
            "18 synthetic resources",
            "6 EBS volumes",
            "6 Elastic IP addresses",
            "6 RDS instances",
            "41 memory events",
            "3 exceptions",
            "8 historical seed decisions",
            "2 human approvals",
            "0 decision embeddings",
        )
        for count in required_counts:
            with self.subTest(count=count):
                self.assertIn(count, self.readme_text)

    def test_project_charter_identifies_phase_p2_as_implemented_and_live_verified(self):
        self.assertIn(
            "Phase P2 synthetic data ingestion is IMPLEMENTED AND LIVE VERIFIED",
            self.project_charter_text,
        )
        self.assertIn("The two primary demo stories now exist in CockroachDB", self.project_charter_text)
        self.assertIn("18 synthetic resources", self.project_charter_text)
        self.assertIn("41 memory events", self.project_charter_text)
        self.assertIn("0 decision embeddings", self.project_charter_text)
        self.assertIn(
            "`orphanproof.decision_embeddings` remains empty until the planned vector-memory phase",
            self.project_charter_text,
        )

    def test_synthetic_dataset_doc_no_longer_says_not_loaded(self):
        forbidden_phrases = (
            "has not been loaded",
            "live verification has not been run",
            "not been loaded into the live database",
        )
        for phrase in forbidden_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.dataset_doc_text)
        self.assertIn("loaded into the development CockroachDB cluster", self.dataset_doc_text)

    def test_synthetic_dataset_doc_documents_idempotence_verification(self):
        self.assertIn("loaded twice to confirm idempotence", self.dataset_doc_text)
        self.assertIn("synthetic_seed_contract_status | PASS", self.dataset_doc_text)
        self.assertIn("18 synthetic resources", self.dataset_doc_text)
        self.assertIn("8 historical seed decisions", self.dataset_doc_text)
        self.assertIn("0 decision embeddings", self.dataset_doc_text)
        self.assertIn("does not claim production readiness", self.dataset_doc_text)

    def test_planned_integrations_remain_marked_as_planned_or_not_implemented(self):
        for doc_name, doc_text in (
            ("README.md", self.readme_text),
            ("PROJECT_CHARTER.md", self.project_charter_text),
        ):
            with self.subTest(doc=doc_name, integration="MCP"):
                self.assertIn("MCP integration", doc_text)
                self.assertRegex(doc_text, r"MCP integration: planned|MCP integration.*remain planned")
            with self.subTest(doc=doc_name, integration="Bedrock"):
                self.assertIn("Amazon Bedrock reasoning: planned", doc_text)
            with self.subTest(doc=doc_name, integration="agent workflow"):
                self.assertRegex(doc_text, r"agent (verdict )?workflow")
                self.assertRegex(
                    doc_text,
                    r"agent (verdict )?workflow.*not yet implemented|agent (verdict )?workflow.*remain planned",
                )
            with self.subTest(doc=doc_name, integration="dashboard"):
                self.assertIn("dashboard", doc_text)
                self.assertRegex(doc_text, r"dashboard.*not yet implemented|dashboard.*remain planned")
        self.assertIn("vector retrieval", self.readme_text)
        self.assertIn("vector retrieval", self.project_charter_text)
        self.assertIn("AWS deployment", self.readme_text)
