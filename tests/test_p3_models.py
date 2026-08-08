from __future__ import annotations

import unittest
from decimal import Decimal
from uuid import uuid4

from test_p3_service import FakeMemoryRepository

from orphanproof.models import (
    EventType,
    EvidenceCounts,
    EvidenceSignals,
    HistoricalDecision,
    MemoryContext,
    ResourceType,
)


class P3ModelTests(unittest.TestCase):
    def test_enum_validation(self):
        self.assertEqual(ResourceType("EBS_VOLUME"), ResourceType.EBS_VOLUME)
        self.assertEqual(EventType("DEPENDENCY"), EventType.DEPENDENCY)
        with self.assertRaises(ValueError):
            ResourceType("S3_BUCKET")

    def test_decimal_and_datetime_serialization(self):
        decision = HistoricalDecision(
            id=uuid4(),
            verdict="KEEP",
            confidence_score=Decimal("94.00"),
            blast_radius="High synthetic risk.",
            evidence_summary="Evidence exists.",
            recommended_action="Keep.",
            rollback_plan="Restore.",
            human_status="APPROVED",
            decision_source="SEED",
            decided_at="2026-08-01T00:00:00Z",
        )
        payload = decision.model_dump(mode="json")
        self.assertEqual(payload["confidence_score"], "94.00")
        self.assertEqual(payload["decided_at"], "2026-08-01T00:00:00Z")

    def test_memory_context_structure_and_flags(self):
        raw = FakeMemoryRepository().get_memory_context("demo-rds-dr-standby-001")
        context = MemoryContext(
            resource=raw["resource"],
            memory_events=raw["memory_events"],
            exceptions=raw["exceptions"],
            historical_decisions=raw["historical_decisions"],
            human_approvals=raw["human_approvals"],
            evidence_counts=EvidenceCounts(
                total_memory_events=5,
                active_exceptions=1,
                expired_exceptions=0,
                historical_decisions=1,
                human_approvals=1,
            ),
            evidence_signals=EvidenceSignals(
                active_exception_exists=True,
                expired_exception_exists=False,
                dependency_evidence_exists=True,
                ownership_evidence_exists=False,
                creation_evidence_exists=True,
                activity_evidence_exists=True,
                prior_keep_exists=True,
                prior_quarantine_exists=False,
                prior_remove_exists=False,
            ),
        )
        self.assertEqual(context.analysis_mode, "evidence_only")
        self.assertFalse(context.ai_verdict_generated)
        self.assertEqual(context.evidence_counts.total_memory_events, 5)
        self.assertTrue(context.evidence_signals.active_exception_exists)


if __name__ == "__main__":
    unittest.main()
