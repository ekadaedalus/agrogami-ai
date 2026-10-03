import base64
from datetime import timedelta
from io import BytesIO
from uuid import UUID, uuid4
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from agrogami.api.app import create_app, Role
from agrogami.application import ApplicationService, EvaluationRun
from agrogami.assessment import AssessmentSnapshot, SnapshotStatus
from agrogami.schemas import CanonicalEvent, Coverage, Source
from agrogami.storage import Store
from agrogami.fixtures import APPLICANT, T0, fixture_event, fixture_sources, coverage
from agrogami.risk.models import LogisticRiskModel, ValidationScope as S
from agrogami.datasets import DatasetIdentity, RiskDataset
from agrogami.calibration.core import Calibrator
from agrogami.fairness.metrics import fairness_metrics


@pytest.fixture
def service(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "core.db"))
    service = ApplicationService(store, tmp_path / "private")
    yield service
    store.engine.dispose()


@pytest.fixture
def client(service):
    with TestClient(create_app(service, tokens={"viewer-test": Role.viewer, "reviewer-test": Role.reviewer, "admin-test": Role.admin})) as client:
        yield client


REVIEWER = {"x-agrogami-token": "reviewer-test"}


def sms_payload(**changes):
    return dict(applicant_id=str(APPLICANT), account_id=str(uuid4()), provider="SYNTHETIC-bKash-like",
        text="SYNTHETIC: Receipt Tk 100.00. Fee Tk 0.00. TrxID A. Date 2025-12-01. Time 10:30:00+06:00.") | changes


def seed(service, **changes):
    event = fixture_event("api-event", **changes)
    service.store.save(fixture_sources([event])[0])
    service.store.save(event)
    return event


