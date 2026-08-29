from __future__ import annotations

import unittest

from _support import clone_state, load_state, request, state_hash
from ledgerlab_policy import authorize_object, authorize_report

REQUIRED_EVENT_FIELDS = {
    "event_id",
    "event_type",
    "actor_id",
    "effective_actor_id",
    "credential_id",
    "tenant_id",
    "job_id",
    "action",
    "resource_id",
    "decision",
    "reason_code",
    "reason",
    "correlation_id",
    "policy_version",
}


# [Implementation 7] Fixture-backed policy verification
class PolicyVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_state()

    def assert_decision(
        self,
        function,
        expected: str,
        req: dict,
        state: dict | None = None,
        reason_code: str | None = None,
    ) -> dict:
        current = clone_state(state if state is not None else self.state)
        # 판정 함수가 입력 상태를 몰래 수정하는 구현도 함께 검출합니다.
        before = state_hash(current)
        result = function(current, req)
        self.assertEqual(expected, result["decision"])
        if reason_code is not None:
            self.assertEqual(reason_code, result["reason_code"])
        self.assertEqual(before, state_hash(current))

        event = result["event"]
        self.assertEqual(REQUIRED_EVENT_FIELDS, set(event))
        self.assertEqual(result["decision"], event["decision"])
        self.assertEqual(result["reason_code"], event["reason_code"])
        self.assertEqual(result["reason"], event["reason"])
        self.assertEqual("authorization.decision", event["event_type"])
        self.assertTrue(event["policy_version"])
        for field in REQUIRED_EVENT_FIELDS - {
            "event_type",
            "decision",
            "reason_code",
            "reason",
            "policy_version",
        }:
            self.assertEqual(req.get(field), event[field], field)
        return result

    def test_report_owner_is_allowed(self) -> None:
        self.assert_decision(
            authorize_report,
            "allow",
            request(
                event_id="EV-RPT-001",
                actor_id="user-a",
                effective_actor_id="user-a",
                action="report.read",
                resource_id="report-a",
            ),
            reason_code="report_scope_satisfied",
        )

    def test_report_scope_denials(self) -> None:
        cases = [
            (
                "cross owner",
                request(
                    event_id="EV-RPT-002",
                    actor_id="user-b",
                    effective_actor_id="user-b",
                    action="report.read",
                    resource_id="report-a",
                ),
                "report_scope_mismatch",
                None,
            ),
            (
                "pending report",
                request(
                    event_id="EV-RPT-003",
                    actor_id="user-a",
                    effective_actor_id="user-a",
                    action="report.read",
                    resource_id="report-pending",
                ),
                "report_not_completed",
                None,
            ),
            (
                "unknown report",
                request(
                    event_id="EV-RPT-004",
                    actor_id="user-a",
                    effective_actor_id="user-a",
                    action="report.read",
                    resource_id="report-missing",
                ),
                "actor_or_report_not_found",
                None,
            ),
            (
                "foreign tenant actor",
                request(
                    event_id="EV-RPT-005",
                    actor_id="user-c",
                    effective_actor_id="user-c",
                    action="report.read",
                    resource_id="report-a",
                ),
                "actor_tenant_mismatch",
                None,
            ),
            (
                "delegated actor",
                request(
                    event_id="EV-RPT-006",
                    actor_id="user-a",
                    effective_actor_id="user-b",
                    action="report.read",
                    resource_id="report-a",
                ),
                "actor_context_invalid",
                None,
            ),
            (
                "missing tenant",
                request(
                    event_id="EV-RPT-007",
                    actor_id="user-a",
                    effective_actor_id="user-a",
                    tenant_id=None,
                    action="report.read",
                    resource_id="report-a",
                ),
                "actor_tenant_mismatch",
                None,
            ),
        ]
        for name, req, reason, state in cases:
            with self.subTest(name=name):
                self.assert_decision(
                    authorize_report,
                    "deny",
                    req,
                    state,
                    reason,
                )

    def test_report_policy_context_fails_closed(self) -> None:
        policy_down = clone_state(self.state)
        policy_down["policy_available"] = False
        self.assert_decision(
            authorize_report,
            "deny",
            request(
                event_id="EV-RPT-008",
                actor_id="user-a",
                effective_actor_id="user-a",
                action="report.read",
                resource_id="report-a",
            ),
            policy_down,
            "policy_context_unavailable",
        )

    def test_report_state_tenant_drift_is_denied(self) -> None:
        state = clone_state(self.state)
        state["reports"]["report-a"]["tenant_id"] = "tenant-99"
        self.assert_decision(
            authorize_report,
            "deny",
            request(
                event_id="EV-RPT-009",
                actor_id="user-a",
                effective_actor_id="user-a",
                action="report.read",
                resource_id="report-a",
            ),
            state,
            "report_scope_mismatch",
        )

    def test_current_job_object_is_allowed(self) -> None:
        self.assert_decision(
            authorize_object,
            "allow",
            request(
                event_id="EV-OBJ-001",
                actor_id="id-report-worker",
                effective_actor_id="id-report-worker",
                credential_id="cred-job-81",
                job_id="job-81",
                action="object.read",
                resource_id="synthetic/tenant-42/job-81/input.json",
            ),
            reason_code="credential_scope_satisfied",
        )

    def test_object_scope_and_lifecycle_denials(self) -> None:
        # 유사 prefix와 정확한 만료 시각은 단순 startswith 또는 `<` 비교를 검출합니다.
        cases = [
            (
                "cross job",
                "cred-job-81",
                "job-9",
                "synthetic/tenant-42/job-9/input.json",
                "job_scope_mismatch",
            ),
            (
                "prefix confusion",
                "cred-job-81",
                "job-81",
                "synthetic/tenant-42/job-81x/input.json",
                "object_prefix_mismatch",
            ),
            (
                "parent traversal",
                "cred-job-81",
                "job-81",
                "synthetic/tenant-42/job-81/../job-9/input.json",
                "object_prefix_mismatch",
            ),
            (
                "expired credential",
                "cred-expired",
                "job-81",
                "synthetic/tenant-42/job-81/input.json",
                "credential_expired",
            ),
            (
                "exact expiry",
                "cred-at-expiry",
                "job-81",
                "synthetic/tenant-42/job-81/input.json",
                "credential_expired",
            ),
            (
                "revoked credential",
                "cred-revoked",
                "job-81",
                "synthetic/tenant-42/job-81/input.json",
                "credential_revoked",
            ),
        ]
        for index, (name, credential, job, resource, reason) in enumerate(cases, 1):
            with self.subTest(name=name):
                self.assert_decision(
                    authorize_object,
                    "deny",
                    request(
                        event_id=f"EV-OBJ-{index + 1:03d}",
                        actor_id="id-report-worker",
                        effective_actor_id="id-report-worker",
                        credential_id=credential,
                        job_id=job,
                        action="object.read",
                        resource_id=resource,
                    ),
                    reason_code=reason,
                )

    def test_object_identity_and_context_denials(self) -> None:
        base = {
            "credential_id": "cred-job-81",
            "job_id": "job-81",
            "action": "object.read",
            "resource_id": "synthetic/tenant-42/job-81/input.json",
        }
        cases = [
            (
                "wrong service",
                request(
                    event_id="EV-OBJ-020",
                    actor_id="id-other-worker",
                    effective_actor_id="id-other-worker",
                    **base,
                ),
                "credential_service_mismatch",
            ),
            (
                "delegated service",
                request(
                    event_id="EV-OBJ-021",
                    actor_id="id-report-worker",
                    effective_actor_id="id-other-worker",
                    **base,
                ),
                "actor_context_invalid",
            ),
            (
                "missing job",
                request(
                    event_id="EV-OBJ-022",
                    actor_id="id-report-worker",
                    effective_actor_id="id-report-worker",
                    **{**base, "job_id": None},
                ),
                "job_scope_mismatch",
            ),
            (
                "missing action",
                request(
                    event_id="EV-OBJ-023",
                    actor_id="id-report-worker",
                    effective_actor_id="id-report-worker",
                    **{**base, "action": None},
                ),
                "action_context_invalid",
            ),
        ]
        for name, req, reason in cases:
            with self.subTest(name=name):
                self.assert_decision(
                    authorize_object,
                    "deny",
                    req,
                    reason_code=reason,
                )

    def test_malformed_credential_scope_fails_closed(self) -> None:
        # Credential의 tenant·job·prefix가 서로 맞지 않아도 허용하는 구현을 검출합니다.
        req = request(
            event_id="EV-OBJ-024",
            actor_id="id-report-worker",
            effective_actor_id="id-report-worker",
            credential_id="cred-job-81",
            job_id="job-81",
            action="object.read",
            resource_id="synthetic/tenant-99/job-81/input.json",
        )

        prefix_drift = clone_state(self.state)
        prefix_drift["credentials"]["cred-job-81"][
            "object_prefix"
        ] = "synthetic/tenant-99/job-81/"
        self.assert_decision(
            authorize_object,
            "deny",
            req,
            prefix_drift,
            "credential_scope_incomplete",
        )

        revoked_unknown = clone_state(self.state)
        revoked_unknown["credentials"]["cred-job-81"].pop("revoked")
        self.assert_decision(
            authorize_object,
            "deny",
            {
                **req,
                "event_id": "EV-OBJ-025",
                "resource_id": "synthetic/tenant-42/job-81/input.json",
            },
            revoked_unknown,
            "credential_scope_incomplete",
        )

        tenant_drift = clone_state(self.state)
        tenant_drift["credentials"]["cred-job-81"]["tenant_id"] = "tenant-99"
        tenant_drift["credentials"]["cred-job-81"][
            "object_prefix"
        ] = "synthetic/tenant-99/job-81/"
        self.assert_decision(
            authorize_object,
            "deny",
            {
                **req,
                "event_id": "EV-OBJ-026",
                "resource_id": "synthetic/tenant-99/job-81/input.json",
            },
            tenant_drift,
            "tenant_scope_mismatch",
        )

    def test_object_policy_and_time_context_fail_closed(self) -> None:
        request_value = request(
            event_id="EV-OBJ-030",
            actor_id="id-report-worker",
            effective_actor_id="id-report-worker",
            credential_id="cred-job-81",
            job_id="job-81",
            action="object.read",
            resource_id="synthetic/tenant-42/job-81/input.json",
        )

        policy_down = clone_state(self.state)
        policy_down["policy_available"] = False
        self.assert_decision(
            authorize_object,
            "deny",
            request_value,
            policy_down,
            "policy_context_unavailable",
        )

        missing_now = clone_state(self.state)
        missing_now.pop("now")
        self.assert_decision(
            authorize_object,
            "deny",
            request_value,
            missing_now,
            "time_context_invalid",
        )

        invalid_expiry = clone_state(self.state)
        invalid_expiry["credentials"]["cred-job-81"]["expires_at"] = "invalid"
        self.assert_decision(
            authorize_object,
            "deny",
            request_value,
            invalid_expiry,
            "time_context_invalid",
        )


if __name__ == "__main__":
    unittest.main()
