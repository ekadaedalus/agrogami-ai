"""Repository-owned synthetic preparation and isolated runtime regression coverage."""
from datetime import datetime, timezone
from decimal import Decimal
import importlib
import json
from pathlib import Path
import socket
from uuid import UUID

import pytest

from agrogami.application import ApplicationService
from agrogami.assessment import AssessmentSnapshot
from agrogami.mcp.server import Gateway
from agrogami.schemas import CanonicalEvent, CandidateExtraction, FeatureSnapshot, Source
from agrogami.storage import Store


def test_prepare_demo_preserves_synthetic_review_history_and_withheld_assessment(tmp_path, monkeypatch):
    preparation = importlib.import_module("scripts.prepare_demo")
    monkeypatch.setattr(preparation, "DEMO_ROOT", tmp_path / "synthetic_demo")
    before = datetime.now(timezone.utc)
    manifest = preparation.prepare_demo()
    after = datetime.now(timezone.utc)
    assert manifest["scope"] == "SYNTHETIC_DEMO"
    assert before <= datetime.fromisoformat(manifest["created_at"]) <= after
    for name in ("scenario_id", "applicant_id", "source_id", "candidate_id", "original_event_id",
                 "accepted_event_id", "current_event_id", "assessment_id"):
        assert UUID(manifest[name]).version == 4
    assert manifest["accepted_event_id"] == manifest["current_event_id"]
    directory = preparation.DEMO_ROOT / manifest["scenario_id"]
    assert json.loads((directory / "manifest.json").read_text(encoding="utf-8")) == manifest
    store = Store("sqlite:///" + (directory / "scenario.db").as_posix())
    try:
        service = ApplicationService(store, directory / "private")
        source = store.get(Source, UUID(manifest["source_id"]))
        assert source.synthetic
        assert before <= source.ingestion_timestamp <= after
        candidate = store.get(CandidateExtraction, UUID(manifest["candidate_id"]))
        assert candidate.source_id == source.source_id
        assert candidate.fields["amount"].normalized_value == "100.00"
        original = store.get(CanonicalEvent, UUID(manifest["original_event_id"]))
        current = store.get(CanonicalEvent, UUID(manifest["current_event_id"]))
        assert original.validation_status == "NEEDS_REVIEW"
        assert original.ownership == "unknown"
        assert current.validation_status == "ACCEPTED" and current.reviewed
        assert current.ownership == "external" and current.amount == Decimal("100.00")
        assert current.supersedes_event_id == original.event_id
        assert store.history(current.event_id) == [original, current]
        assert len(store.corrections(original.event_id)) == 1
        assert set(manifest["feature_snapshot_ids"]) == {"30", "60", "90"}
        for window, identifier in manifest["feature_snapshot_ids"].items():
            features = store.get(FeatureSnapshot, UUID(identifier))
            assert features.window_days == int(window)
            inflow = features.features["external_inflow_total"]
            assert inflow.value == Decimal("100.00")
            assert inflow.contributing_event_ids == (current.event_id,)
            assert features.features["payment_punctuality"].value is None
        assessment = service.records.get(AssessmentSnapshot, UUID(manifest["assessment_id"]))
        assert assessment.status == "INSUFFICIENT_EVIDENCE"
        assert assessment.model_validation_scope == "UNTRAINED"
        assert assessment.display_score is assessment.raw_probability is assessment.calibrated_probability is None
        explanation = Gateway(service).explanation(assessment.assessment_id)
        assert explanation["reasons"] and explanation["limitations"]
        history = service.records.assessments(UUID(manifest["applicant_id"]))
        assert len(history) == 2
        assert history[0].status == "NEEDS_REVIEW" and history[0].display_score is None
        assert assessment.supersedes_assessment_id == history[0].assessment_id
        assert store.get(CandidateExtraction, candidate.candidate_id) == candidate
    finally:
        store.engine.dispose()


