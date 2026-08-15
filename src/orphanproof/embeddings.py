"""Bedrock Titan embeddings and deterministic memory text builders."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Protocol

from orphanproof.config import DEFAULT_AWS_REGION, DEFAULT_EMBEDDING_MODEL
from orphanproof.models import HistoricalDecision, MemoryContext

EMBEDDING_DIMENSIONS = 1024


class EmbeddingProviderError(RuntimeError):
    """Raised when embedding generation fails closed."""


class EmbeddingProviderProtocol(Protocol):
    model_id: str

    def embed_text(self, text: str) -> list[float]: ...


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _decimal_text(value: Decimal) -> str:
    return f"{value:.2f}"


def build_canonical_decision_memory_text(
    context: MemoryContext,
    decision: HistoricalDecision,
) -> str:
    """Build stable semantic text for historical decision embeddings."""

    resource = context.resource
    relevant_events = [
        {
            "event_type": event.event_type.value,
            "summary": event.summary,
            "evidence": event.evidence,
        }
        for event in context.memory_events
    ]
    exception_signals = [
        {
            "reason": exception.reason,
            "status": exception.status.value,
        }
        for exception in context.exceptions
    ]
    lines = [
        "Cloud Nexus OrphanProof historical decision memory",
        f"resource_type: {resource.resource_type.value}",
        f"lifecycle_state: {resource.lifecycle_state}",
        f"created_via: {resource.created_via.value}",
        f"current_evidence: {_stable_json(resource.current_evidence)}",
        f"historical_verdict: {decision.verdict.value}",
        f"historical_confidence_score: {_decimal_text(decision.confidence_score)}",
        f"human_status: {decision.human_status.value}",
        f"blast_radius: {decision.blast_radius}",
        f"evidence_summary: {decision.evidence_summary}",
        f"recommended_action: {decision.recommended_action}",
        f"rollback_plan: {decision.rollback_plan}",
        f"memory_events: {_stable_json(relevant_events)}",
        f"exceptions: {_stable_json(exception_signals)}",
        f"evidence_signals: {_stable_json(context.evidence_signals.model_dump(mode='json'))}",
    ]
    return "\n".join(lines)


def build_current_resource_retrieval_text(context: MemoryContext) -> str:
    """Build stable semantic text for vector retrieval of the current resource."""

    resource = context.resource
    lines = [
        "Cloud Nexus OrphanProof current resource evidence",
        f"resource_type: {resource.resource_type.value}",
        f"lifecycle_state: {resource.lifecycle_state}",
        f"created_via: {resource.created_via.value}",
        f"current_evidence: {_stable_json(resource.current_evidence)}",
        "memory_events: "
        + _stable_json(
            [
                {
                    "event_type": event.event_type.value,
                    "summary": event.summary,
                    "evidence": event.evidence,
                }
                for event in context.memory_events
            ]
        ),
        "exceptions: "
        + _stable_json(
            [
                {
                    "reason": exception.reason,
                    "status": exception.status.value,
                }
                for exception in context.exceptions
            ]
        ),
        f"evidence_signals: {_stable_json(context.evidence_signals.model_dump(mode='json'))}",
    ]
    return "\n".join(lines)


class BedrockEmbeddingProvider:
    """Generates 1024-dimensional normalized Titan embeddings through Bedrock Runtime."""

    def __init__(
        self,
        client: Any | None = None,
        model_id: str = DEFAULT_EMBEDDING_MODEL,
        region_name: str = DEFAULT_AWS_REGION,
    ) -> None:
        self._client = client
        self.model_id = model_id
        self._region_name = region_name

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client("bedrock-runtime", region_name=self._region_name)
        return self._client

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingProviderError("embedding text must not be empty")
        body = json.dumps(
            {
                "inputText": text,
                "dimensions": EMBEDDING_DIMENSIONS,
                "normalize": True,
            }
        )
        try:
            response = self.client.invoke_model(modelId=self.model_id, body=body)
        except Exception as exc:  # pragma: no cover - provider-specific
            raise EmbeddingProviderError(_sanitize_provider_error(exc)) from exc
        embedding = self._extract_embedding(response)
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise EmbeddingProviderError("embedding response dimensions did not match VECTOR(1024)")
        return embedding

    @staticmethod
    def _extract_embedding(response: Any) -> list[float]:
        try:
            raw_body = response["body"].read()
            payload = json.loads(raw_body)
            vector = payload["embedding"]
        except Exception as exc:
            raise EmbeddingProviderError("malformed embedding provider response") from exc
        if not isinstance(vector, list) or not all(
            isinstance(item, int | float) for item in vector
        ):
            raise EmbeddingProviderError("malformed embedding vector")
        return [float(item) for item in vector]


def _sanitize_provider_error(exc: Exception) -> str:
    name = exc.__class__.__name__
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = response.get("Error", {}).get("Code")
        if code:
            return f"embedding provider failed: {name}: {code}"
    return f"embedding provider failed: {name}"
