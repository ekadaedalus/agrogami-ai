"""Create a new repository-local SYNTHETIC scenario, without loading environment settings."""
from datetime import timedelta
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from agrogami.application import ApplicationService
from agrogami.mcp.server import Gateway
from agrogami.schemas import CanonicalEvent, Coverage, utcnow
from agrogami.storage import Store
from agrogami.ui.samples import sample_sms, synthetic_account


DEMO_ROOT = Path(__file__).resolve().parents[1] / "private_data" / "synthetic_demo"


def prepare_demo() -> dict[str, Any]:
    """Append an isolated Tk100 demo; UUIDs and recording times are actually generated."""
    created_at = utcnow()
    scenario_id, applicant_id = uuid4(), uuid4()
    directory = DEMO_ROOT / str(scenario_id)
    directory.mkdir(parents=True, exist_ok=False)
    store = Store("sqlite:///" + (directory / "scenario.db").as_posix())
    try:
        # Deliberately construct an untrained service: never load .env, private
        # databases, real evidence or optional artifacts from the host environment.
        service = ApplicationService(store, directory / "private")
        provider = "SYNTHETIC-bKash-like"
        job = service.sms_intake(applicant_id=applicant_id,
            account_id=synthetic_account(applicant_id, provider),
            provider=provider, text=sample_sms("External inflow", now=created_at))
        assert job.status == "NEEDS_REVIEW" and job.event_id and job.candidate_id
        original = store.get(CanonicalEvent, job.event_id)
        assert original is not None and original.validation_status == "NEEDS_REVIEW"
        accepted = service.review(job.event_id, {"ownership": "external"},
            "Synthetic demo ownership corroboration", "reviewer-demo")
        assert accepted.validation_status == "ACCEPTED"
        pending = service.records.assessments(applicant_id)[-1]
        assessment_time = max(utcnow(), pending.assessment_time + timedelta(microseconds=1))
        coverage = Coverage(applicant_id=applicant_id, known_at=accepted.created_at,
            evidence_event_ids=(accepted.event_id,), reasons=("synthetic_demo_coverage_unknown",))
        snapshots = service.features(applicant_id, assessment_time, coverage)
        for snapshot in snapshots.values():
            store.save(snapshot)
        assessment = service.assessment(applicant_id=applicant_id, t0=assessment_time,
            coverage=coverage, previous_id=pending.assessment_id)
        assert assessment.status == "INSUFFICIENT_EVIDENCE" and assessment.display_score is None
        explanation = Gateway(service).explanation(assessment.assessment_id)
        assert explanation["reasons"] and explanation["limitations"]
        assert store.history(accepted.event_id) == [original, accepted]
        manifest = {
            "scope": "SYNTHETIC_DEMO", "scenario_id": str(scenario_id),
            "created_at": created_at.isoformat(), "applicant_id": str(applicant_id),
            "source_id": str(job.source_id), "candidate_id": str(job.candidate_id),
            "original_event_id": str(job.event_id), "accepted_event_id": str(accepted.event_id),
            "current_event_id": str(accepted.event_id), "assessment_id": str(assessment.assessment_id),
            "assessment_status": assessment.status.value,
            "feature_snapshot_ids": {str(window): str(snapshot.snapshot_id)
                                     for window, snapshot in snapshots.items()},
        }
        # Exclusive creation makes accidental replacement fail visibly.
        with (directory / "manifest.json").open("x", encoding="utf-8") as target:
            json.dump(manifest, target, indent=2)
            target.write("\n")
        return manifest
    finally:
        store.engine.dispose()


def main() -> int:
    try:
        print(json.dumps(prepare_demo(), indent=2))
        return 0
    except Exception:
        print("FAIL: synthetic demo preparation; existing scenarios were not replaced")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
