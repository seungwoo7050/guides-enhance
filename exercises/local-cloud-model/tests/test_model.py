from __future__ import annotations

import json
import unittest

from local_cloud_model import (
    AccessDenied,
    CloudModel,
    CloudModelError,
    EventConflict,
    QuotaExceeded,
    TenantInactive,
)


def provision_pair() -> CloudModel:
    model = CloudModel()
    model.provision_tenant("tenant-a", "starter")
    model.provision_tenant("tenant-b", "starter")
    return model


# [Implementation 9]
# Public API behavior tests.
class CloudModelTest(unittest.TestCase):
    def test_stateful_resources_are_private_and_unique(self) -> None:
        model = provision_pair()

        resources = model.evidence_snapshot("tenant-a")["resources"]

        self.assertEqual(2, len(resources))
        self.assertTrue(all(resource["stateful"] is True for resource in resources))
        self.assertTrue(all(resource["public"] is False for resource in resources))
        self.assertEqual(2, len({resource["id"] for resource in resources}))

    def test_provisioning_rejects_invalid_transitions_atomically(self) -> None:
        model = CloudModel()
        model.provision_tenant("tenant-a", "starter")
        before = model.evidence_snapshot("tenant-a")

        with self.assertRaises(ValueError):
            model.provision_tenant("tenant-b", "unknown")
        with self.assertRaises(CloudModelError):
            model.provision_tenant("tenant-a", "pro")

        self.assertEqual(before, model.evidence_snapshot("tenant-a"))
        self.assertIsNone(model.evidence_snapshot("tenant-b")["tenant"])

    def test_owner_update_preserves_active_document_capacity(self) -> None:
        model = provision_pair()
        model.store_document("tenant-a", "doc-1", "one")
        model.store_document("tenant-a", "doc-2", "two")

        model.store_document("tenant-a", "doc-2", "updated")

        self.assertEqual("updated", model.read_document("tenant-a", "doc-2"))
        self.assertEqual(
            ["doc-1", "doc-2"],
            model.evidence_snapshot("tenant-a")["active_documents"],
        )

    def test_foreign_access_and_missing_reads_are_denied_without_mutation(self) -> None:
        model = provision_pair()
        model.store_document("tenant-a", "doc-a", "synthetic-secret")
        before = model.evidence_snapshot("tenant-a")

        with self.assertRaises(AccessDenied):
            model.read_document("tenant-b", "doc-a")
        with self.assertRaises(AccessDenied):
            model.read_document("tenant-b", "missing")
        with self.assertRaises(AccessDenied):
            model.store_document("tenant-b", "doc-a", "intrusion")

        self.assertEqual(before, model.evidence_snapshot("tenant-a"))
        self.assertEqual("synthetic-secret", model.read_document("tenant-a", "doc-a"))

    def test_document_quota_rejection_is_atomic(self) -> None:
        model = provision_pair()
        model.store_document("tenant-a", "doc-1", "one")
        model.store_document("tenant-a", "doc-2", "two")
        # 예외 전에 doc-3을 저장하는 구현은 snapshot 비교에서 검출됩니다.
        before = model.evidence_snapshot("tenant-a")

        with self.assertRaises(QuotaExceeded):
            model.store_document("tenant-a", "doc-3", "three")

        after = model.evidence_snapshot("tenant-a")
        self.assertEqual(before, after)
        self.assertNotIn("doc-3", after["active_documents"])

    def test_duplicate_events_have_one_effect(self) -> None:
        model = provision_pair()
        model.store_document("tenant-a", "doc-a", "data")
        model.enqueue_event("event-1", "tenant-a", "doc-a")
        model.enqueue_event("event-1", "tenant-a", "doc-a")
        model.enqueue_event("event-2", "tenant-a", "doc-a")

        # 중복 delivery가 output이나 usage를 두 번 늘리는 구현을 검출합니다.
        statuses = [model.process_next(), model.process_next(), model.process_next()]
        evidence = model.evidence_snapshot("tenant-a")

        self.assertEqual(["processed", "duplicate", "processed"], statuses)
        self.assertEqual(2, len(evidence["active_outputs"]))
        self.assertEqual(2, evidence["usage_evidence"])

    def test_event_identity_is_tenant_scoped_and_payload_stable(self) -> None:
        model = provision_pair()
        model.store_document("tenant-a", "doc-a", "a")
        model.store_document("tenant-a", "doc-a2", "a2")
        model.store_document("tenant-b", "doc-b", "b")
        model.enqueue_event("shared-id", "tenant-a", "doc-a")
        model.enqueue_event("shared-id", "tenant-b", "doc-b")
        before = model.evidence_snapshot("tenant-a")

        with self.assertRaises(EventConflict):
            model.enqueue_event("shared-id", "tenant-a", "doc-a2")

        self.assertEqual(before, model.evidence_snapshot("tenant-a"))
        self.assertEqual("processed", model.process_next())
        self.assertEqual("processed", model.process_next())
        self.assertEqual(1, model.usage_for("tenant-a"))
        self.assertEqual(1, model.usage_for("tenant-b"))

    def test_retry_and_dead_letter_bounds_are_exact(self) -> None:
        model = provision_pair()
        model.enqueue_event("missing-1", "tenant-a", "missing")

        self.assertEqual("retry", model.process_next(max_attempts=2))
        interim = model.evidence_snapshot("tenant-a")
        self.assertEqual(1, interim["pending_events"][0]["attempts"])
        self.assertEqual("dead-lettered", model.process_next(max_attempts=2))

        final = model.evidence_snapshot("tenant-a")
        self.assertEqual(2, final["dead_letters"][0]["attempts"])
        self.assertEqual(0, final["usage_evidence"])
        self.assertEqual([], final["active_outputs"])

        one_try = provision_pair()
        one_try.enqueue_event("missing-2", "tenant-a", "missing")
        self.assertEqual("dead-lettered", one_try.process_next(max_attempts=1))
        before_invalid = one_try.evidence_snapshot("tenant-a")
        with self.assertRaises(ValueError):
            one_try.process_next(max_attempts=0)
        self.assertEqual(before_invalid, one_try.evidence_snapshot("tenant-a"))

    def test_foreign_document_event_is_dead_lettered_without_effect(self) -> None:
        model = provision_pair()
        model.store_document("tenant-a", "doc-a", "protected")
        model.enqueue_event("event-b", "tenant-b", "doc-a")

        model.drain_events(max_attempts=2)

        evidence_a = model.evidence_snapshot("tenant-a")
        evidence_b = model.evidence_snapshot("tenant-b")
        self.assertEqual([], evidence_b["active_outputs"])
        self.assertEqual(0, evidence_b["usage_evidence"])
        self.assertEqual(1, len(evidence_b["dead_letters"]))
        self.assertEqual(["doc-a"], evidence_a["active_documents"])

    def test_bounded_drain_preserves_pending_work_evidence(self) -> None:
        model = provision_pair()
        model.enqueue_event("missing", "tenant-a", "missing")

        # 처리 상한에 도달한 뒤 queue를 조용히 비우는 구현을 검출합니다.
        with self.assertRaises(CloudModelError):
            model.drain_events(max_attempts=3, max_steps=1)

        evidence = model.evidence_snapshot("tenant-a")
        self.assertEqual(1, len(evidence["pending_events"]))
        self.assertEqual(1, evidence["pending_events"][0]["attempts"])

    def test_invalid_processing_limits_are_rejected_without_mutation(self) -> None:
        model = provision_pair()
        model.enqueue_event("missing", "tenant-a", "missing")
        before = model.evidence_snapshot("tenant-a")

        with self.assertRaises(ValueError):
            model.process_next(max_attempts=0)
        with self.assertRaises(ValueError):
            model.drain_events(max_attempts=0, max_steps=1)
        with self.assertRaises(ValueError):
            model.drain_events(max_attempts=1, max_steps=0)

        self.assertEqual(before, model.evidence_snapshot("tenant-a"))

    def test_tenant_deletion_clears_active_state_and_retains_evidence(self) -> None:
        model = provision_pair()
        model.store_document("tenant-a", "doc-a", "data")
        model.enqueue_event("processed", "tenant-a", "doc-a")
        self.assertEqual("processed", model.process_next())
        model.enqueue_event("pending", "tenant-a", "missing")
        model.enqueue_event("dead", "tenant-a", "missing")
        self.assertEqual("retry", model.process_next(max_attempts=2))
        self.assertEqual("dead-lettered", model.process_next(max_attempts=1))
        usage_before = model.usage_for("tenant-a")

        model.delete_tenant("tenant-a")

        evidence = model.evidence_snapshot("tenant-a")
        self.assertEqual({"state": "DELETED", "plan": "starter"}, evidence["tenant"])
        for field in (
            "active_documents",
            "active_outputs",
            "pending_events",
            "dead_letters",
            "event_registry",
            "resources",
        ):
            self.assertEqual([], evidence[field])
        self.assertEqual(usage_before, evidence["usage_evidence"])
        tenant_b = model.evidence_snapshot("tenant-b")["tenant"]
        self.assertEqual("ACTIVE", tenant_b["state"])
        with self.assertRaises(TenantInactive):
            model.read_document("tenant-a", "doc-a")
        with self.assertRaises(TenantInactive):
            model.enqueue_event("late", "tenant-a", "doc-a")

    def test_deleted_tenant_identity_is_terminal_and_deletion_is_idempotent(
        self,
    ) -> None:
        model = CloudModel()
        model.provision_tenant("tenant-a", "starter")
        model.delete_tenant("tenant-a")
        first = model.evidence_snapshot("tenant-a")

        model.delete_tenant("tenant-a")
        self.assertEqual(first, model.evidence_snapshot("tenant-a"))
        with self.assertRaises(TenantInactive):
            model.provision_tenant("tenant-a", "pro")
        self.assertEqual(first, model.evidence_snapshot("tenant-a"))

        unknown_before = model.evidence_snapshot("unknown")
        model.delete_tenant("unknown")
        self.assertEqual(unknown_before, model.evidence_snapshot("unknown"))

    def test_evidence_snapshot_is_content_free_deep_and_deterministic(self) -> None:
        model = provision_pair()
        model.store_document("tenant-a", "doc-a", "must-not-appear")

        # 본문 노출과 내부 list aliasing을 한 테스트에서 함께 검출합니다.
        first = model.evidence_snapshot("tenant-a")
        serialized = json.dumps(first, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("must-not-appear", serialized)

        first["active_documents"].append("tampered")
        second = model.evidence_snapshot("tenant-a")
        self.assertNotIn("tampered", second["active_documents"])
        self.assertEqual(second, model.evidence_snapshot("tenant-a"))

    def test_resource_inventory_is_a_sorted_copy(self) -> None:
        model = provision_pair()

        first = model.resource_inventory()
        ids = [resource["id"] for resource in first]
        self.assertEqual(sorted(ids), ids)

        first[0]["public"] = True
        self.assertTrue(
            all(resource["public"] is False for resource in model.resource_inventory())
        )


if __name__ == "__main__":
    unittest.main()
