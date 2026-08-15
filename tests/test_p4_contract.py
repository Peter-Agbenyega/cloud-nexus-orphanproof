from __future__ import annotations

import importlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from test_p3_service import FakeMemoryRepository

from orphanproof.agent import OrphanProofAgent
from orphanproof.api import create_app
from orphanproof.config import Settings
from orphanproof.embeddings import (
    EMBEDDING_DIMENSIONS,
    BedrockEmbeddingProvider,
    EmbeddingProviderError,
    build_canonical_decision_memory_text,
    build_current_resource_retrieval_text,
)
from orphanproof.mcp_integration import (
    CockroachManagedMcpClient,
    McpIntegrationError,
    is_tool_allowed,
)
from orphanproof.memory_provider import DirectMemoryContextProvider, ManagedMcpMemoryContextProvider
from orphanproof.models import (
    CurrentAIVerdict,
    MemoryTransport,
    SimilarHistoricalDecision,
    contains_affirmative_destructive_execution_claim,
)
from orphanproof.reasoning import (
    SYSTEM_PROMPT,
    BedrockReasoningProvider,
    ReasoningProviderError,
    build_reasoning_prompt,
    build_repair_prompt,
    parse_current_ai_verdict,
)
from orphanproof.service import MemoryService, ResourceNotFoundError
from orphanproof.vector_memory import (
    DecisionEmbeddingWriter,
    VectorMemoryRepository,
    validate_vector_limit,
    vector_literal,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeBody:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


class FakeEmbeddingClient:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.vector = vector or [0.01] * EMBEDDING_DIMENSIONS

    def invoke_model(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"body": FakeBody({"embedding": self.vector})}


class FakeReasoningClient:
    def __init__(self, texts: list[str]) -> None:
        self.texts = texts
        self.calls: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        text = self.texts.pop(0)
        return {"output": {"message": {"content": [{"text": text}]}}}


class FakeConnection:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.executed: list[tuple[str, tuple[Any, ...]]] = []
        self.committed = False
        self.rowcount = 1

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    def cursor(self) -> FakeConnection:
        return self

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        self.executed.append((sql, params))

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows

    def commit(self) -> None:
        self.committed = True


class FakeDatabase:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.connection = FakeConnection(rows)

    def connect(self) -> FakeConnection:
        return self.connection


class FakeEmbeddingProvider:
    model_id = "fake-embedding"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        return [0.01] * EMBEDDING_DIMENSIONS


class FakeVectorRepository:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[list[float], int]] = []

    def find_similar_decisions(
        self,
        query_embedding: list[float],
        limit: int = 3,
    ) -> list[SimilarHistoricalDecision]:
        self.calls.append((query_embedding, limit))
        if self.fail:
            raise RuntimeError("vector provider failed")
        return [
            SimilarHistoricalDecision(
                decision_id=UUID("40000000-0000-4000-8000-000000000001"),
                resource_key="demo-rds-dr-standby-001",
                resource_type="RDS_INSTANCE",
                lifecycle_state="STANDBY",
                historical_verdict="KEEP",
                distance=0.1,
                similarity=0.9,
                evidence_summary="DR evidence exists.",
                recommended_action="Keep.",
                blast_radius="High.",
                rollback_plan="Restore.",
            )
        ]


class FakeReasoningProvider:
    model_id = "fake-reasoning"

    def __init__(self, verdict: str = "KEEP", fail: bool = False) -> None:
        self.verdict = verdict
        self.fail = fail
        self.calls = 0

    def reason(
        self, context: Any, similar_decisions: list[SimilarHistoricalDecision]
    ) -> CurrentAIVerdict:
        self.calls += 1
        if self.fail:
            raise RuntimeError("reasoning provider failed")
        return CurrentAIVerdict(
            verdict=self.verdict,
            confidence_score=90,
            evidence_summary="Evidence supports recommendation.",
            blast_radius="Human review required.",
            recommended_action="Recommend review.",
            rollback_plan="Restore from synthetic snapshot if needed.",
            human_review_required=True,
        )