def test_prepare_demo_rerun_isolated_from_existing_data_and_environment(tmp_path, monkeypatch):
    preparation = importlib.import_module("scripts.prepare_demo")
    monkeypatch.setattr(preparation, "DEMO_ROOT", tmp_path / "synthetic_demo")
    private = tmp_path / "existing-private-data"
    private.mkdir()
    sentinel = private / "evidence.bin"
    sentinel.write_bytes(b"unchanged private-data sentinel")
    monkeypatch.setenv("AGROGAMI_DATABASE_URL", "sqlite:///" + (private / "must-not-open.db").as_posix())
    monkeypatch.setenv("DATABASE_URL", "sqlite:///" + (private / "also-must-not-open.db").as_posix())
    monkeypatch.setenv("AGROGAMI_PRIVATE_DATA_DIR", str(private))
    monkeypatch.setenv("AGROGAMI_RISK_MODEL_PATH", str(private / "missing-model.json"))
    monkeypatch.setenv("AGROGAMI_ENABLE_REAL_MODELS", "true")
    first = preparation.prepare_demo()
    first_dir = preparation.DEMO_ROOT / first["scenario_id"]
    recorded = {path.relative_to(first_dir): path.read_bytes() for path in first_dir.rglob("*") if path.is_file()}
    second = preparation.prepare_demo()
    assert first["scenario_id"] != second["scenario_id"]
    assert first["applicant_id"] != second["applicant_id"]
    assert {path.relative_to(first_dir): path.read_bytes() for path in first_dir.rglob("*") if path.is_file()} == recorded
    assert list(private.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"unchanged private-data sentinel"
    # There is no caller-selected database/output path that could target existing evidence.
    with pytest.raises(TypeError):
        preparation.prepare_demo(private)


def test_runtime_ports_allow_independent_ephemeral_selection_and_reject_occupied_port():
    runtime = importlib.import_module("scripts.verify_local_runtime")
    ports = runtime.select_ports((0, 0, 0))
    assert len(set(ports)) == 3 and all(0 < port <= 65535 for port in ports)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        occupied = listener.getsockname()[1]
        with pytest.raises(ValueError, match="port"):
            runtime.select_ports((occupied, 0, 0))
    with pytest.raises(ValueError, match="port"):
        runtime.select_ports((-1, 0, 0))


def test_runtime_environment_cannot_inherit_private_databases_or_models(tmp_path, monkeypatch):
    runtime = importlib.import_module("scripts.verify_local_runtime")
    for name in ("AGROGAMI_DATABASE_URL", "DATABASE_URL", "AGROGAMI_PRIVATE_DATA_DIR",
                 "AGROGAMI_RISK_MODEL_PATH", "AGROGAMI_CALIBRATOR_PATH", "AGROGAMI_DEBERTA_CHECKPOINT",
                 "AGROGAMI_TROCR_CHECKPOINT", "AGROGAMI_LAYOUTLMV3_CHECKPOINT", "AGROGAMI_APPLICANT_GRANTS"):
        monkeypatch.setenv(name, "must-not-be-used")
    env = runtime.runtime_environment(tmp_path, "synthetic-test-credential", (18000, 18501, 18001))
    assert "DATABASE_URL" not in env
    assert not any(name in env for name in ("AGROGAMI_RISK_MODEL_PATH", "AGROGAMI_CALIBRATOR_PATH",
        "AGROGAMI_DEBERTA_CHECKPOINT", "AGROGAMI_TROCR_CHECKPOINT", "AGROGAMI_LAYOUTLMV3_CHECKPOINT"))
    assert env["AGROGAMI_DATABASE_URL"] == "sqlite:///" + (tmp_path / "runtime.db").as_posix()
    assert env["AGROGAMI_PRIVATE_DATA_DIR"] == str(tmp_path / "private")
    assert env["AGROGAMI_LOCAL_DEMO_MODE"] == "true"
    assert env["AGROGAMI_ENABLE_REAL_MODELS"] == "false"
    assert env["AGROGAMI_API_URL"] == "http://127.0.0.1:18000"
    assert env["AGROGAMI_MCP_PORT"] == "18001"
    assert json.loads(env["AGROGAMI_APPLICANT_GRANTS"]) == {}


def test_runtime_cli_accepts_configurable_ports():
    runtime = importlib.import_module("scripts.verify_local_runtime")
    args = runtime.parse_args(["--api-port", "0", "--ui-port", "18501", "--mcp-port", "18001"])
    assert (args.api_port, args.ui_port, args.mcp_port) == (0, 18501, 18001)
