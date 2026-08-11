from __future__ import annotations

import ast
import inspect
import re
import unittest
from pathlib import Path

import orphanproof.repository as repository
from orphanproof.repository import (
    MemoryRepository,
    ReadOnlyQueryError,
    _assert_select_only,
    validate_pagination,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_PATH = REPO_ROOT / "src" / "orphanproof" / "repository.py"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"
API_DOC_PATH = REPO_ROOT / "docs" / "API.md"


class P3RepositoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = REPOSITORY_PATH.read_text(encoding="utf-8")
        cls.module = ast.parse(cls.source)
        cls.sql_literals = cls._extract_sql_literals()

    @classmethod
    def _extract_sql_literals(cls) -> list[str]:
        sql_values = []
        for node in ast.walk(cls.module):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.endswith("COLUMNS"):
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            sql_values.append(node.value.value)
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.JoinedStr):
                    text = "".join(
                        value.value
                        for value in node.value.values
                        if isinstance(value, ast.Constant)
                    )
                    if "FROM orphanproof." in text:
                        sql_values.append(text)
                elif isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    if "FROM orphanproof." in node.value.value:
                        sql_values.append(node.value.value)
        return sql_values

    def test_required_repository_methods_exist(self):
        for method_name in (
            "list_resources",
            "get_resource",
            "get_memory_events",
            "get_exceptions",
            "get_decisions",
            "get_human_approvals",
            "get_memory_context",
        ):
            with self.subTest(method_name=method_name):
                self.assertTrue(callable(getattr(MemoryRepository, method_name)))

    def test_repository_source_contains_select_queries_only(self):
        self.assertGreaterEqual(len(self.sql_literals), 6)
        for sql in self.sql_literals:
            with self.subTest(sql=sql[:80]):
                normalized = sql.strip().upper()
                if "FROM ORPHANPROOF." in normalized:
                    self.assertTrue(normalized.startswith("SELECT"))
                self.assertIsNone(
                    re.search(
                        r"\b(INSERT|UPDATE|UPSERT|DELETE|DROP|TRUNCATE|ALTER|CREATE)\b",
                        normalized,
                    )
                )

    def test_read_only_guard_accepts_multiline_select(self):
        _assert_select_only(
            """
            SELECT
                id,
                event_type
            FROM orphanproof.memory_events
            WHERE resource_id = %s
            """
        )

    def test_read_only_guard_rejects_modifying_sql(self):
        with self.assertRaises(ReadOnlyQueryError):
            _assert_select_only(
                """
                DELETE FROM orphanproof.memory_events
                WHERE resource_id = %s
                """
            )

    def test_sql_uses_orphanproof_schema_explicitly(self):
        expected_tables = (
            "orphanproof.resources",
            "orphanproof.memory_events",
            "orphanproof.exceptions",
            "orphanproof.decisions",
            "orphanproof.human_approvals",
        )
        combined = "\n".join(self.sql_literals)
        for table_name in expected_tables:
            with self.subTest(table_name=table_name):
                self.assertIn(table_name, combined)

    def test_sql_uses_bound_parameters(self):
        parameterized_queries = [
            sql for sql in self.sql_literals if "WHERE" in sql.upper() or "LIMIT" in sql.upper()
        ]
        self.assertGreaterEqual(len(parameterized_queries), 6)
        for sql in parameterized_queries:
            with self.subTest(sql=sql[:80]):
                self.assertIn("%s", sql)

    def test_user_input_is_not_concatenated_into_sql(self):
        for node in ast.walk(self.module):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                left_text = ast.unparse(node.left)
                right_text = ast.unparse(node.right)
                self.assertFalse("sql" in left_text.lower() or "sql" in right_text.lower())
        for function in (
            repository.MemoryRepository.list_resources,
            repository.MemoryRepository.get_resource,
            repository.MemoryRepository.get_memory_events,
            repository.MemoryRepository.get_exceptions,
            repository.MemoryRepository.get_decisions,
            repository.MemoryRepository.get_human_approvals,
        ):
            source = inspect.getsource(function)
            with self.subTest(function=function.__name__):
                self.assertNotRegex(source, r"\{resource_key\}|\{resource_id\}|\{resource_type\}")

    def test_limit_and_offset_validation(self):
        with self.assertRaises(ValueError):
            validate_pagination(101, 0)
        with self.assertRaises(ValueError):
            validate_pagination(50, -1)
        with self.assertRaises(ValueError):
            validate_pagination(-1, 0)

    def test_no_connection_opens_during_module_import(self):
        self.assertNotIn("Database(", self.source.split("class MemoryRepository")[0])
        self.assertNotIn("connect()", self.source.split("class MemoryRepository")[0])

    def test_no_embeddings_or_similarity_retrieval_exists_yet(self):
        lower_source = self.source.lower()
        self.assertNotIn("decision_embeddings", lower_source)
        self.assertNotIn("<=>", lower_source)
        self.assertNotIn("vector_cosine", lower_source)
        self.assertNotIn("similarity", lower_source)

    def test_env_example_omits_credential_shaped_database_url(self):
        env_example = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
        forbidden = ("postgresql://", "postgres://", "username:password")
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, env_example)
        self.assertIsNone(re.search(r"(?m)^\s*DATABASE_URL\s*=\s*\S+", env_example))
        self.assertIn("DATABASE_URL is intentionally omitted", env_example)
        self.assertIn("untracked local .env file", env_example)
        self.assertIn("managed secret service", env_example)
        self.assertIn("Never commit, print, or document", env_example)

    def test_api_docs_omit_credential_shaped_database_url(self):
        api_doc = API_DOC_PATH.read_text(encoding="utf-8")
        forbidden = ("postgresql://", "postgres://", "username:password")
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, api_doc)
        self.assertIn("ignored local `.env` file", api_doc)
        self.assertIn("approved CockroachDB connection workflow", api_doc)
        self.assertIn("Never copy the value into source code", api_doc)
        self.assertIn("Exception evidence uses effective status", api_doc)
        self.assertIn("returned unchanged and is not mutated", api_doc)


if __name__ == "__main__":
    unittest.main()