class P4EmbeddingTests(unittest.TestCase):
    def test_canonical_memory_text_is_deterministic_and_semantic(self):
        context = MemoryService(FakeMemoryRepository()).get_memory_context(
            "demo-rds-dr-standby-001"
        )
        decision = context.historical_decisions[0]
        first = build_canonical_decision_memory_text(context, decision)
        second = build_canonical_decision_memory_text(context, decision)
        self.assertEqual(first, second)
        self.assertIn("resource_type: RDS_INSTANCE", first)
        self.assertIn("historical_verdict: KEEP", first)
        self.assertNotIn(str(decision.id), first)

    def test_current_retrieval_text_contains_evidence(self):
        context = MemoryService(FakeMemoryRepository()).get_memory_context("demo-ebs-abandoned-001")
        text = build_current_resource_retrieval_text(context)
        self.assertIn("resource_type: EBS_VOLUME", text)
        self.assertIn("ownership", text.lower())

    def test_titan_request_and_dimension_validation(self):
        client = FakeEmbeddingClient()
        provider = BedrockEmbeddingProvider(client=client, model_id="amazon.titan-embed-text-v2:0")
        vector = provider.embed_text("stable memory")
        self.assertEqual(len(vector), 1024)
        body = json.loads(client.calls[0]["body"])
        self.assertEqual(client.calls[0]["modelId"], "amazon.titan-embed-text-v2:0")
        self.assertEqual(body["dimensions"], 1024)
        self.assertTrue(body["normalize"])
        self.assertEqual(body["inputText"], "stable memory")

    def test_wrong_size_and_malformed_embedding_response_rejected(self):
        with self.assertRaises(EmbeddingProviderError):
            BedrockEmbeddingProvider(client=FakeEmbeddingClient([0.1])).embed_text("x")

        class Malformed:
            def invoke_model(self, **kwargs: Any) -> dict[str, Any]:
                return {"body": FakeBody({"not_embedding": []})}

        with self.assertRaises(EmbeddingProviderError):
            BedrockEmbeddingProvider(client=Malformed()).embed_text("x")

    def test_provider_import_makes_no_boto3_client(self):
        module = importlib.import_module("orphanproof.embeddings")
        self.assertTrue(hasattr(module, "BedrockEmbeddingProvider"))


class P4VectorTests(unittest.TestCase):
    def test_vector_literal_and_limit_validation(self):
        self.assertTrue(vector_literal([0.0] * 1024).startswith("[0.0"))
        with self.assertRaises(ValueError):
            vector_literal([0.0])
        with self.assertRaises(ValueError):
            validate_vector_limit(0)
        with self.assertRaises(ValueError):
            validate_vector_limit(6)

    def test_similarity_repository_uses_parameterized_cosine_select(self):
        rows = [
            {
                "decision_id": UUID("40000000-0000-4000-8000-000000000001"),
                "resource_key": "demo-rds-dr-standby-001",
                "resource_type": "RDS_INSTANCE",
                "lifecycle_state": "STANDBY",
                "historical_verdict": "KEEP",
                "distance": 0.2,
                "similarity": 0.8,
                "evidence_summary": "e",
                "recommended_action": "a",
                "blast_radius": "b",
                "rollback_plan": "r",
            }
        ]
        database = FakeDatabase(rows)
        result = VectorMemoryRepository(database).find_similar_decisions([0.0] * 1024)
        sql, params = database.connection.executed[0]
        self.assertIn("<=>", sql)
        self.assertIn("%s::VECTOR(1024)", sql)
        self.assertNotRegex(sql.upper(), r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE)\b")
        self.assertEqual(len(params), 4)
        self.assertEqual(result[0].historical_verdict, "KEEP")
        self.assertFalse(hasattr(result[0], "embedding"))

    def test_embedding_writer_scoped_to_decision_embeddings(self):
        database = FakeDatabase()
        changed = DecisionEmbeddingWriter(database).upsert_decision_embedding(
            "40000000-0000-4000-8000-000000000001",
            "memory",
            [0.0] * 1024,
            "amazon.titan-embed-text-v2:0",
        )
        sql, params = database.connection.executed[0]
        self.assertEqual(changed, 1)
        self.assertIn("INSERT INTO orphanproof.decision_embeddings", sql)
        self.assertIn("ON CONFLICT (decision_id)", sql)
        self.assertNotRegex(sql.upper(), r"\b(DELETE|DROP|TRUNCATE|ALTER|CREATE)\b")
        self.assertEqual(len(params), 4)
        self.assertTrue(database.connection.committed)


