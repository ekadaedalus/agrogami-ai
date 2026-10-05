"""Synthetic deployment authorization and applicant isolation regressions."""
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agrogami.api.app import Role, create_app
from agrogami.application import ApplicationService
from agrogami.config import Settings
from agrogami.fixtures import APPLICANT, ACCOUNT, T0, coverage
from agrogami.mcp.server import create_prism
from agrogami.storage import Store
from agrogami.ui.samples import sample_sms


TOKENS = {"synthetic-view": Role.viewer, "synthetic-review": Role.reviewer, "synthetic-admin": Role.admin}


def headers(role):
    return {"X-Agrogami-Token": "synthetic-" + role} if role else {}


def sms(applicant=APPLICANT):
    return {"applicant_id": str(applicant), "account_id": str(ACCOUNT),
            "text": sample_sms("External inflow"), "provider": "SYNTHETIC-bKash-like"}


@pytest.fixture
def service(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "synthetic.db"))
    yield ApplicationService(store, tmp_path / "sources")
    store.engine.dispose()


@pytest.fixture
def deployment(monkeypatch):
    monkeypatch.setenv("AGROGAMI_LOCAL_DEMO_MODE", "false")
    monkeypatch.setenv("AGROGAMI_APPLICANT_GRANTS", json.dumps({
        "synthetic-view": [str(APPLICANT)], "synthetic-review": [str(APPLICANT)]}))


@pytest.mark.parametrize("suffix", ["events", "features?scoring_time=" + T0.isoformat().replace("+", "%2B"), "assessments"])
def test_deployment_anonymous_applicant_reads_rejected(service, deployment, suffix):
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        assert client.get(f"/api/v1/applicants/{APPLICANT}/{suffix}").status_code == 401


@pytest.mark.parametrize("kind", ["jobs", "sources", "assessments", "candidates", "evaluations"])
def test_deployment_anonymous_resource_reads_rejected_before_lookup(service, deployment, kind):
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        assert client.get(f"/api/v1/{kind}/{uuid4()}").status_code == 401


@pytest.mark.parametrize("role,expected", [(None, 401), ("invalid", 401), ("view", 403), ("review", 201), ("admin", 201)])
def test_deployment_intake_requires_write_role(service, deployment, role, expected):
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        assert client.post("/api/v1/intake/sms", json=sms(), headers=headers(role)).status_code == expected


@pytest.mark.parametrize("role,expected", [(None, 401), ("view", 403), ("review", 200), ("admin", 200)])
def test_deployment_correction_capability(service, deployment, role, expected):
    job = service.sms_intake(**(sms() | {"applicant_id": APPLICANT, "account_id": ACCOUNT}))
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        result = client.post(f"/api/v1/events/{job.event_id}/review", headers=headers(role), json={
            "changes": {"ownership": "external"}, "reason": "Synthetic corroboration", "reviewer_alias": "reviewer-synthetic"})
        assert result.status_code == expected


def test_deployment_resource_ids_do_not_bypass_applicant_grants(service, deployment):
    other = uuid4()
    job = service.sms_intake(**(sms(other) | {"applicant_id": other, "account_id": ACCOUNT}))
    snapshot = service.assessment(applicant_id=other, t0=T0,
        coverage=coverage().model_copy(update={"applicant_id": other}))
    paths = [f"jobs/{job.job_id}", f"sources/{job.source_id}", f"candidates/{job.candidate_id}",
             f"applicants/{other}/events", f"assessments/{snapshot.assessment_id}",
             f"assessments/{snapshot.assessment_id}/explanation", f"applicants/{other}/assessments"]
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        for path in paths:
            assert client.get("/api/v1/" + path, headers=headers("review")).status_code == 403
            assert client.get("/api/v1/" + path, headers=headers("admin")).status_code == 200
        assert client.post("/api/v1/intake/sms", json=sms(other), headers=headers("review")).status_code == 403
        assert client.post(f"/api/v1/events/{job.event_id}/review", headers=headers("review"), json={
            "changes": {"ownership": "external"}, "reason": "Synthetic", "reviewer_alias": "reviewer-synthetic"}).status_code == 403


def test_deployment_nonadmin_without_grants_is_denied(service, deployment, monkeypatch):
    monkeypatch.setenv("AGROGAMI_APPLICANT_GRANTS", "{}")
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        assert client.get(f"/api/v1/applicants/{APPLICANT}/events", headers=headers("review")).status_code == 403


