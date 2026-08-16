"""Bedrock embeddings and deterministic memory text builders."""

from __future__ import annotations

import json
import math
import re
from decimal import Decimal
from hashlib import sha256
from typing import Any, Protocol

from orphanproof.config import DEFAULT_AWS_REGION, DEFAULT_EMBEDDING_MODEL
from orphanproof.models import HistoricalDecision, MemoryContext

EMBEDDING_DIMENSIONS = 1024
TITAN_EMBED_TEXT_V2_MODEL = "amazon.titan-embed-text-v2:0"
COHERE_EMBED_V4_MODEL = "cohere.embed-v4:0"
US_COHERE_EMBED_V4_MODEL = "us.cohere.embed-v4:0"
GLOBAL_COHERE_EMBED_V4_MODEL = "global.cohere.embed-v4:0"
LOCAL_FEATURE_HASH_MODEL = "local.feature-hash-v1"
COHERE_DOCUMENT_INPUT_TYPE = "search_document"
COHERE_QUERY_INPUT_TYPE = "search_query"
SUPPORTED_BEDROCK_EMBEDDING_MODELS = {
    TITAN_EMBED_TEXT_V2_MODEL,
    COHERE_EMBED_V4_MODEL,
    US_COHERE_EMBED_V4_MODEL,
    GLOBAL_COHERE_EMBED_V4_MODEL,
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class EmbeddingProviderError(RuntimeError):
    """Raised when embedding generation fails closed."""


class EmbeddingProviderProtocol(Protocol):
    model_id: str

    def embed_text(self, text: str) -> list[float]: ...

    def embed_document(self, text: str) -> list[float]: ...

    def embed_query(self, text: str) -> list[float]: ...


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
    """Generates 1024-dimensional embeddings through Bedrock Runtime."""

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
        return self.embed_document(text)

    def embed_document(self, text: str) -> list[float]:
        return self._embed(text, input_type=COHERE_DOCUMENT_INPUT_TYPE)

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, input_type=COHERE_QUERY_INPUT_TYPE)

    def _embed(self, text: str, input_type: str) -> list[float]:
        if not text.strip():
            raise EmbeddingProviderError("embedding text must not be empty")
        body = json.dumps(self._request_payload(text, input_type))
        try:
            response = self.client.invoke_model(modelId=self.model_id, body=body)
        except Exception as exc:  # pragma: no cover - provider-specific
            raise EmbeddingProviderError(_sanitize_provider_error(exc)) from exc
        embedding = self._extract_embedding(response)
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise EmbeddingProviderError("embedding response dimensions did not match VECTOR(1024)")
        return embedding

    def _request_payload(self, text: str, input_type: str) -> dict[str, Any]:
        if self.model_id == TITAN_EMBED_TEXT_V2_MODEL:
            return {
                "inputText": text,
                "dimensions": EMBEDDING_DIMENSIONS,
                "normalize": True,
            }
        if _is_cohere_embed_v4_model(self.model_id):
            return {
                "input_type": input_type,
                "texts": [text],
                "embedding_types": ["float"],
                "output_dimension": EMBEDDING_DIMENSIONS,
            }
        raise EmbeddingProviderError("unsupported embedding model")

    def _extract_embedding(self, response: Any) -> list[float]:
        try:
            raw_body = response["body"].read()
            payload = json.loads(raw_body)
        except Exception as exc:
            raise EmbeddingProviderError("malformed embedding provider response") from exc
        if self.model_id == TITAN_EMBED_TEXT_V2_MODEL:
            vector = payload.get("embedding")
        elif _is_cohere_embed_v4_model(self.model_id):
            vector = _extract_cohere_float_embedding(payload)
        else:
            raise EmbeddingProviderError("unsupported embedding model")
        if not isinstance(vector, list) or not all(
            isinstance(item, int | float) for item in vector
        ):
            raise EmbeddingProviderError("malformed embedding vector")
        return [float(item) for item in vector]


class LocalFeatureHashEmbeddingProvider:
    """Deterministic local feature-hash embeddings for offline demos."""

    model_id = LOCAL_FEATURE_HASH_MODEL

    def embed_text(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_document(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        tokens = _TOKEN_PATTERN.findall(text.lower())
        if not tokens:
            return vector

        for token in tokens:
            self._accumulate(vector, f"tok:{token}", 1.0)
            if len(token) >= 4:
                self._accumulate(vector, f"prefix:{token[:4]}", 0.35)
                self._accumulate(vector, f"suffix:{token[-4:]}", 0.35)

        for left, right in zip(tokens, tokens[1:], strict=False):
            self._accumulate(vector, f"bigram:{left}:{right}", 0.75)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

    @staticmethod
    def _accumulate(vector: list[float], feature: str, weight: float) -> None:
        digest = sha256(feature.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign * weight


def create_embedding_provider(
    model_id: str = DEFAULT_EMBEDDING_MODEL,
    region_name: str = DEFAULT_AWS_REGION,
    client: Any | None = None,
) -> EmbeddingProviderProtocol:
    """Create the explicitly configured embedding provider."""

    if model_id == LOCAL_FEATURE_HASH_MODEL:
        if client is not None:
            raise EmbeddingProviderError(
                "local embedding provider does not accept a network client"
            )
        return LocalFeatureHashEmbeddingProvider()
    if model_id in SUPPORTED_BEDROCK_EMBEDDING_MODELS:
        return BedrockEmbeddingProvider(client=client, model_id=model_id, region_name=region_name)
    raise EmbeddingProviderError("unsupported embedding model")


def _is_cohere_embed_v4_model(model_id: str) -> bool:
    return model_id in {
        COHERE_EMBED_V4_MODEL,
        US_COHERE_EMBED_V4_MODEL,
        GLOBAL_COHERE_EMBED_V4_MODEL,
    }


def _extract_cohere_float_embedding(payload: dict[str, Any]) -> Any:
    embeddings = payload.get("embeddings")
    if isinstance(embeddings, list) and len(embeddings) == 1:
        return embeddings[0]
    if isinstance(embeddings, dict):
        float_embeddings = embeddings.get("float")
        if isinstance(float_embeddings, list) and len(float_embeddings) == 1:
            return float_embeddings[0]
    raise EmbeddingProviderError("malformed embedding provider response")


def _sanitize_provider_error(exc: Exception) -> str:
    name = exc.__class__.__name__
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = response.get("Error", {}).get("Code")
        if code:
            return f"embedding provider failed: {name}: {code}"
    return f"embedding provider failed: {name}"