class P4McpTests(unittest.TestCase):
    def load_mcp_verifier_module(self) -> Any:
        script_path = REPO_ROOT / "scripts" / "p4_verify_mcp.py"
        spec = importlib.util.spec_from_file_location("p4_verify_mcp_test", script_path)
        self.assertIsNotNone(spec)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_default_disabled_report_and_secret_repr(self):
        settings = Settings(mcp_bearer_token="secret-token", mcp_cluster_id="secret-cluster")
        text = repr(settings)
        self.assertNotIn("secret-token", text)
        self.assertNotIn("secret-cluster", text)
        report = CockroachManagedMcpClient(Settings()).capability_report()
        self.assertFalse(report.configured)
        self.assertFalse(report.connected)

    def test_mcp_verifier_loads_explicit_env_file(self):
        module = self.load_mcp_verifier_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "ORPHANPROOF_MCP_ENABLED=true",
                        "ORPHANPROOF_MCP_CLUSTER_ID=fake-cluster-for-test",
                        "ORPHANPROOF_MCP_BEARER_TOKEN=fake-token-for-test",
                    ]
                ),
                encoding="utf-8",
            )
            settings = module.load_settings(env_path)
            lines = "\n".join(module.build_status_lines(settings))
        self.assertTrue(settings.mcp_is_configured())
        self.assertNotIn("fake-token-for-test", repr(settings))
        self.assertNotIn("fake-cluster-for-test", repr(settings))
        self.assertIn("MCP_CLUSTER_ID_PRESENT=True", lines)
        self.assertIn("MCP_AUTH_PRESENT=True", lines)
        self.assertNotIn("fake-token-for-test", lines)
        self.assertNotIn("fake-cluster-for-test", lines)

    def test_mcp_verifier_missing_file_and_missing_auth_skip_safely(self):
        module = self.load_mcp_verifier_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_env_path = Path(tmpdir) / ".env"
            missing_file_settings = module.load_settings(missing_env_path)
            empty_env_path = Path(tmpdir) / "empty.env"
            empty_env_path.write_text("ORPHANPROOF_MCP_ENABLED=true\n", encoding="utf-8")
            missing_auth_settings = module.load_settings(empty_env_path)

        for settings in (missing_file_settings, missing_auth_settings):
            with self.subTest(settings=repr(settings)):
                lines = module.build_status_lines(settings)
                self.assertFalse(settings.mcp_is_configured())
                self.assertIn("MCP_LIVE_VERIFICATION=SKIPPED", lines)
                self.assertIn("MCP_AUTH_PRESENT=False", lines)

    def test_allowlist_and_deny_policy(self):
        self.assertTrue(is_tool_allowed("select_query"))
        self.assertTrue(is_tool_allowed("get_table_schema"))
        self.assertFalse(is_tool_allowed("insert_rows"))
        self.assertFalse(is_tool_allowed("create_database"))

    def test_mcp_mode_does_not_silently_fallback(self):
        class FailingMcp:
            def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
                raise McpIntegrationError("MCP failed")

            def list_tools(self) -> list[str]:
                return []

        provider = ManagedMcpMemoryContextProvider(FailingMcp(), lambda _key, _result: None)
        with self.assertRaises(McpIntegrationError):
            provider.get_memory_context("demo-rds-dr-standby-001")
        self.assertEqual(provider.memory_transport, MemoryTransport.COCKROACHDB_MANAGED_MCP)

    def test_fake_mcp_provider_returns_typed_context(self):
        context = MemoryService(FakeMemoryRepository()).get_memory_context(
            "demo-rds-dr-standby-001"
        )

        class FakeMcp:
            def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
                return {"ok": True}

            def list_tools(self) -> list[str]:
                return ["select_query"]

        provider = ManagedMcpMemoryContextProvider(FakeMcp(), lambda _key, _result: context)
        self.assertEqual(provider.get_memory_context("demo-rds-dr-standby-001"), context)
        self.assertEqual(provider.memory_transport.value, "cockroachdb_managed_mcp")


