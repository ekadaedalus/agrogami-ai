from pathlib import Path
from uuid import uuid4
import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from agrogami.api.app import create_app, Role
from agrogami.application import ApplicationService, EvaluationRun
from agrogami.config import Settings
from agrogami.storage import Store
from agrogami.fixtures import APPLICANT, fixture_event, fixture_sources, coverage, T0
from agrogami.ui.api_client import APIClient, ClientError
from agrogami.ui.samples import sample_sms, SCENARIOS
from agrogami.ui.formatting import display
from agrogami.mcp.server import create_prism, Gateway
from agrogami.fairness.metrics import fairness_metrics

@pytest.fixture
def service(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "product.db"))
    service = ApplicationService(store, tmp_path / "private")
    yield service
    store.engine.dispose()

def seed(service):
    event = fixture_event("product")
    service.store.save(fixture_sources([event])[0])
    service.store.save(event)
    return event

def test_end_to_end_http_client_correction_and_immutable_history(service):
    from scripts.smoke_test import run
    with TestClient(create_app(service, tokens={"test-review": Role.reviewer})) as transport:
        result = run(APIClient("http://testserver", "test-review", transport))
    assert result["status"] == "passed"

def test_docs_ready_and_private_candidate_authorization(service):
    with TestClient(create_app(service, tokens={"review": Role.reviewer})) as client:
        docs = client.get("/docs")
        assert docs.status_code == 200 and "Research Prototype" in docs.text
        assert "Canonical" in docs.text and "Prism" in docs.text
        assert client.get("/api/docs").status_code == 200
        assert client.get("/ready").json()["optional_models"]["trocr"] is False
        assert client.get(f"/api/v1/candidates/{uuid4()}").status_code == 403

@pytest.mark.parametrize("scenario", SCENARIOS)
def test_synthetic_sample_intake(service, scenario):
    job = service.sms_intake(applicant_id=APPLICANT, account_id=uuid4(),
        text=sample_sms(scenario), provider="SYNTHETIC-bKash-like")
    assert job.event_id is not None
    assert job.status == "NEEDS_REVIEW"

def test_ui_unknowns_are_not_zero():
    assert "Unavailable" in display(None)
    assert display(0) == "0"
    assert "coverage_missing" in display(None, ("coverage_missing",))

def test_synthetic_document_scope_preserved_and_filenames_not_accepted(service):
    import base64
    from io import BytesIO
    from PIL import Image
    from agrogami.schemas import Source
    buffer = BytesIO()
    Image.new("RGB", (80, 80), "white").save(buffer, "PNG")
    with TestClient(create_app(service)) as client:
        body = {"applicant_id": str(APPLICANT), "content_base64": base64.b64encode(buffer.getvalue()).decode(), "synthetic": True}
        response = client.post("/api/v1/intake/document", json=body)
        assert response.status_code == 201
        source = service.store.get(Source, response.json()["source_id"])
        assert source.synthetic
        assert client.post("/api/v1/intake/document", json=body | {"filename": "../../private.env"}).status_code == 422

def test_project_docs_escape_uploaded_html_and_deny_path_selection(tmp_path):
    from fastapi import FastAPI
    from agrogami.api.project_docs import router
    (tmp_path / "PRD.md").write_text('<script>alert("secret")</script>', encoding="utf-8")
    app = FastAPI(docs_url=None)
    app.include_router(router(tmp_path))
    with TestClient(app) as client:
        response = client.get("/docs?path=../../.env")
        assert "<script>" not in response.text
        assert "&lt;script&gt;" in response.text

def test_ui_overview_and_invalid_identifier_no_traceback():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(Path("src/agrogami/ui/app.py").resolve(), default_timeout=10).run()
    assert not app.exception
    assert "Research Prototype" in app.title[0].value
    app.sidebar.text_input[2].set_value("invalid").run()
    assert not app.exception
    assert app.error

def test_client_error_does_not_echo_response_body(service):
    with TestClient(create_app(service)) as transport:
        client = APIClient("http://testserver", transport=transport)
        with pytest.raises(ClientError, match="Reviewer/admin"):
            client.candidate(uuid4())

def test_prism_minimized_ledger_and_no_mutation(service):
    event = seed(service)
    ledger = Gateway(service).ledger(APPLICANT)
    assert ledger["events"][0]["event_id"] == str(event.event_id)
    assert "counterparty" not in ledger["events"][0]
    assert "account_id" not in ledger["events"][0]
    assert service.store.events(APPLICANT) == [event]

def test_prism_requires_explicit_enablement_and_credentials(service):
    with pytest.raises(ValueError, match="disabled"):
        create_prism(service, Settings(_env_file=None, mcp_enabled=False))
    with pytest.raises(ValueError, match="credentials"):
        create_prism(service, Settings(_env_file=None, mcp_enabled=True, demo_tokens={}))

def test_sdk_diagnostics_do_not_log_untrusted_arguments(service, caplog):
    import logging
    create_prism(service, Settings(_env_file=None, mcp_enabled=True, mcp_auth_token="test-token"))
    with caplog.at_level(logging.WARNING):
        logging.getLogger("mcp.server.lowlevel.server").warning("Unknown tool raw-phone-01700000000 secret-token")
    assert "01700000000" not in caplog.text
    assert "secret-token" not in caplog.text
    assert "mcp_protocol" in caplog.text

