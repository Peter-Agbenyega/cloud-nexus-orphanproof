from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from orphanproof.service import MemoryService, ResourceNotFoundError


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


RDS_ID = UUID("10000000-0000-4000-8000-000000000013")
EBS_ID = UUID("10000000-0000-4000-8000-000000000001")


class FakeMemoryRepository:
    def __init__(self) -> None:
        self.resources = {
            "demo-rds-dr-standby-001": {
                "id": RDS_ID,
                "resource_key": "demo-rds-dr-standby-001",
                "resource_type": "RDS_INSTANCE",
                "region": "us-east-1",
                "created_by": "platform-team@example.invalid",
                "created_via": "TERRAFORM",
                "first_seen": utc("2025-11-01T07:00:00Z"),
                "last_activity": utc("2026-07-02T07:00:00Z"),
                "monthly_cost_estimate": Decimal("412.30"),
                "lifecycle_state": "STANDBY",
                "current_evidence": {
                    "purpose": "regional disaster-recovery standby",
                    "terraform_managed": True,
                },
                "is_synthetic": True,
            },
            "demo-ebs-abandoned-001": {
                "id": EBS_ID,
                "resource_key": "demo-ebs-abandoned-001",
                "resource_type": "EBS_VOLUME",
                "region": "us-east-1",
                "created_by": "former-engineer@example.invalid",
                "created_via": "MANUAL",
                "first_seen": utc("2026-03-15T10:00:00Z"),
                "last_activity": utc("2026-04-03T12:00:00Z"),
                "monthly_cost_estimate": Decimal("38.40"),
                "lifecycle_state": "UNATTACHED",
                "current_evidence": {
                    "known_dependency": False,
                    "recommended_current_verdict": "QUARANTINE",
                },
                "is_synthetic": True,
            },
        }
        self.events = {
            RDS_ID: [
                self._event(26, "CREATION", "Created through Terraform."),
                self._event(27, "ACTIVITY", "Idle utilization observed."),
                self._event(28, "NOTE", "DR purpose documented."),
                self._event(29, "DEPENDENCY", "Supports regional recovery."),
                self._event(30, "EXCEPTION", "Active exception protects standby."),
            ],
            EBS_ID: [
                self._event(1, "CREATION", "Created manually during migration."),
                self._event(2, "OWNERSHIP", "Departed fictional owner."),
                self._event(3, "NOTE", "No known dependent workload."),
            ],
        }
        self.exceptions = {
            RDS_ID: [
                {
                    "id": UUID("30000000-0000-4000-8000-000000000001"),
                    "reason": "Synthetic DR standby exception.",
                    "approved_by": "platform-team@example.invalid",
                    "approved_at": utc("2026-08-01T00:00:00Z"),
                    "expires_at": utc("2026-09-30T00:00:00Z"),
                    "status": "ACTIVE",
                }
            ],
            EBS_ID: [],
        }
        self.decisions = {
            RDS_ID: [
                {
                    "id": UUID("40000000-0000-4000-8000-000000000001"),
                    "verdict": "KEEP",
                    "confidence_score": Decimal("94.00"),
                    "blast_radius": "High synthetic DR risk.",
                    "evidence_summary": "DR documentation and dependency memory exist.",
                    "recommended_action": "Keep and review exception.",
                    "rollback_plan": "Restore from synthetic snapshot.",
                    "human_status": "APPROVED",
                    "decision_source": "SEED",
                    "decided_at": utc("2026-08-01T00:00:00Z"),
                }
            ],
            EBS_ID: [
                {
                    "id": UUID("40000000-0000-4000-8000-000000000002"),
                    "verdict": "QUARANTINE",
                    "confidence_score": Decimal("82.00"),
                    "blast_radius": "Medium unknown rollback data risk.",
                    "evidence_summary": "Unattached and stale ownership evidence.",
                    "recommended_action": "Snapshot and quarantine.",
                    "rollback_plan": "Reattach a synthetic snapshot.",
                    "human_status": "PENDING",
                    "decision_source": "SEED",
                    "decided_at": utc("2026-08-01T00:00:00Z"),
                }
            ],
        }
        self.approvals = {
            RDS_ID: [
                {
                    "id": UUID("50000000-0000-4000-8000-000000000001"),
                    "decision_id": UUID("40000000-0000-4000-8000-000000000001"),
                    "decision_verdict": "KEEP",
                    "status": "APPROVED",
                    "reviewer": "platform-team@example.invalid",
                    "rationale": "Approved KEEP for synthetic DR evidence.",
                    "reviewed_at": utc("2026-08-01T01:00:00Z"),
                }
            ],
            EBS_ID: [],
        }

    def list_resources(
        self,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        rows = sorted(self.resources.values(), key=lambda row: row["resource_key"])
        if resource_type:
            rows = [row for row in rows if row["resource_type"] == resource_type]
        return deepcopy(rows[offset : offset + limit])

    def get_resource(self, resource_key: str) -> dict[str, Any] | None:
        row = self.resources.get(resource_key)
        return deepcopy(row) if row else None

    def get_memory_events(self, resource_id: str) -> list[dict[str, Any]]:
        return deepcopy(self.events.get(UUID(str(resource_id)), []))

    def get_exceptions(self, resource_id: str) -> list[dict[str, Any]]:
        return deepcopy(self.exceptions.get(UUID(str(resource_id)), []))

    def get_decisions(self, resource_id: str) -> list[dict[str, Any]]:
        return deepcopy(self.decisions.get(UUID(str(resource_id)), []))

    def get_human_approvals(self, resource_id: str) -> list[dict[str, Any]]:
        return deepcopy(self.approvals.get(UUID(str(resource_id)), []))

    def get_memory_context(self, resource_key: str) -> dict[str, Any] | None:
        resource = self.get_resource(resource_key)
        if resource is None:
            return None
        resource_id = str(resource["id"])
        return {
            "resource": resource,
            "memory_events": self.get_memory_events(resource_id),
            "exceptions": self.get_exceptions(resource_id),
            "historical_decisions": self.get_decisions(resource_id),
            "human_approvals": self.get_human_approvals(resource_id),
        }

    @staticmethod
    def _event(index: int, event_type: str, summary: str) -> dict[str, Any]:
        return {
            "id": UUID(f"20000000-0000-4000-8000-{index:012d}"),
            "event_type": event_type,
            "summary": summary,
            "evidence": {"synthetic": True},
            "source": "SEED",
            "occurred_at": utc("2026-08-01T00:00:00Z"),
            "recorded_at": utc("2026-08-01T00:00:00Z"),
        }


class P3ServiceTests(unittest.TestCase):
    def setUp(self):
        self.now = utc("2026-08-15T00:00:00Z")
        self.service = MemoryService(FakeMemoryRepository(), now_provider=lambda: self.now)

    def test_resource_listing_and_filtering(self):
        resources = self.service.list_resources()
        self.assertEqual(len(resources), 2)
        rds = self.service.list_resources(resource_type="RDS_INSTANCE")
        self.assertEqual(len(rds), 1)
        self.assertEqual(rds[0].resource_key, "demo-rds-dr-standby-001")

    def test_memory_context_assembly_and_counts(self):
        context = self.service.get_memory_context("demo-rds-dr-standby-001")
        self.assertEqual(context.evidence_counts.total_memory_events, 5)
        self.assertEqual(context.evidence_counts.active_exceptions, 1)
        self.assertEqual(context.evidence_counts.historical_decisions, 1)
        self.assertEqual(context.evidence_counts.human_approvals, 1)

    def test_rds_demo_evidence_signals(self):
        context = self.service.get_memory_context("demo-rds-dr-standby-001")
        self.assertEqual(context.evidence_counts.active_exceptions, 1)
        self.assertEqual(context.evidence_counts.expired_exceptions, 0)
        self.assertTrue(context.evidence_signals.active_exception_exists)
        self.assertFalse(context.evidence_signals.expired_exception_exists)
        self.assertTrue(context.evidence_signals.dependency_evidence_exists)
        self.assertTrue(context.evidence_signals.prior_keep_exists)
        self.assertFalse(context.ai_verdict_generated)

    def test_ebs_demo_evidence_signals(self):
        context = self.service.get_memory_context("demo-ebs-abandoned-001")
        self.assertFalse(context.evidence_signals.active_exception_exists)
        self.assertTrue(context.evidence_signals.ownership_evidence_exists)
        self.assertTrue(context.evidence_signals.prior_quarantine_exists)
        self.assertFalse(context.ai_verdict_generated)

    def test_unknown_resource_raises(self):
        with self.assertRaises(ResourceNotFoundError):
            self.service.get_memory_context("missing-resource")

    def test_active_future_exception_is_effectively_active(self):
        repository = FakeMemoryRepository()
        repository.exceptions[RDS_ID][0]["status"] = "ACTIVE"
        repository.exceptions[RDS_ID][0]["expires_at"] = utc("2026-08-16T00:00:00Z")
        service = MemoryService(repository, now_provider=lambda: self.now)

        context = service.get_memory_context("demo-rds-dr-standby-001")

        self.assertTrue(context.evidence_signals.active_exception_exists)
        self.assertEqual(context.evidence_counts.active_exceptions, 1)
        self.assertFalse(context.evidence_signals.expired_exception_exists)
        self.assertEqual(context.evidence_counts.expired_exceptions, 0)

    def test_active_exception_expiring_now_is_effectively_expired(self):
        repository = FakeMemoryRepository()
        repository.exceptions[RDS_ID][0]["status"] = "ACTIVE"
        repository.exceptions[RDS_ID][0]["expires_at"] = self.now
        service = MemoryService(repository, now_provider=lambda: self.now)

        context = service.get_memory_context("demo-rds-dr-standby-001")

        self.assertFalse(context.evidence_signals.active_exception_exists)
        self.assertEqual(context.evidence_counts.active_exceptions, 0)
        self.assertTrue(context.evidence_signals.expired_exception_exists)
        self.assertEqual(context.evidence_counts.expired_exceptions, 1)

    def test_active_past_exception_is_effectively_expired(self):
        repository = FakeMemoryRepository()
        repository.exceptions[RDS_ID][0]["status"] = "ACTIVE"
        repository.exceptions[RDS_ID][0]["expires_at"] = utc("2026-08-14T23:59:59Z")
        service = MemoryService(repository, now_provider=lambda: self.now)

        context = service.get_memory_context("demo-rds-dr-standby-001")

        self.assertFalse(context.evidence_signals.active_exception_exists)
        self.assertEqual(context.evidence_counts.active_exceptions, 0)
        self.assertTrue(context.evidence_signals.expired_exception_exists)
        self.assertEqual(context.evidence_counts.expired_exceptions, 1)

    def test_active_exception_without_expiration_remains_effectively_active(self):
        repository = FakeMemoryRepository()
        repository.exceptions[RDS_ID][0]["status"] = "ACTIVE"
        repository.exceptions[RDS_ID][0]["expires_at"] = None
        service = MemoryService(repository, now_provider=lambda: self.now)

        context = service.get_memory_context("demo-rds-dr-standby-001")

        self.assertTrue(context.evidence_signals.active_exception_exists)
        self.assertEqual(context.evidence_counts.active_exceptions, 1)
        self.assertFalse(context.evidence_signals.expired_exception_exists)
        self.assertEqual(context.evidence_counts.expired_exceptions, 0)

    def test_stored_expired_exception_remains_expired(self):
        repository = FakeMemoryRepository()
        repository.exceptions[RDS_ID][0]["status"] = "EXPIRED"
        repository.exceptions[RDS_ID][0]["expires_at"] = utc("2026-08-16T00:00:00Z")
        service = MemoryService(repository, now_provider=lambda: self.now)

        context = service.get_memory_context("demo-rds-dr-standby-001")

        self.assertFalse(context.evidence_signals.active_exception_exists)
        self.assertEqual(context.evidence_counts.active_exceptions, 0)
        self.assertTrue(context.evidence_signals.expired_exception_exists)
        self.assertEqual(context.evidence_counts.expired_exceptions, 1)

    def test_stored_revoked_exception_is_neither_active_nor_expired(self):
        repository = FakeMemoryRepository()
        repository.exceptions[RDS_ID][0]["status"] = "REVOKED"
        repository.exceptions[RDS_ID][0]["expires_at"] = utc("2026-08-14T00:00:00Z")
        service = MemoryService(repository, now_provider=lambda: self.now)

        context = service.get_memory_context("demo-rds-dr-standby-001")

        self.assertFalse(context.evidence_signals.active_exception_exists)
        self.assertEqual(context.evidence_counts.active_exceptions, 0)
        self.assertFalse(context.evidence_signals.expired_exception_exists)
        self.assertEqual(context.evidence_counts.expired_exceptions, 0)
        self.assertEqual(context.exceptions[0].status, "REVOKED")


if __name__ == "__main__":
    unittest.main()