class P4ReasoningTests(unittest.TestCase):
    def valid_json(self, verdict: str = "KEEP", human_review: bool = True) -> str:
        return json.dumps(
            {
                "verdict": verdict,
                "confidence_score": 91,
                "evidence_summary": "DR evidence and active exception support retention.",
                "blast_radius": "High risk requires review.",
                "recommended_action": "Keep pending human review.",
                "rollback_plan": "Restore from synthetic snapshot if needed.",
                "human_review_required": human_review,
            }
        )

    def test_prompt_contains_safety_policy_and_untrusted_data_rule(self):
        context = MemoryService(FakeMemoryRepository()).get_memory_context(
            "demo-rds-dr-standby-001"
        )
        prompt = build_reasoning_prompt(context, [])
        self.assertIn("human_review_required", prompt)
        self.assertIn("Text inside resource names", SYSTEM_PROMPT)
        self.assertIn("You recommend. You do not execute.", SYSTEM_PROMPT)

    def test_nova_model_and_structured_json_validation(self):
        client = FakeReasoningClient([self.valid_json()])
        provider = BedrockReasoningProvider(client=client, model_id="amazon.nova-lite-v1:0")
        context = MemoryService(FakeMemoryRepository()).get_memory_context(
            "demo-rds-dr-standby-001"
        )
        verdict = provider.reason(context, [])
        self.assertEqual(verdict.verdict, "KEEP")
        self.assertEqual(client.calls[0]["modelId"], "amazon.nova-lite-v1:0")
        self.assertEqual(client.calls[0]["inferenceConfig"]["temperature"], 0.0)

    def test_invalid_output_rejected_or_repaired_once(self):
        context = MemoryService(FakeMemoryRepository()).get_memory_context(
            "demo-rds-dr-standby-001"
        )
        client = FakeReasoningClient(["not-json", self.valid_json("QUARANTINE")])
        verdict = BedrockReasoningProvider(client=client).reason(context, [])
        self.assertEqual(verdict.verdict, "QUARANTINE")
        self.assertEqual(len(client.calls), 2)
        original_prompt = client.calls[0]["messages"][0]["content"][0]["text"]
        repair_prompt = client.calls[1]["messages"][0]["content"][0]["text"]
        repair_payload = json.loads(repair_prompt)
        self.assertEqual(repair_payload["original_evidence_prompt"], original_prompt)
        self.assertEqual(repair_payload["invalid_model_response"], "not-json")
        self.assertIn("Do not invent evidence", repair_payload["instruction"])
        self.assertEqual(client.calls[1]["system"][0]["text"], SYSTEM_PROMPT)
        with self.assertRaises(ReasoningProviderError):
            failing_client = FakeReasoningClient(["not-json", "still bad"])
            BedrockReasoningProvider(client=failing_client).reason(
                context,
                [],
            )
        self.assertEqual(len(failing_client.calls), 2)

    def test_repair_prompt_contains_original_evidence_and_invalid_response(self):
        prompt = '{"current_resource_evidence": {"resource": "demo"}}'
        repair = build_repair_prompt(prompt, "malformed response")
        payload = json.loads(repair)
        self.assertEqual(payload["original_evidence_prompt"], prompt)
        self.assertEqual(payload["invalid_model_response"], "malformed response")
        self.assertIn("Do not invent evidence", payload["instruction"])

    def test_invalid_verdict_confidence_and_false_human_review_rejected(self):
        with self.assertRaises(ReasoningProviderError):
            parse_current_ai_verdict(self.valid_json("DESTROY"))
        payload = json.loads(self.valid_json())
        payload["confidence_score"] = 101
        with self.assertRaises(ReasoningProviderError):
            parse_current_ai_verdict(json.dumps(payload))
        with self.assertRaises(ReasoningProviderError):
            parse_current_ai_verdict(self.valid_json(human_review=False))

    def test_destructive_execution_claim_rejected(self):
        payload = json.loads(self.valid_json())
        payload["evidence_summary"] = "I deleted the resource."
        with self.assertRaises(ReasoningProviderError):
            parse_current_ai_verdict(json.dumps(payload))

    def test_destructive_execution_detector_allows_safe_language(self):
        accepted = (
            "No action taken.",
            "No resource was deleted.",
            "If the resource is deleted, restore the snapshot.",
            "If removal is approved, detach only after human review.",
            "The resource should not be terminated automatically.",
            "Deletion would require explicit human approval.",
            "No automatic remediation occurred.",
            "The resource remains unchanged.",
            "Recommend deletion only after human approval.",
            "If rollback is needed after an approved deletion, restore the snapshot.",
        )
        for text in accepted:
            with self.subTest(text=text):
                self.assertFalse(contains_affirmative_destructive_execution_claim(text))
                CurrentAIVerdict(
                    verdict="QUARANTINE",
                    confidence_score=50,
                    evidence_summary=text,
                    blast_radius="Review required.",
                    recommended_action="Require human review.",
                    rollback_plan="Restore snapshot if needed.",
                    human_review_required=True,
                )

    def test_destructive_execution_detector_rejects_affirmative_execution_claims(self):
        rejected = (
            "The resource was deleted.",
            "We deleted the volume.",
            "The instance has been terminated.",
            "The Elastic IP was released.",
            "The volume was detached.",
            "The database was stopped.",
            "The resource was removed.",
            "The action was taken automatically.",
            "We terminated the instance.",
            "The remediation was executed.",
        )
        for text in rejected:
            with self.subTest(text=text):
                self.assertTrue(contains_affirmative_destructive_execution_claim(text))
                with self.assertRaises(ValueError):
                    CurrentAIVerdict(
                        verdict="QUARANTINE",
                        confidence_score=50,
                        evidence_summary=text,
                        blast_radius="Review required.",
                        recommended_action="Require human review.",
                        rollback_plan="Restore snapshot if needed.",
                        human_review_required=True,
                    )


