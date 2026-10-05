"""Verify a live local API, including safe intake/review/version flow."""
import argparse
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from urllib.request import urlopen
from urllib.parse import urlencode
from agrogami.ui.api_client import APIClient, ClientError
from agrogami.ui.samples import sample_sms

def run(client: APIClient) -> dict:
    applicant, account = uuid4(), uuid4()
    assert client.request("GET", "/health")["status"] == "ok"
    assert client.request("GET", "/ready")["database"] == "available"
    job = client.intake_sms({"applicant_id": str(applicant), "account_id": str(account),
        "provider": "SYNTHETIC-bKash-like", "text": sample_sms("External inflow")})
    assert job.status == "NEEDS_REVIEW"
    original_candidate = client.candidate(job.candidate_id)
    reviewed = client.request("POST", f"/api/v1/events/{job.event_id}/review", {
        "changes": {"ownership": "external"}, "reason": "Synthetic ownership corroboration", "reviewer_alias": "reviewer-smoke"})
    assert reviewed["validation_status"] == "ACCEPTED"
    assert client.candidate(job.candidate_id) == original_candidate
    now = datetime.now(timezone.utc)
    payload = {"applicant_id": str(applicant), "assessment_time": now.isoformat(), "coverage": {
        "applicant_id": str(applicant), "known_at": (now - timedelta(microseconds=1)).isoformat(),
        "reasons": ["smoke_unknown_coverage"]}}
    first = client.request("POST", "/api/v1/assessments", payload)
    assert first["display_score"] is None
    second_event = client.request("POST", f"/api/v1/events/{reviewed['event_id']}/review", {
        "changes": {"amount": "125.00"}, "reason": "Synthetic amount correction", "reviewer_alias": "reviewer-smoke"})
    assert second_event["supersedes_event_id"] == reviewed["event_id"]
    events = client.events(applicant)
    assert {str(e.event_id) for e in events} >= {str(job.event_id), reviewed["event_id"], second_event["event_id"]}
    features = client.request("GET", f"/api/v1/applicants/{applicant}/features?" + urlencode({
        "scoring_time": datetime.now(timezone.utc).isoformat()}))
    assert features["30"]["features"]["external_inflow_total"]["value"] == "125.00"
    assert second_event["event_id"] in features["30"]["features"]["external_inflow_total"]["contributing_event_ids"]
    assert client.assessment(first["assessment_id"]).model_dump(mode="json") == first
    history = client.request("GET", f"/api/v1/applicants/{applicant}/assessments")
    assert len(history) >= 3
    assert second_event["event_id"] in history[-1]["evidence_version_ids"]
    assert client.request("GET", f"/api/v1/assessments/{first['assessment_id']}/explanation")["reasons"]
    return {"status": "passed", "applicant_id": str(applicant), "assessment_id": first["assessment_id"]}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    client = APIClient(args.api_url, os.environ.get("AGROGAMI_SMOKE_TOKEN", ""))
    try:
        with urlopen(args.api_url.rstrip("/") + "/docs", timeout=10) as response:
            documentation = response.read()
            assert b"<h1>Agrogami AI</h1>" in documentation
            assert b"Traceable underwriting from financial records traditional credit systems ignore" in documentation
            assert b"Demo environment" in documentation
        result = run(client)
        print("PASS: API, docs, synthetic intake, candidate review, correction, snapshots and explanation")
        return 0
    except (ClientError, OSError, AssertionError):
        print("FAIL: local smoke flow; check services and reviewer AGROGAMI_SMOKE_TOKEN")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