def test_health_swagger_reserved_docs_and_openapi(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_sms_intake_creates_candidate_review_job_and_pending_event(client):
    response = client.post("/api/v1/intake/sms", json=sms_payload())
    assert response.status_code == 201
    job = response.json()
    assert job["status"] == "NEEDS_REVIEW"
    assert job["candidate_id"] is not None
    assert client.get(f"/api/v1/jobs/{job['job_id']}").json() == job
    source = client.get(f"/api/v1/sources/{job['source_id']}").json()
    assert source["synthetic"]
    events = client.get(f"/api/v1/applicants/{APPLICANT}/events").json()
    assert events[0]["validation_status"] == "NEEDS_REVIEW"
    assert events[0]["ownership"] == "unknown"


@pytest.mark.parametrize("text", ["unsupported 100 balance 9000", "SYNTHETIC: Payment Tk 100.00. Fee Tk 0.00. TrxID A."])
def test_unsupported_and_missing_time_retained_without_imputation(client, text):
    result = client.post("/api/v1/intake/sms", json=sms_payload(text=text)).json()
    assert result["status"] == "NEEDS_REVIEW"
    assert result["event_id"] is None


@pytest.mark.parametrize("changes", [{"text": ""}, {"applicant_id": "bad-uuid"}, {"extra": "unknown"}])
def test_intake_contract_validation(client, changes):
    assert client.post("/api/v1/intake/sms", json=sms_payload(**changes)).status_code == 422


def test_document_preprocessing_blocked_model_job_no_private_paths(client, service):
    image = Image.new("RGB", (80, 80), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    response = client.post("/api/v1/intake/document", json={"applicant_id": str(APPLICANT),
        "content_base64": base64.b64encode(buffer.getvalue()).decode()})
    assert response.status_code == 201
    assert response.json()["status"] == "BLOCKED_MODEL_ARTIFACT"
    assert str(service.private_dir) not in response.text
    source = client.get("/api/v1/sources/" + response.json()["source_id"])
    assert str(service.private_dir) not in source.text
    assert len(list((service.private_dir / "objects").glob("*.bin"))) == 1


@pytest.mark.parametrize("content", ["invalid-base64!", base64.b64encode(b"not an image").decode()])
def test_invalid_document_safe_error(client, content):
    result = client.post("/api/v1/intake/document", json={"applicant_id": str(APPLICANT), "content_base64": content})
    assert result.status_code == 422
    assert "Traceback" not in result.text


@pytest.mark.parametrize("headers,status", [({}, 403), ({"x-agrogami-token": "viewer-test"}, 403),
    ({"x-agrogami-token": "invalid"}, 401), ({"x-agrogami-role": "admin"}, 403)])
def test_review_authorization(client, service, headers, status):
    event = seed(service)
    result = client.post(f"/api/v1/events/{event.event_id}/review", headers=headers,
        json={"changes": {"amount": "150"}, "reason": "synthetic correction", "reviewer_alias": "reviewer-demo"})
    assert result.status_code == status


@pytest.mark.parametrize("token", ["reviewer-test", "admin-test"])
def test_review_creates_new_version_not_overwrite(client, service, token):
    event = seed(service, ownership="unknown")
    response = client.post(f"/api/v1/events/{event.event_id}/review", headers={"x-agrogami-token": token},
        json={"changes": {"ownership": "external"}, "reason": "synthetic ownership verified", "reviewer_alias": "reviewer-demo"})
    assert response.status_code == 200
    assert response.json()["supersedes_event_id"] == str(event.event_id)
    assert response.json()["validation_status"] == "ACCEPTED"
    assert service.store.get(CanonicalEvent, event.event_id) == event


def test_feature_route_calls_core_with_unknown_coverage(client, service):
    event = seed(service)
    response = client.get(f"/api/v1/applicants/{APPLICANT}/features", params={"scoring_time": T0.isoformat()})
    assert response.status_code == 200
    features = response.json()["30"]["features"]
    assert features["external_inflow_total"]["value"] == "100"
    assert features["liquidity_floor"]["value"] is None
    assert features["coverage_days"]["value"] == 0


def test_assessment_insufficient_not_low_score_and_immutable(client, service):
    seed(service)
    payload = {"applicant_id": str(APPLICANT), "assessment_time": T0.isoformat(), "coverage": coverage().model_dump(mode="json")}
    response = client.post("/api/v1/assessments", headers=REVIEWER, json=payload)
    assert response.status_code == 201
    record = response.json()
    assert record["status"] == "INSUFFICIENT_EVIDENCE"
    assert record["display_score"] is None
    assert record["calibrated_probability"] is None
    key = record["assessment_id"]
    assert client.get(f"/api/v1/assessments/{key}").json() == record
    assert "INSUFFICIENT_EVIDENCE" in {r["code"] for r in client.get(f"/api/v1/assessments/{key}/explanation").json()["reasons"]}
    existing = service.records.get(AssessmentSnapshot, UUID(key))
    with pytest.raises(IntegrityError):
        service.records.save(existing)


def test_pending_evidence_status(client, service):
    seed(service, ownership="unknown", validation_status="NEEDS_REVIEW")
    record = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage(complete=True))
    assert record.status == SnapshotStatus.NEEDS_REVIEW
    assert record.display_score is None


def test_correction_new_assessment_preserves_old_snapshot(service):
    event = seed(service)
    first = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage())
    corrected = service.review(event.event_id, {"amount": "150"}, "synthetic change", "reviewer-demo")
    later = corrected.created_at + timedelta(seconds=1)
    second = service.assessment(applicant_id=APPLICANT, t0=later,
        coverage=Coverage(applicant_id=APPLICANT, known_at=corrected.created_at), previous_id=first.assessment_id)
    assert second.assessment_id != first.assessment_id
    assert second.supersedes_assessment_id == first.assessment_id
    assert corrected.event_id in second.evidence_version_ids
    assert service.records.get(AssessmentSnapshot, first.assessment_id) == first


def test_synthetic_risk_calibration_assessment_is_illustrative(service):
    data = RiskDataset(identity=DatasetIdentity(dataset_id="SYNTHETIC-risk", target_definition="Invented labels", scope="synthetic", limitations=()),
        sample_ids=tuple(f"train-{i}" for i in range(12)), feature_names=("external_inflow_total",),
        values=tuple((float(i * 20),) for i in range(12)), labels=tuple(int(i >= 6) for i in range(12)))
    model = LogisticRiskModel.fit(data, scope=S.SYNTHETIC_DEMO, version="synthetic-v1")
    calibrator = Calibrator.fit([.1, .2, .8, .9], [0, 0, 1, 1], [f"cal-{i}" for i in range(4)],
        model=model.artifact, dataset_id="SYNTHETIC-risk", version="synthetic-cal")
    service.model, service.calibrator = model, calibrator
    seed(service)
    record = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage(complete=True))
    assert record.status == SnapshotStatus.ILLUSTRATIVE
    assert 300 <= record.display_score <= 850
    assert record.raw_probability is not None and record.calibrated_probability is not None


