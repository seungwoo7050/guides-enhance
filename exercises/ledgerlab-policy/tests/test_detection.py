from __future__ import annotations

import copy
import unittest

from _support import load_state, request
from ledgerlab_policy import authorize_object, authorize_report, detect


# [Implementation 7-1] Detection behavior verification
class DetectionVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_state()

    def report_event(
        self,
        event_id: str,
        actor_id: str,
        report_id: str,
        correlation_id: str = "CORR-LAB-1",
    ) -> dict:
        return authorize_report(
            self.state,
            request(
                event_id=event_id,
                actor_id=actor_id,
                effective_actor_id=actor_id,
                action="report.read",
                resource_id=report_id,
                correlation_id=correlation_id,
            ),
        )["event"]

    def object_event(
        self,
        event_id: str,
        job_id: str,
        resource_id: str,
        correlation_id: str = "CORR-LAB-1",
    ) -> dict:
        return authorize_object(
            self.state,
            request(
                event_id=event_id,
                actor_id="id-report-worker",
                effective_actor_id="id-report-worker",
                credential_id="cred-job-81",
                job_id=job_id,
                action="object.read",
                resource_id=resource_id,
                correlation_id=correlation_id,
            ),
        )["event"]

    def test_benign_and_duplicate_events_do_not_alert(self) -> None:
        owner = self.report_event("EV-DET-001", "user-a", "report-a")
        normal_job = self.object_event(
            "EV-DET-002",
            "job-81",
            "synthetic/tenant-42/job-81/input.json",
        )
        self.assertEqual([], detect([owner, normal_job, copy.deepcopy(owner)]))

    def test_cross_scope_denials_share_one_correlation_alert(self) -> None:
        cross_owner = self.report_event("EV-DET-003", "user-b", "report-a")
        cross_job = self.object_event(
            "EV-DET-004",
            "job-9",
            "synthetic/tenant-42/job-9/input.json",
        )
        events = [copy.deepcopy(cross_job), cross_owner, cross_job]
        alerts = detect(events)

        self.assertEqual(1, len(alerts))
        alert = alerts[0]
        self.assertEqual("DET-CROSS-SCOPE:CORR-LAB-1", alert["alert_id"])
        self.assertEqual("CORR-LAB-1", alert["correlation_id"])
        self.assertEqual(
            ["EV-DET-003", "EV-DET-004"],
            alert["evidence_event_ids"],
        )
        self.assertEqual(
            ["id-report-worker", "user-b"],
            alert["actor_ids"],
        )
        self.assertEqual(["cred-job-81"], alert["credential_ids"])
        self.assertEqual(
            ["job_scope_mismatch", "report_scope_mismatch"],
            alert["reason_codes"],
        )

    def test_unrelated_correlations_remain_separate(self) -> None:
        # 서로 다른 요청의 거절을 한 사건으로 합치는 구현을 검출합니다.
        first = self.report_event(
            "EV-DET-005",
            "user-b",
            "report-a",
            "CORR-A",
        )
        second = self.object_event(
            "EV-DET-006",
            "job-9",
            "synthetic/tenant-42/job-9/input.json",
            "CORR-B",
        )
        alerts = detect([second, first])
        self.assertEqual(["CORR-A", "CORR-B"], [a["correlation_id"] for a in alerts])
        self.assertEqual(["EV-DET-005"], alerts[0]["evidence_event_ids"])
        self.assertEqual(["EV-DET-006"], alerts[1]["evidence_event_ids"])

    def test_prefix_scope_denial_is_detected(self) -> None:
        event = self.object_event(
            "EV-DET-007",
            "job-81",
            "synthetic/tenant-42/job-81x/input.json",
        )
        alerts = detect([event])
        self.assertEqual(1, len(alerts))
        self.assertEqual(["object_prefix_mismatch"], alerts[0]["reason_codes"])

    def test_conflicting_duplicate_cannot_hide_suspicious_event(self) -> None:
        # 먼저 도착한 정상형 중복 event만 채택해 거절 기록을 숨기는 구현을 검출합니다.
        suspicious = self.report_event("EV-DET-008", "user-b", "report-a")
        benign_duplicate = copy.deepcopy(suspicious)
        benign_duplicate["decision"] = "allow"
        benign_duplicate["reason_code"] = "report_scope_satisfied"
        benign_duplicate["reason"] = "owner and tenant policy satisfied"

        alerts = detect([benign_duplicate, suspicious])
        self.assertEqual(1, len(alerts))
        self.assertEqual(["EV-DET-008"], alerts[0]["evidence_event_ids"])

    def test_malformed_events_are_ignored(self) -> None:
        self.assertEqual(
            [],
            detect(
                [
                    None,
                    {},
                    {"event_id": ""},
                    {
                        "event_id": "EV-DET-009",
                        "event_type": "authorization.decision",
                        "decision": "deny",
                        "reason_code": "report_scope_mismatch",
                        "correlation_id": None,
                    },
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