def test_explicit_local_demo_allows_only_synthetic_anonymous_intake(service, monkeypatch):
    monkeypatch.setenv("AGROGAMI_LOCAL_DEMO_MODE", "true")
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        assert client.post("/api/v1/intake/sms", json=sms()).status_code == 201
        real = sms() | {"text": "Unmarked evidence awaiting annotation"}
        assert client.post("/api/v1/intake/sms", json=real).status_code == 403
        assert client.post("/api/v1/intake/sms", json=real, headers=headers("review")).status_code == 201


def test_default_configuration_requires_credentials(monkeypatch):
    monkeypatch.delenv("AGROGAMI_LOCAL_DEMO_MODE", raising=False)
    assert Settings(_env_file=None).local_demo_mode is False


@pytest.mark.parametrize("environment", ["production", "deployment", "public"])
def test_deployment_environment_rejects_local_anonymous_mode(environment):
    with pytest.raises(ValueError, match="local demo"):
        Settings(_env_file=None, env=environment, local_demo_mode=True)


def test_assessment_predecessor_cannot_cross_applicants(service, deployment):
    other = uuid4()
    previous = service.assessment(applicant_id=other, t0=T0,
        coverage=coverage().model_copy(update={"applicant_id": other}))
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        result = client.post("/api/v1/assessments", headers=headers("review"), json={
            "applicant_id": str(APPLICANT), "assessment_time": T0.isoformat(),
            "coverage": coverage().model_dump(mode="json"),
            "supersedes_assessment_id": str(previous.assessment_id)})
        assert result.status_code in {403, 422}
        assert not service.records.assessments(APPLICANT)


def test_local_anonymous_cannot_read_private_applicant_resources(service, monkeypatch):
    from agrogami.fixtures import fixture_event, fixture_sources
    monkeypatch.setenv("AGROGAMI_LOCAL_DEMO_MODE", "true")
    event = fixture_event("private-authorization-regression")
    source = fixture_sources([event])[0].model_copy(update={"synthetic": False})
    service.store.save(source)
    service.store.save(event)
    snapshot = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage())
    paths = [f"sources/{source.source_id}", f"applicants/{APPLICANT}/events",
             f"applicants/{APPLICANT}/features?scoring_time={T0.isoformat().replace('+', '%2B')}",
             f"applicants/{APPLICANT}/assessments", f"assessments/{snapshot.assessment_id}",
             f"assessments/{snapshot.assessment_id}/explanation"]
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        for path in paths:
            assert client.get("/api/v1/" + path).status_code == 403
            assert client.get("/api/v1/" + path, headers=headers("review")).status_code == 200


@pytest.mark.parametrize("role,expected", [(None, 401), ("invalid", 401), ("view", 403), ("review", 201), ("admin", 201)])
def test_deployment_assessment_creation_requires_write_role(service, deployment, role, expected):
    with TestClient(create_app(service, tokens=TOKENS)) as client:
        result = client.post("/api/v1/assessments", headers=headers(role), json={
            "applicant_id": str(APPLICANT), "assessment_time": T0.isoformat(),
            "coverage": coverage().model_dump(mode="json")})
        assert result.status_code == expected


def test_deployment_ui_uses_only_server_api_destination(monkeypatch, deployment):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("AGROGAMI_API_URL", "http://127.0.0.1:8000")
    app = AppTest.from_file(Path("src/agrogami/ui/app.py").resolve(), default_timeout=15).run()
    assert not app.exception
    assert "API URL" not in {field.label for field in app.sidebar.text_input}


def test_prism_deployment_respects_applicant_grants(service, deployment, monkeypatch):
    monkeypatch.setenv("AGROGAMI_DEMO_TOKENS", json.dumps(TOKENS))
    settings = Settings(_env_file=None, mcp_enabled=True)
    _, application = create_prism(service, settings)
    other = uuid4()
    snapshot = service.assessment(applicant_id=other, t0=T0,
        coverage=coverage().model_copy(update={"applicant_id": other}))
    with TestClient(application, base_url="http://127.0.0.1:8001") as client:
        def call(name, arguments, role="review"):
            return client.post("/mcp", headers={"Authorization": "Bearer synthetic-" + role,
                "Accept": "application/json, text/event-stream"}, json={"jsonrpc": "2.0", "id": 1,
                "method": "tools/call", "params": {"name": name, "arguments": arguments}}).json()["result"]
        assert not call("get_evidence_ledger", {"applicant_id": str(APPLICANT)}, "view").get("isError", False)
        for name, arguments in [("get_evidence_ledger", {"applicant_id": str(other)}),
                                ("get_assessment_snapshot", {"assessment_id": str(snapshot.assessment_id)}),
                                ("get_explanation_factors", {"assessment_id": str(snapshot.assessment_id)})]:
            assert call(name, arguments)["isError"]
            assert not call(name, arguments, "admin").get("isError", False)