class P4OrchestrationAndApiTests(unittest.TestCase):
    def build_agent(self, verdict: str = "KEEP", vector_fail: bool = False) -> OrphanProofAgent:
        return OrphanProofAgent(
            memory_provider=DirectMemoryContextProvider(FakeMemoryRepository()),
            embedding_provider=FakeEmbeddingProvider(),
            vector_repository=FakeVectorRepository(fail=vector_fail),
            reasoning_provider=FakeReasoningProvider(verdict=verdict),
        )

    def test_agent_order_and_safe_response(self):
        agent = self.build_agent("KEEP")
        result = agent.analyze_resource("demo-rds-dr-standby-001")
        self.assertEqual(result.analysis_mode, "ai_assisted")
        self.assertTrue(result.ai_verdict_generated)
        self.assertFalse(result.decision_persisted)
        self.assertFalse(result.automatic_action_taken)
        self.assertTrue(result.human_review_required)
        self.assertEqual(result.memory_transport, MemoryTransport.DIRECT_COCKROACHDB)
        self.assertEqual(result.vector_neighbors_used, 1)

    def test_unknown_resource_and_provider_failures(self):
        with self.assertRaises(ResourceNotFoundError):
            self.build_agent().analyze_resource("missing-resource")
        with self.assertRaises(RuntimeError):
            self.build_agent(vector_fail=True).analyze_resource("demo-rds-dr-standby-001")

    def test_rds_and_ebs_fake_scenarios(self):
        self.assertEqual(
            self.build_agent("KEEP")
            .analyze_resource("demo-rds-dr-standby-001")
            .current_ai_verdict.verdict,
            "KEEP",
        )
        self.assertEqual(
            self.build_agent("QUARANTINE")
            .analyze_resource("demo-ebs-abandoned-001")
            .current_ai_verdict.verdict,
            "QUARANTINE",
        )

    def test_api_preserves_p3_and_adds_p4_analyze(self):
        client = TestClient(
            create_app(
                repository=FakeMemoryRepository(),
                agent=self.build_agent("KEEP"),
                settings=Settings(database_url=None),
            )
        )
        p3 = client.get("/api/v1/resources/demo-rds-dr-standby-001/memory-context").json()
        self.assertEqual(p3["analysis_mode"], "evidence_only")
        self.assertFalse(p3["ai_verdict_generated"])

        response = client.post("/api/v1/resources/demo-rds-dr-standby-001/analyze")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["analysis_mode"], "ai_assisted")
        self.assertTrue(payload["ai_verdict_generated"])
        self.assertFalse(payload["automatic_action_taken"])
        self.assertTrue(payload["human_review_required"])
        self.assertIn("embedding_model", payload)
        self.assertNotIn("[0.01", json.dumps(payload))

    def test_api_unknown_and_provider_failure_are_sanitized(self):
        client = TestClient(
            create_app(
                repository=FakeMemoryRepository(),
                agent=self.build_agent(vector_fail=True),
                settings=Settings(database_url=None),
            )
        )
        response = client.post("/api/v1/resources/demo-rds-dr-standby-001/analyze")
        self.assertEqual(response.status_code, 503)
        text = json.dumps(response.json())
        self.assertNotIn("DATABASE_URL", text)
        self.assertNotIn("Bearer", text)

    def test_api_provider_failure_returns_fixed_public_message(self):
        class SecretFailAgent:
            def __init__(self, message: str) -> None:
                self.message = message

            def analyze_resource(self, resource_key: str) -> None:
                raise RuntimeError(self.message)

        secret_messages = (
            "Bearer topsecret",
            "postgresql://user:password@example.invalid/db",
            "AWS_SECRET_ACCESS_KEY=supersecret",
            "AWS_SESSION_TOKEN=sessionsecret",
            "ORPHANPROOF_MCP_BEARER_TOKEN=mcpsecret",
            "ORPHANPROOF_MCP_CLUSTER_ID=cluster-secret",
        )
        forbidden_fragments = (
            "Bearer",
            "topsecret",
            "postgresql://",
            "postgres://",
            "example.invalid",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "supersecret",
            "sessionsecret",
            "ORPHANPROOF_MCP_BEARER_TOKEN",
            "ORPHANPROOF_MCP_CLUSTER_ID",
            "mcpsecret",
            "cluster-secret",
        )
        for secret_message in secret_messages:
            with self.subTest(secret_message=secret_message):
                client = TestClient(
                    create_app(
                        repository=FakeMemoryRepository(),
                        agent=SecretFailAgent(secret_message),
                        settings=Settings(database_url=None),
                    )
                )
                response = client.post("/api/v1/resources/demo-rds-dr-standby-001/analyze")
                self.assertEqual(response.status_code, 503)
                payload = response.json()
                self.assertEqual(payload["detail"]["message"], "provider failure")
                text = json.dumps(payload)
                self.assertNotIn(secret_message, text)
                for fragment in forbidden_fragments:
                    self.assertNotIn(fragment, text)

    def test_no_aws_remediation_clients_exist(self):
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (REPO_ROOT / "src" / "orphanproof").glob("*.py")
        )
        for service_name in ("ec2", "rds", "s3", "iam", "lambda"):
            self.assertNotIn(f'boto3.client("{service_name}"', source)
            self.assertNotIn(f"boto3.client('{service_name}'", source)
        self.assertIn('boto3.client("bedrock-runtime"', source)


if __name__ == "__main__":
    unittest.main()
