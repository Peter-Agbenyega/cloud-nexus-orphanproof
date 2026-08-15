"""P4 agent orchestration for AI-assisted memory analysis."""

from __future__ import annotations

from orphanproof.embeddings import EmbeddingProviderProtocol, build_current_resource_retrieval_text
from orphanproof.memory_provider import MemoryContextProviderProtocol
from orphanproof.models import P4AnalysisResponse
from orphanproof.reasoning import ReasoningProviderProtocol
from orphanproof.vector_memory import DEFAULT_VECTOR_LIMIT, VectorMemoryRepository


class OrphanProofAgent:
    """Coordinates evidence, embeddings, vector memory, and Bedrock reasoning."""

    def __init__(
        self,
        memory_provider: MemoryContextProviderProtocol,
        embedding_provider: EmbeddingProviderProtocol,
        vector_repository: VectorMemoryRepository,
        reasoning_provider: ReasoningProviderProtocol,
    ) -> None:
        self._memory_provider = memory_provider
        self._embedding_provider = embedding_provider
        self._vector_repository = vector_repository
        self._reasoning_provider = reasoning_provider

    def analyze_resource(self, resource_key: str) -> P4AnalysisResponse:
        context = self._memory_provider.get_memory_context(resource_key)
        retrieval_text = build_current_resource_retrieval_text(context)
        query_embedding = self._embedding_provider.embed_text(retrieval_text)
        similar_decisions = self._vector_repository.find_similar_decisions(
            query_embedding,
            limit=DEFAULT_VECTOR_LIMIT,
        )
        verdict = self._reasoning_provider.reason(context, similar_decisions)
        return P4AnalysisResponse(
            resource=context.resource,
            current_ai_verdict=verdict,
            similar_historical_decisions=similar_decisions,
            evidence_signals=context.evidence_signals,
            memory_transport=self._memory_provider.memory_transport,
            embedding_model=self._embedding_provider.model_id,
            reasoning_model=self._reasoning_provider.model_id,
            vector_neighbors_used=len(similar_decisions),
        )
