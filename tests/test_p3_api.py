from __future__ import annotations

import importlib
import json
import unittest
from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from test_p3_service import FakeMemoryRepository

from orphanproof.api import create_app
from orphanproof.config import Settings
from orphanproof.embeddings import LOCAL_FEATURE_HASH_MODEL
from orphanproof.models import SimilarHistoricalDecision


class FakeVectorRepository:
    def find_similar_decisions(self, query_embedding, limit=3):
        self.query_embedding = query_embedding
        self.limit = limit
        return [
            SimilarHistoricalDecision(
                decision_id=UUID("40000000-0000-4000-8000-000000000001"),
                resource_key="demo-rds-dr-standby-001",
                resource_type="RDS_INSTANCE",
                lifecycle_state="STANDBY",
                historical_verdict="KEEP",
                distance=0.043,
                similarity=0.957,
                evidence_summary="DR documentation and dependency memory exist.",
                recommended_action="Keep and review exception.",
                blast_radius="High synthetic DR risk.",
                rollback_plan="Restore from synthetic snapshot.",
            )
        ]


class P3ApiTests(unittest.TestCase):
    def setUp(self):
        settings = Settings(database_url=None, cors_origins=["http://localhost:5173"])
        now = datetime(2026, 8, 15, tzinfo=UTC)
        self.client = TestClient(
            create_app(
                repository=FakeMemoryRepository(),
                settings=settings,
                now_provider=lambda: now,
            )
        )

    def assert_safe_response(self, payload):
        text = json.dumps(payload)
        forbidden = (
            "DATABASE_URL",
            "postgresql://",
            "SELECT ",
            " INSERT ",
            " UPDATE ",
            " DELETE ",
            " DROP ",
            "password",
            "token",
            "certificate",
        )
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, text)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["phase"], "P3_MEMORY_RETRIEVAL")
        self.assertEqual(payload["database_mode"], "dependency_injected")
        self.assertEqual(payload["deployment_platform"], "local")
        self.assertEqual(payload["analysis_mode"], "evidence_only")
        self.assertFalse(payload["ai_verdict_generated"])

    def test_root_demo_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.text
        self.assertIn("Cloud Nexus OrphanProof", body)
        self.assertIn("Idle doesn't mean orphaned.", body)
        self.assertIn("It never deletes cloud resources automatically.", body)
        self.assertIn("Human review required.", body)
        self.assertIn("Bedrock integration available", body)
        self.assertIn("demo-rds-dr-standby-001", body)
        self.assertIn("demo-ebs-abandoned-001", body)

    def test_demo(self):
        response = self.client.get("/api/v1/demo")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["analysis_mode"], "evidence_only")
        self.assertFalse(payload["ai_verdict_generated"])
        keys = {resource["resource_key"] for resource in payload["resources"]}
        self.assertEqual(keys, {"demo-rds-dr-standby-001", "demo-ebs-abandoned-001"})
        self.assertTrue(all(resource["is_synthetic"] for resource in payload["resources"]))
        self.assert_safe_response(payload)

    def test_list_resources_filtering_and_pagination(self):
        response = self.client.get("/api/v1/resources")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        response = self.client.get("/api/v1/resources?resource_type=RDS_INSTANCE")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["resource_key"], "demo-rds-dr-standby-001")

        response = self.client.get("/api/v1/resources?limit=1&offset=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_invalid_query_values_return_422(self):
        for path in (
            "/api/v1/resources?resource_type=S3_BUCKET",
            "/api/v1/resources?limit=101",
            "/api/v1/resources?offset=-1",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 422)

    def test_get_resource_detail(self):
        response = self.client.get("/api/v1/resources/demo-ebs-abandoned-001")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["resource_type"], "EBS_VOLUME")
        self.assertNotIn("memory_events", payload)
        self.assert_safe_response(payload)

    def test_get_memory_context_and_demo_signals(self):
        response = self.client.get("/api/v1/resources/demo-rds-dr-standby-001/memory-context")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["evidence_signals"]["active_exception_exists"])
        self.assertTrue(payload["evidence_signals"]["dependency_evidence_exists"])
        self.assertTrue(payload["evidence_signals"]["prior_keep_exists"])
        self.assertFalse(payload["ai_verdict_generated"])
        self.assert_safe_response(payload)

        response = self.client.get("/api/v1/resources/demo-ebs-abandoned-001/memory-context")
        payload = response.json()
        self.assertFalse(payload["evidence_signals"]["active_exception_exists"])
        self.assertTrue(payload["evidence_signals"]["ownership_evidence_exists"])
        self.assertTrue(payload["evidence_signals"]["prior_quarantine_exists"])
        self.assert_safe_response(payload)

    def test_vector_memory_endpoint_is_historical_and_safe(self):
        vector_repository = FakeVectorRepository()
        client = TestClient(
            create_app(
                repository=FakeMemoryRepository(),
                vector_repository=vector_repository,
                settings=Settings(
                    database_url=None,
                    cors_origins=["http://localhost:5173"],
                    bedrock_embedding_model=LOCAL_FEATURE_HASH_MODEL,
                ),
                now_provider=lambda: datetime(2026, 8, 15, tzinfo=UTC),
            )
        )

        response = client.get("/api/v1/resources/demo-rds-dr-standby-001/vector-memory")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["analysis_mode"], "vector_memory")
        self.assertEqual(payload["embedding_model"], LOCAL_FEATURE_HASH_MODEL)
        self.assertEqual(payload["memory_transport"], "direct_cockroachdb")
        self.assertFalse(payload["ai_verdict_generated"])
        self.assertIsNone(payload["current_ai_verdict"])
        self.assertFalse(payload["decision_persisted"])
        self.assertFalse(payload["automatic_action_taken"])
        self.assertTrue(payload["human_review_required"])
        self.assertEqual(payload["vector_neighbors_used"], 1)
        self.assertEqual(
            payload["similar_historical_decisions"][0]["historical_verdict"],
            "KEEP",
        )
        self.assertNotIn("current_verdict", json.dumps(payload))
        self.assert_safe_response(payload)
        self.assertEqual(len(vector_repository.query_embedding), 1024)

    def test_unknown_resource_returns_404(self):
        response = self.client.get("/api/v1/resources/missing-resource")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["message"], "resource not found")
        self.assert_safe_response(response.json())

    def test_cors_localhost_and_no_wildcard(self):
        response = self.client.options(
            "/api/v1/resources",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")

        wildcard_settings = {"database_url": None, "cors_origins": ["*"]}
        with self.assertRaises(ValueError):
            Settings(**wildcard_settings)

    def test_no_database_connection_during_app_import(self):
        module = importlib.import_module("orphanproof.api")
        self.assertTrue(hasattr(module, "app"))

    def test_lambda_handler_import(self):
        module = importlib.import_module("orphanproof.lambda_handler")
        self.assertTrue(hasattr(module, "handler"))


if __name__ == "__main__":
    unittest.main()
