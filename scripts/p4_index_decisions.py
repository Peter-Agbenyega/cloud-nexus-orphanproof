#!/usr/bin/env python3
"""Plan, load, or verify P4 historical decision embeddings safely."""
# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from apply_database_migrations import ENV_PATH, MigrationConfigError, load_database_url

from orphanproof.config import Settings
from orphanproof.database import Database
from orphanproof.embeddings import build_canonical_decision_memory_text, create_embedding_provider
from orphanproof.repository import MemoryRepository
from orphanproof.service import MemoryService
from orphanproof.vector_memory import DecisionEmbeddingWriter

COMMANDS = {"plan", "load", "verify"}


def fail(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def sanitized_error(exc: Exception) -> str:
    text = str(exc).strip()
    if text and "://" not in text and "Bearer " not in text:
        return text
    return f"{exc.__class__.__name__}"


def _database() -> Database:
    return Database(database_url=load_database_url(ENV_PATH))


def _settings() -> Settings:
    return Settings(
        _env_file=ENV_PATH,
        _env_file_encoding="utf-8",
        database_url=load_database_url(ENV_PATH),
    )


def _decision_rows(database: Database) -> list[dict[str, object]]:
    sql = """
        SELECT
            d.id AS decision_id,
            r.resource_key,
            de.decision_id IS NOT NULL AS embedding_exists
        FROM orphanproof.decisions AS d
        INNER JOIN orphanproof.resources AS r ON r.id = d.resource_id
        LEFT JOIN orphanproof.decision_embeddings AS de ON de.decision_id = d.id
        WHERE d.decision_source = 'SEED'
        ORDER BY d.decided_at ASC, d.id ASC
    """
    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return list(cursor.fetchall())


def plan(database: Database) -> int:
    rows = _decision_rows(database)
    needed = sum(not row["embedding_exists"] for row in rows)
    print(f"HISTORICAL_DECISIONS={len(rows)}")
    print(f"DECISION_EMBEDDINGS_NEEDED={needed}")
    return 0


def load(database: Database) -> int:
    rows = _decision_rows(database)
    settings = _settings()
    provider = create_embedding_provider(
        model_id=settings.bedrock_embedding_model,
        region_name=settings.aws_region,
    )
    writer = DecisionEmbeddingWriter(database)
    service = MemoryService(MemoryRepository(database))
    attempted = 0
    changed = 0
    for row in rows:
        context = service.get_memory_context(str(row["resource_key"]))
        decision = next(
            item for item in context.historical_decisions if str(item.id) == str(row["decision_id"])
        )
        memory_text = build_canonical_decision_memory_text(context, decision)
        embedding = provider.embed_document(memory_text)
        attempted += 1
        changed += writer.upsert_decision_embedding(
            decision_id=str(decision.id),
            memory_text=memory_text,
            embedding=embedding,
            embedding_model=provider.model_id,
        )
    print(f"DECISION_EMBEDDINGS_ATTEMPTED={attempted}")
    print(f"DECISION_EMBEDDINGS_CHANGED={changed}")
    return 0


def verify(database: Database) -> int:
    sql = """
        SELECT
            COUNT(*) AS embedding_count,
            COUNT(DISTINCT embedding_model) AS model_count,
            min(embedding_model) AS embedding_model
        FROM orphanproof.decision_embeddings
    """
    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
            cursor.execute(
                """
                SELECT
                    r.resource_key,
                    d.verdict,
                    (de.embedding <=> de.embedding) AS distance
                FROM orphanproof.decision_embeddings AS de
                INNER JOIN orphanproof.decisions AS d ON d.id = de.decision_id
                INNER JOIN orphanproof.resources AS r ON r.id = d.resource_id
                ORDER BY r.resource_key ASC
                LIMIT 3
                """
            )
            samples = list(cursor.fetchall())
    print(f"DECISION_EMBEDDINGS_COUNT={row['embedding_count']}")
    print(f"DECISION_EMBEDDING_MODEL_COUNT={row['model_count']}")
    print(f"DECISION_EMBEDDING_MODEL={row['embedding_model']}")
    for sample in samples:
        print(
            "VECTOR_SAMPLE="
            f"{sample['resource_key']}|{sample['verdict']}|distance={float(sample['distance']):.6f}"
        )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in COMMANDS:
        fail("usage: python3 scripts/p4_index_decisions.py {plan|load|verify}", 2)
    try:
        database = _database()
        command = argv[1]
        if command == "plan":
            return plan(database)
        if command == "load":
            return load(database)
        return verify(database)
    except MigrationConfigError as exc:
        fail(str(exc))
    except Exception as exc:
        fail(f"P4 indexing failed safely: {sanitized_error(exc)}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
