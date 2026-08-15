"""Narrow decision embedding persistence and read-only vector similarity search."""

from __future__ import annotations

import re
from collections.abc import Sequence

from orphanproof.database import Database
from orphanproof.models import SimilarHistoricalDecision

MAX_VECTOR_LIMIT = 5
DEFAULT_VECTOR_LIMIT = 3


class VectorMemoryError(RuntimeError):
    """Raised when vector memory operations fail closed."""


def validate_vector_limit(limit: int) -> None:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if limit > MAX_VECTOR_LIMIT:
        raise ValueError("limit must be at most 5")


def vector_literal(vector: Sequence[float]) -> str:
    if len(vector) != 1024:
        raise ValueError("query embedding must contain exactly 1024 dimensions")
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


class DecisionEmbeddingWriter:
    """Writes only orphanproof.decision_embeddings rows."""

    _blocked = re.compile(r"\b(DELETE|DROP|TRUNCATE|ALTER|CREATE)\b", re.I)

    def __init__(self, database: Database):
        self._database = database

    def upsert_decision_embedding(
        self,
        decision_id: str,
        memory_text: str,
        embedding: Sequence[float],
        embedding_model: str,
    ) -> int:
        sql = """
            INSERT INTO orphanproof.decision_embeddings (
                decision_id,
                memory_text,
                embedding,
                embedding_model
            )
            VALUES (%s, %s, %s::VECTOR(1024), %s)
            ON CONFLICT (decision_id) DO UPDATE SET
                memory_text = excluded.memory_text,
                embedding = excluded.embedding,
                embedding_model = excluded.embedding_model
            WHERE orphanproof.decision_embeddings.memory_text IS DISTINCT FROM excluded.memory_text
               OR orphanproof.decision_embeddings.embedding_model IS DISTINCT FROM
                  excluded.embedding_model
        """
        self._assert_scoped_sql(sql)
        with self._database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql, (decision_id, memory_text, vector_literal(embedding), embedding_model)
                )
                count = cursor.rowcount
            connection.commit()
        return int(count if count is not None and count >= 0 else 0)

    @classmethod
    def _assert_scoped_sql(cls, sql: str) -> None:
        normalized = sql.strip().upper()
        if not normalized.startswith("INSERT INTO ORPHANPROOF.DECISION_EMBEDDINGS"):
            raise VectorMemoryError("embedding writer may only insert decision_embeddings")
        if cls._blocked.search(normalized):
            raise VectorMemoryError("embedding writer contains forbidden SQL")
        forbidden_tables = (
            "ORPHANPROOF.RESOURCES",
            "ORPHANPROOF.MEMORY_EVENTS",
            "ORPHANPROOF.EXCEPTIONS",
            "ORPHANPROOF.DECISIONS SET",
            "ORPHANPROOF.HUMAN_APPROVALS",
        )
        if any(table in normalized for table in forbidden_tables):
            raise VectorMemoryError("embedding writer must not modify other memory tables")


class VectorMemoryRepository:
    """Reads nearest historical decisions using CockroachDB cosine distance."""

    _blocked = re.compile(r"\b(INSERT|UPDATE|UPSERT|DELETE|DROP|TRUNCATE|ALTER|CREATE)\b", re.I)

    def __init__(self, database: Database):
        self._database = database

    def find_similar_decisions(
        self,
        query_embedding: Sequence[float],
        limit: int = DEFAULT_VECTOR_LIMIT,
    ) -> list[SimilarHistoricalDecision]:
        validate_vector_limit(limit)
        sql = """
            SELECT
                de.decision_id,
                r.resource_key,
                r.resource_type,
                r.lifecycle_state,
                d.verdict AS historical_verdict,
                (de.embedding <=> %s::VECTOR(1024)) AS distance,
                (1 - (de.embedding <=> %s::VECTOR(1024))) AS similarity,
                d.evidence_summary,
                d.recommended_action,
                d.blast_radius,
                d.rollback_plan
            FROM orphanproof.decision_embeddings AS de
            INNER JOIN orphanproof.decisions AS d
                ON d.id = de.decision_id
            INNER JOIN orphanproof.resources AS r
                ON r.id = d.resource_id
            ORDER BY de.embedding <=> %s::VECTOR(1024) ASC
            LIMIT %s
        """
        self._assert_select_only(sql)
        literal = vector_literal(query_embedding)
        with self._database.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (literal, literal, literal, limit))
                rows = list(cursor.fetchall())
        return [SimilarHistoricalDecision.model_validate(row) for row in rows]

    @classmethod
    def _assert_select_only(cls, sql: str) -> None:
        normalized = sql.strip().upper()
        if not normalized.startswith("SELECT"):
            raise VectorMemoryError("similarity queries must be SELECT-only")
        if cls._blocked.search(normalized):
            raise VectorMemoryError("similarity repository contains forbidden SQL")