def test_fairness_route_restricted_and_separate_from_evaluation(client, service):
    report = fairness_metrics([0, 1], [0, 1], ["SYNTHETIC-A", "SYNTHETIC-B"], positive_label_definition="test")
    run = EvaluationRun(dataset_id="SYNTHETIC", scope="SYNTHETIC_DEMO", metrics={"brier": .01}, fairness=report, limitations=("test only",))
    service.records.save(run)
    assert client.get(f"/api/v1/evaluations/{run.run_id}").json()["fairness"] is None
    assert client.get(f"/api/v1/evaluations/{run.run_id}/fairness").status_code == 403
    assert client.get(f"/api/v1/evaluations/{run.run_id}/fairness", headers=REVIEWER).status_code == 200


def test_source_metadata_redacts_private_path(client, service):
    source = fixture_sources([fixture_event("metadata")])[0]
    source = Source.model_validate(source.model_dump() | {"metadata": {"private_path": str(service.private_dir)}})
    service.store.save(source)
    result = client.get(f"/api/v1/sources/{source.source_id}")
    assert str(service.private_dir) not in result.text


def test_missing_records_404(client):
    key = uuid4()
    for path in (f"jobs/{key}", f"sources/{key}", f"assessments/{key}", f"evaluations/{key}"):
        assert client.get("/api/v1/" + path).status_code == 404


def test_optional_document_adapters_only_persist_candidates(service):
    from agrogami.extraction.documents import TrOCRAdapter, LayoutLMv3Adapter
    from agrogami.extraction.bio import LABELS
    from PIL import ImageDraw
    service.trocr = TrOCRAdapter(lambda image: "SYNTHETIC 100", "fake-v1")
    service.layout = LayoutLMv3Adapter(lambda image, words, boxes: [[10 if l == "B-AMOUNT" else -10 for l in LABELS] for _ in words], "fake-v1")
    image = Image.new("RGB", (160, 80), "white")
    ImageDraw.Draw(image).rectangle((10, 10, 100, 20), fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    job = service.document_intake(applicant_id=APPLICANT, content=buffer.getvalue(), deskew_degrees=0)
    assert job.status == "NEEDS_REVIEW"
    assert len(job.candidate_ids) == 2
    assert not service.store.events(APPLICANT)


def test_public_benchmark_scoring_withheld(service):
    from agrogami.risk.models import ModelArtifact
    artifact = ModelArtifact(version="public-test", algorithm="regularized_logistic", scope=S.PUBLIC_DATASET_BENCHMARK,
        dataset_id="public-test", target_definition="Original public target", feature_names=("external_inflow_total",))
    model = LogisticRiskModel(artifact, [0], 0, [0], [1])
    calibrator = Calibrator.fit([.1, .2, .8, .9], [0, 0, 1, 1], [f"cal-{i}" for i in range(4)],
        model=model.artifact, dataset_id="public-test", version="public-cal")
    service.model, service.calibrator = model, calibrator
    seed(service)
    record = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage(complete=True))
    assert record.status == SnapshotStatus.ILLUSTRATIVE
    assert record.display_score is None


def test_model_calibrator_mismatch_rejected(service):
    from agrogami.risk.models import ModelArtifact
    artifact = ModelArtifact(version="test", algorithm="regularized_logistic", scope=S.SYNTHETIC_DEMO,
        dataset_id="SYNTHETIC", target_definition="Invented", feature_names=("external_inflow_total",))
    model = LogisticRiskModel(artifact, [0], 0, [0], [1])
    calibrator = Calibrator.fit([.1, .2, .8, .9], [0, 0, 1, 1], [f"cal-{i}" for i in range(4)],
        model=model.artifact, dataset_id="SYNTHETIC", version="cal")
    other = ModelArtifact.model_validate(artifact.model_dump() | {"artifact_id": uuid4()})
    service.model = LogisticRiskModel(other, [0], 0, [0], [1])
    service.calibrator = calibrator
    seed(service)
    with pytest.raises(ValueError):
        service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage(complete=True))


