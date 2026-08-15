#!/usr/bin/env python3
"""Run the narrow P4 live demo against the two primary synthetic stories."""
# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from apply_database_migrations import ENV_PATH, MigrationConfigError, load_database_url

from orphanproof.agent import OrphanProofAgent
from orphanproof.config import Settings
from orphanproof.database import Database
from orphanproof.embeddings import BedrockEmbeddingProvider
from orphanproof.memory_provider import DirectMemoryContextProvider
from orphanproof.reasoning import BedrockReasoningProvider
from orphanproof.repository import MemoryRepository
from orphanproof.vector_memory import VectorMemoryRepository

DEMO_KEYS = ("demo-rds-dr-standby-001", "demo-ebs-abandoned-001")


def fail(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def sanitized_error(exc: Exception) -> str:
    text = str(exc).strip()
    if text and "://" not in text and "Bearer " not in text:
        return text
    return f"{exc.__class__.__name__}"


def main() -> int:
    try:
        settings = Settings(database_url=load_database_url(ENV_PATH))
    except MigrationConfigError as exc:
        fail(str(exc))
    database = Database(settings=settings)
    repository = MemoryRepository(database)
    agent = OrphanProofAgent(
        memory_provider=DirectMemoryContextProvider(repository),
        embedding_provider=BedrockEmbeddingProvider(
            model_id=settings.bedrock_embedding_model,
            region_name=settings.aws_region,
        ),
        vector_repository=VectorMemoryRepository(database),
        reasoning_provider=BedrockReasoningProvider(
            model_id=settings.bedrock_reasoning_model,
            region_name=settings.aws_region,
        ),
    )
    for resource_key in DEMO_KEYS:
        try:
            result = agent.analyze_resource(resource_key)
        except Exception as exc:
            fail(f"P4 demo failed safely for {resource_key}: {sanitized_error(exc)}")
        print(f"RESOURCE={result.resource.resource_key}")
        print(f"MEMORY_TRANSPORT={result.memory_transport.value}")
        print(f"VECTOR_NEIGHBORS={result.vector_neighbors_used}")
        print(f"AI_VERDICT={result.current_ai_verdict.verdict.value}")
        print(f"HUMAN_REVIEW_REQUIRED={result.human_review_required}")
        print(f"AUTOMATIC_ACTION_TAKEN={result.automatic_action_taken}")
        print(f"DECISION_PERSISTED={result.decision_persisted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