@pytest.mark.parametrize("page", ["Overview", "Intake / Samples", "Evidence Review", "Event Ledger", "Feature Summary",
    "Assessment", "Explanation", "Evaluation / Fairness", "Audit / Versions", "Documentation"])
def test_ui_pages_use_backend_without_tracebacks(service, monkeypatch, page):
    from streamlit.testing.v1 import AppTest
    seed(service)
    snapshot = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage())
    original = APIClient.__init__
    with TestClient(create_app(service, tokens={"review": Role.reviewer})) as transport:
        def initialize(self, base_url, token="", **kwargs):
            original(self, base_url, token, transport)
        monkeypatch.setattr(APIClient, "__init__", initialize)
        app = AppTest.from_file(Path("src/agrogami/ui/app.py").resolve(), default_timeout=10)
        app.session_state["applicant"] = str(APPLICANT)
        app.session_state["assessment_id"] = str(snapshot.assessment_id)
        app.run()
        app.sidebar.text_input[1].set_value("review")
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
        assert not app.error

def test_ui_full_synthetic_review_assessment_workflow(service, monkeypatch):
    from streamlit.testing.v1 import AppTest
    original = APIClient.__init__
    with TestClient(create_app(service, tokens={"review": Role.reviewer})) as transport:
        def initialize(self, base_url, token="", **kwargs):
            original(self, base_url, token, transport)
        monkeypatch.setattr(APIClient, "__init__", initialize)
        app = AppTest.from_file(Path("src/agrogami/ui/app.py").resolve(), default_timeout=10).run()
        app.sidebar.text_input[1].set_value("review")
        app.sidebar.radio[0].set_value("Intake / Samples").run()
        app.button[0].click().run()
        assert not app.exception and app.session_state["job"]["candidate_id"]
        app.sidebar.radio[0].set_value("Evidence Review").run()
        app.button[0].click().run()
        assert not app.exception and not app.error
        app.sidebar.radio[0].set_value("Feature Summary").run()
        assert not app.exception and len(app.dataframe) == 3
        app.sidebar.radio[0].set_value("Assessment").run()
        app.button[0].click().run()
        assert not app.exception and app.session_state["assessment_id"]
        app.sidebar.radio[0].set_value("Explanation").run()
        assert not app.exception
        app.sidebar.radio[0].set_value("Audit / Versions").run()
        assert not app.exception and app.json

def test_prism_streamable_http_protocol_four_tools_auth_and_fairness(service):
    seed(service)
    snapshot = service.assessment(applicant_id=APPLICANT, t0=T0, coverage=coverage())
    report = fairness_metrics([0, 1, 0, 1], [0, 1, 0, 1], ["SYNTHETIC-A"] * 4, positive_label_definition="synthetic")
    run = EvaluationRun(dataset_id="SYNTHETIC", scope="SYNTHETIC_DEMO", metrics={}, fairness=report, limitations=("Synthetic only",))
    service.records.save(run)
    settings = Settings(_env_file=None, mcp_enabled=True, mcp_auth_token="view", demo_tokens={"review": "reviewer"})
    server, application = create_prism(service, settings)
    headers = {"Authorization": "Bearer view", "Accept": "application/json, text/event-stream"}
    with TestClient(application, base_url="http://127.0.0.1:8001") as client:
        assert client.post("/mcp", json={}).status_code == 401
        response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "internal-test", "version": "1"}}})
        assert response.status_code == 200, response.text
        assert "result" in response.json()
        def call(method, params, token="view"):
            response = client.post("/mcp", headers=headers | {"Authorization": "Bearer " + token},
                json={"jsonrpc": "2.0", "id": 2, "method": method, "params": params})
            assert response.status_code == 200, response.text
            return response.json()["result"]
        tools = call("tools/list", {})["tools"]
        assert {t["name"] for t in tools} == {"get_evidence_ledger", "get_assessment_snapshot", "get_explanation_factors", "get_fairness_audit"}
        for name, arguments in [("get_evidence_ledger", {"applicant_id": str(APPLICANT)}),
                                ("get_assessment_snapshot", {"assessment_id": str(snapshot.assessment_id)}),
                                ("get_explanation_factors", {"assessment_id": str(snapshot.assessment_id)})]:
            result = call("tools/call", {"name": name, "arguments": arguments})
            assert not result.get("isError", False), result
            assert str(service.private_dir) not in json.dumps(result)
        args = {"name": "get_fairness_audit", "arguments": {"run_id": str(run.run_id)}}
        assert call("tools/call", args)["isError"]
        assert not call("tools/call", args, "review").get("isError", False)
        assert call("tools/call", {"name": "correct_event", "arguments": {}})["isError"]
        for name, arguments in [("get_assessment_snapshot", {"assessment_id": str(uuid4())}),
                                ("get_explanation_factors", {"assessment_id": str(uuid4())}),
                                ("get_fairness_audit", {"run_id": str(uuid4())})]:
            result = call("tools/call", {"name": name, "arguments": arguments}, "review")
            assert result["isError"]
            assert str(service.private_dir) not in json.dumps(result)
        empty = call("tools/call", {"name": "get_evidence_ledger", "arguments": {"applicant_id": str(uuid4())}})
        assert not empty.get("isError", False)