def test_unsupported_candidate_requires_explicit_reviewed_facts(client, service):
    from agrogami.schemas import CandidateExtraction, Provenance
    payload = sms_payload(text="unsupported ambiguous source")
    job = client.post("/api/v1/intake/sms", json=payload).json()
    original = service.store.get(CandidateExtraction, UUID(job["candidate_id"]))
    source = service.store.get(Source, UUID(job["source_id"]))
    event = fixture_event("reviewed-candidate", account_id=UUID(payload["account_id"]), source_id=source.source_id,
        source_type=source.source_type, source_provenance=Provenance(source_hash=source.source_hash, span_start=0, span_end=26,
                                                                  template="manual-corroborated", provider=payload["provider"]),
        provider=payload["provider"])
    body = {"event": event.model_dump(mode="json"), "reason": "Synthetic manual corroboration", "reviewer_alias": "reviewer-demo"}
    assert client.post(f"/api/v1/candidates/{job['candidate_id']}/review", json=body).status_code == 403
    response = client.post(f"/api/v1/candidates/{job['candidate_id']}/review", json=body, headers=REVIEWER)
    assert response.status_code == 201
    assert response.json()["reviewed"]
    assert service.store.get(CandidateExtraction, original.candidate_id) == original
    assert client.post(f"/api/v1/candidates/{job['candidate_id']}/review", json=body, headers=REVIEWER).status_code == 409


def test_storage_errors_never_expose_private_paths(client, service, monkeypatch):
    def unavailable(**kwargs):
        raise OSError(f"cannot write {service.private_dir}")
    monkeypatch.setattr(service, "sms_intake", unavailable)
    result = client.post("/api/v1/intake/sms", json=sms_payload())
    assert result.status_code == 503
    assert str(service.private_dir) not in result.text


def test_assessment_unknown_required_feature_withholds_score(service):
    from agrogami.risk.models import ModelArtifact
    artifact = ModelArtifact(version="test", algorithm="regularized_logistic", scope=S.SYNTHETIC_DEMO,
        dataset_id="SYNTHETIC", target_definition="Invented", feature_names=("liquidity_floor",))
    model = LogisticRiskModel(artifact, [0], 0, [0], [1])
    calibrator = Calibrator.fit([.1, .2, .8, .9], [0, 0, 1, 1], [f"cal-{i}" for i in range(4)],
        model=model.artifact, dataset_id="SYNTHETIC", version="cal")
    service.model, service.calibrator = model, calibrator
    seed(service)
    result = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage(complete=True))
    assert result.display_score is None
    assert result.raw_probability is None
    assert result.status == SnapshotStatus.INSUFFICIENT_EVIDENCE


def test_typed_snapshot_cannot_claim_score_for_unknown_evidence(service):
    result = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage())
    with pytest.raises(ValueError):
        AssessmentSnapshot.model_validate(result.model_dump() | {"display_score": 300})


def test_default_api_startup_uses_config_without_loading_models(tmp_path, monkeypatch):
    monkeypatch.setenv("AGROGAMI_DATABASE_URL", "sqlite:///" + str(tmp_path / "startup.db"))
    monkeypatch.setenv("AGROGAMI_PRIVATE_DATA_DIR", str(tmp_path / "private"))
    monkeypatch.setenv("AGROGAMI_DEMO_TOKENS", "{}")
    application = create_app()
    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert application.state.service.model is None
        assert application.state.service.trocr is None
        assert application.state.service.layout is None
        assert client.get("/api/openapi.json").status_code == 200


def test_review_automatically_appends_new_assessment_without_mutating_previous(service):
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from agrogami.application import BackendRecord
    event = seed(service)
    previous = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage())
    corrected = service.review(event.event_id, {"amount": "150"}, "synthetic correction", "reviewer-demo")
    with Session(service.store.engine) as session:
        rows = session.scalars(select(BackendRecord).where(BackendRecord.kind == "assessment_snapshot")).all()
    records = [AssessmentSnapshot.model_validate_json(row.payload) for row in rows]
    assert len(records) == 2
    current = next(record for record in records if record.assessment_id != previous.assessment_id)
    assert current.supersedes_assessment_id == previous.assessment_id
    assert corrected.event_id in current.evidence_version_ids
    assert current.display_score is None
    assert service.records.get(AssessmentSnapshot, previous.assessment_id) == previous


def test_api_assessment_history_exposes_new_review_snapshot(client, service):
    event = seed(service)
    response = client.post(f"/api/v1/events/{event.event_id}/review", headers=REVIEWER,
        json={"changes": {"amount": "150"}, "reason": "synthetic correction", "reviewer_alias": "reviewer-demo"})
    assert response.status_code == 200
    history = client.get(f"/api/v1/applicants/{APPLICANT}/assessments").json()
    assert len(history) == 1
    assert history[0]["status"] == "NEEDS_REVIEW"
    assert history[0]["display_score"] is None
