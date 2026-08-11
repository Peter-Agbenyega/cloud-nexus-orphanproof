from __future__ import annotations

import importlib
import json
import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from test_p3_service import FakeMemoryRepository

from orphanproof.api import create_app
from orphanproof.config import Settings


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
        self.assertEqual(payload["analysis_mode"], "evidence_only")
        self.assertFalse(payload["ai_verdict_generated"])

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


if __name__ == "__main__":
    unittest.main()
