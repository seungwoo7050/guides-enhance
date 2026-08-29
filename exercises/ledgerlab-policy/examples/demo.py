from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ledgerlab_policy import authorize_object, authorize_report, detect


def load_state() -> dict:
    path = PROJECT_ROOT / "fixtures/state.json"
    return json.loads(path.read_text(encoding="utf-8"))


def request(**values: object) -> dict:
    base = {
        "event_id": None,
        "actor_id": None,
        "effective_actor_id": None,
        "credential_id": None,
        "tenant_id": "tenant-42",
        "job_id": None,
        "action": None,
        "resource_id": None,
        "correlation_id": "CORR-DEMO-1",
    }
    base.update(values)
    return base


def main() -> int:
    state = load_state()
    owner = authorize_report(
        state,
        request(
            event_id="EV-DEMO-001",
            actor_id="user-a",
            effective_actor_id="user-a",
            action="report.read",
            resource_id="report-a",
        ),
    )
    cross_job = authorize_object(
        state,
        request(
            event_id="EV-DEMO-002",
            actor_id="id-report-worker",
            effective_actor_id="id-report-worker",
            credential_id="cred-job-81",
            job_id="job-9",
            action="object.read",
            resource_id="synthetic/tenant-42/job-9/input.json",
        ),
    )
    output = {
        "decisions": [owner, cross_job],
        "alerts": detect([owner["event"], cross_job["event"]]),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
