"""Permanent synthetic-only adversarial regressions; no external artifacts or downloads."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import runpy
import sys
from uuid import uuid4

import pytest

from agrogami.calibration.core import Calibrator
from agrogami.datasets import DatasetIdentity, RiskDataset, RESEARCH_TARGET
from agrogami.risk.models import LogisticRiskModel, ValidationScope as Scope


ROOT = Path(__file__).resolve().parents[1]
FEATURES = ("external_inflow_total",)


def synthetic_data(split: str) -> RiskDataset:
    return RiskDataset(identity=DatasetIdentity(dataset_id="SYNTHETIC-adversarial-governance",
        target_definition="Invented binary software-test label", scope="synthetic",
        limitations=("SYNTHETIC software verification only",)),
        sample_ids=tuple(f"SYNTHETIC-{split}-{i}" for i in range(8)), feature_names=FEATURES,
        values=tuple((float(i),) for i in range(8)), labels=(0, 0, 0, 0, 1, 1, 1, 1))


def run_script(monkeypatch, name: str, *arguments: object) -> None:
    monkeypatch.setattr(sys, "argv", [name, *map(str, arguments)])
    runpy.run_path(str(ROOT / "scripts" / name), run_name="__main__")


@pytest.fixture
def experiment(tmp_path, monkeypatch):
    paths = {}
    for split in ("training", "calibration", "test"):
        paths[split] = tmp_path / f"{split}.json"
        paths[split].write_text(synthetic_data(split).model_dump_json(), encoding="utf-8")
    output = tmp_path / "artifacts"
    run_script(monkeypatch, "train_risk.py", "--training", paths["training"],
        "--calibration", paths["calibration"], "--algorithm", "logistic", "--scope", "SYNTHETIC_DEMO",
        "--version", "SYNTHETIC-v1", "--output", output)
    return paths | {"model": output / "model.json", "calibrator": output / "calibrator.json",
                    "experiment": output / "experiment.json", "report": tmp_path / "report.json"}


def evaluate(monkeypatch, experiment) -> None:
    run_script(monkeypatch, "evaluate_risk.py", "--test-data", experiment["test"],
        "--model", experiment["model"], "--calibrator", experiment["calibrator"],
        "--output", experiment["report"])


def edit_json(path: Path, change) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    change(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("mismatch", ["dataset", "target", "scope", "features", "schema",
    "model_uuid", "model_version", "calibrator_uuid", "calibrator_version", "calibrator_model_version",
    "calibration_dataset", "calibration_membership", "training_membership", "training_fingerprint",
    "calibration_fingerprint", "training_count", "calibration_count"])
def test_evaluation_rejects_mismatched_experiment_before_prediction(monkeypatch, experiment, mismatch):
    if mismatch in {"dataset", "target", "scope"}:
        field, value = {"dataset": ("dataset_id", "SYNTHETIC-other"),
                        "target": ("target_definition", "Different invented label"),
                        "scope": ("scope", "public credit benchmark")}[mismatch]
        edit_json(experiment["test"], lambda p: p["identity"].update({field: value}))
    elif mismatch == "features":
        edit_json(experiment["test"], lambda p: p.update(feature_names=["other_feature"]))
    elif mismatch in {"schema", "model_uuid", "model_version", "training_membership"}:
        field, value = {"schema": ("feature_schema_version", "incompatible"),
                        "model_uuid": ("artifact_id", str(uuid4())),
                        "model_version": ("version", "SYNTHETIC-v2"),
                        "training_membership": ("training_sample_ids", ["SYNTHETIC-other-row"])}[mismatch]
        edit_json(experiment["model"], lambda p: p["artifact"].update({field: value}))
    elif mismatch in {"calibrator_uuid", "calibrator_version", "calibrator_model_version",
                      "calibration_dataset", "calibration_membership"}:
        field, value = {"calibrator_uuid": ("artifact_id", str(uuid4())),
                        "calibrator_version": ("version", "SYNTHETIC-cal-v2"),
                        "calibrator_model_version": ("model_version", "SYNTHETIC-v0"),
                        "calibration_dataset": ("calibration_dataset_id", "SYNTHETIC-other"),
                        "calibration_membership": ("calibration_sample_ids", ["SYNTHETIC-other-row"])}[mismatch]
        edit_json(experiment["calibrator"], lambda p: p.update({field: value}))
    else:
        stage, field = mismatch.split("_")
        path = experiment["model"] if stage == "training" else experiment["calibrator"]
        def corrupt_lineage(payload):
            artifact = payload["artifact"] if stage == "training" else payload
            lineage = artifact.get(f"{stage}_lineage")
            assert lineage is not None, "training and calibration artifacts must retain private split lineage"
            lineage["fingerprint" if field == "fingerprint" else "sample_count"] = "0" * 64 if field == "fingerprint" else 999
        edit_json(path, corrupt_lineage)
    def forbidden_prediction(*args, **kwargs):
        pytest.fail("invalid experiment reached model prediction")
    monkeypatch.setattr(LogisticRiskModel, "predict", forbidden_prediction)
    with pytest.raises(ValueError):
        evaluate(monkeypatch, experiment)
    assert not experiment["report"].exists()


def test_evaluation_synthetic_data_cannot_inherit_real_linked_scope(monkeypatch, experiment):
    edit_json(experiment["model"], lambda p: p["artifact"].update(
        scope=Scope.REAL_LINKED_OUTCOME_EXPERIMENT.value, target_definition=RESEARCH_TARGET))
    edit_json(experiment["test"], lambda p: p["identity"].update(target_definition=RESEARCH_TARGET))
    with pytest.raises(ValueError):
        evaluate(monkeypatch, experiment)
    assert not experiment["report"].exists()


def test_evaluation_valid_experiment_preserves_private_reproducibility_lineage(monkeypatch, experiment):
    evaluate(monkeypatch, experiment)
    report = json.loads(experiment["report"].read_text(encoding="utf-8"))
    assert report["scope"] == "SYNTHETIC_DEMO"
    assert experiment["experiment"].is_file()
    lineage = report["private_lineage"]
    model = json.loads(experiment["model"].read_text(encoding="utf-8"))["artifact"]
    calibrator = json.loads(experiment["calibrator"].read_text(encoding="utf-8"))
    assert lineage["model_artifact_id"] == model["artifact_id"]
    assert lineage["model_version"] == model["version"]
    assert lineage["calibrator_artifact_id"] == calibrator["artifact_id"]
    assert lineage["calibrator_version"] == calibrator["version"]
    assert lineage["target_definition"] == synthetic_data("test").identity.target_definition
    for stage, key in (("training", "training"), ("calibration", "calibration"), ("evaluation", "test")):
        split = lineage[f"{stage}_lineage"]
        assert split["sample_count"] == 8
        assert split["sample_ids"] == list(synthetic_data(key).sample_ids)
        assert len(split["fingerprint"]) == 64


@pytest.mark.parametrize("field,value", [
    ("scope", Scope.PUBLIC_DATASET_BENCHMARK), ("target_definition", "Different synthetic target"),
    ("feature_names", ("other_feature",)), ("feature_schema_version", "incompatible"),
    ("training_dataset_id", "SYNTHETIC-other"), ("calibration_dataset_id", "SYNTHETIC-other"),
])
def test_assessment_rejects_incompatible_calibrator_before_prediction(monkeypatch, field, value):
    from agrogami.assessment import assess
    from agrogami.calibration.core import CalibrationArtifact
    from agrogami.fixtures import APPLICANT, T0, coverage, fixture_event

    model = LogisticRiskModel.fit(synthetic_data("training"), scope=Scope.SYNTHETIC_DEMO, version="SYNTHETIC-v1")
    calibration = Calibrator.fit([.1, .9], [0, 1], ["SYNTHETIC-cal-0", "SYNTHETIC-cal-1"],
        model=model.artifact, dataset_id=model.artifact.dataset_id, version="SYNTHETIC-cal-v1")
    calibration.artifact = CalibrationArtifact.model_validate(calibration.artifact.model_dump() | {field: value})
    def forbidden_prediction(*args, **kwargs):
        pytest.fail("incompatible calibrator reached assessment prediction")
    monkeypatch.setattr(model, "predict", forbidden_prediction)
    with pytest.raises(ValueError):
        assess([fixture_event("SYNTHETIC-calibrator-mismatch")], applicant_id=APPLICANT, t0=T0,
               coverage=coverage(complete=True), model=model, calibrator=calibration)


def real_contract_data(stage: str) -> RiskDataset:
    """Invented values exercising a real-linked contract; never an actual real-data experiment."""
    years = {"training": 2020, "calibration": 2021, "evaluation": 2022}
    decision = datetime(years[stage], 1, 1, tzinfo=timezone.utc)
    origin = decision + timedelta(days=1)
    data = synthetic_data(stage)
    # model_copy also exercises stage checks against incomplete already-constructed contracts.
    return data.model_copy(update={
        "identity": DatasetIdentity(dataset_id="SYNTHETIC-real-contract-reproduction",
            target_definition=RESEARCH_TARGET, scope="real linked outcomes",
            limitations=("Invented software fixture, no borrower outcome validation",)),
        "decision_times": (decision,) * 8, "feature_available_times": (decision - timedelta(days=1),) * 8,
        "origination_times": (origin,) * 8,
        "outcome_observation_end_times": (origin + timedelta(days=180),) * 8,
        "label_available_times": (origin + timedelta(days=181),) * 8,
        "available_as_of": origin + timedelta(days=182)})


def fit_real_contract():
    return LogisticRiskModel.fit(real_contract_data("training"),
        scope=Scope.REAL_LINKED_OUTCOME_EXPERIMENT, version="SYNTHETIC-contract-v1")


def calibrate_data(model, data):
    return Calibrator.fit([.1, .2, .3, .4, .6, .7, .8, .9], list(data.labels), list(data.sample_ids),
        model=model.artifact, dataset_id=data.identity.dataset_id, version="SYNTHETIC-cal-v1", data=data)


@pytest.mark.parametrize("stage", ["training", "calibration", "evaluation"])
@pytest.mark.parametrize("missing", ["decision_times", "feature_available_times", "origination_times",
    "outcome_observation_end_times", "label_available_times", "available_as_of"])
def test_temporal_real_linked_metadata_required_at_every_stage(stage, missing):
    data = real_contract_data(stage).model_copy(update={missing: None if missing == "available_as_of" else ()})
    if stage == "training":
        with pytest.raises(ValueError):
            LogisticRiskModel.fit(data, scope=Scope.REAL_LINKED_OUTCOME_EXPERIMENT, version="SYNTHETIC-bad")
    else:
        model = fit_real_contract()
        if stage == "calibration":
            with pytest.raises(ValueError):
                calibrate_data(model, data)
        else:
            from agrogami.calibration import core
            calibration = calibrate_data(model, real_contract_data("calibration"))
            with pytest.raises(ValueError):
                core.validate_evaluation(data, model.artifact, calibration.artifact)


@pytest.mark.parametrize("stage,violation", [
    (stage, violation)
    for stage in ("training", "calibration", "evaluation")
    for violation in ("post_decision", "post_origination", "unmatured_outcome",
                      "premature_label", "future_label", "overlapping_chronology",
                      "unaligned_times", "naive_time")
    if (stage, violation) != ("training", "overlapping_chronology")
])
def test_temporal_leakage_rejected_at_every_stage(stage, violation):
    data = real_contract_data(stage)
    decision = data.decision_times[0]
    origin = data.origination_times[0]
    changes = {
        "post_decision": {"feature_available_times": (decision,) * 8},
        "post_origination": {"origination_times": (decision - timedelta(days=2),) * 8},
        "unmatured_outcome": {"outcome_observation_end_times": (origin + timedelta(days=179),) * 8},
        "premature_label": {"label_available_times": (origin + timedelta(days=179),) * 8},
        "future_label": {"available_as_of": origin + timedelta(days=179)},
        "overlapping_chronology": {"decision_times": (datetime(2020, 1, 2, tzinfo=timezone.utc),) * 8,
            "feature_available_times": (datetime(2019, 12, 31, tzinfo=timezone.utc),) * 8},
        "unaligned_times": {"feature_available_times": (decision - timedelta(days=1),)},
        "naive_time": {"feature_available_times": ((decision - timedelta(days=1)).replace(tzinfo=None),) * 8},
    }[violation]
    data = data.model_copy(update=changes)
    if stage == "training":
        with pytest.raises(ValueError):
            LogisticRiskModel.fit(data, scope=Scope.REAL_LINKED_OUTCOME_EXPERIMENT, version="SYNTHETIC-bad")
    else:
        model = fit_real_contract()
        if stage == "calibration":
            with pytest.raises(ValueError):
                calibrate_data(model, data)
        else:
            from agrogami.calibration import core
            calibration = calibrate_data(model, real_contract_data("calibration"))
            with pytest.raises(ValueError):
                core.validate_evaluation(data, model.artifact, calibration.artifact)


def test_temporal_valid_real_linked_contract_is_accepted_for_all_stages():
    from agrogami.calibration import core
    model = fit_real_contract()
    calibration = calibrate_data(model, real_contract_data("calibration"))
    lineage = core.validate_evaluation(real_contract_data("evaluation"), model.artifact, calibration.artifact)
    assert lineage.scope == Scope.REAL_LINKED_OUTCOME_EXPERIMENT
    assert lineage.evaluation_lineage.sample_count == 8


def test_temporal_real_linked_legacy_calibration_without_dataset_is_rejected():
    model = fit_real_contract()
    with pytest.raises(ValueError):
        Calibrator.fit([.1, .9], [0, 1], ["SYNTHETIC-cal-a", "SYNTHETIC-cal-b"],
            model=model.artifact, dataset_id=model.artifact.dataset_id, version="SYNTHETIC-cal")


@pytest.mark.parametrize("nonfinite", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["native_target", "base", "contribution"])
def test_shap_nonfinite_native_output_fails_safely(field, nonfinite):
    from types import SimpleNamespace
    import numpy as np
    from agrogami.explainability.core import explain_tree
    from agrogami.risk.models import ModelArtifact, TreeRiskModel

    artifact = ModelArtifact(version="SYNTHETIC-finite-check", algorithm="xgboost",
        scope=Scope.SYNTHETIC_DEMO, dataset_id="SYNTHETIC-nonfinite-shap",
        target_definition="Invented software-test label", feature_names=("x",))
    target = nonfinite if field == "native_target" else 3.0
    base = nonfinite if field == "base" else 1.0
    contribution = nonfinite if field == "contribution" else 2.0
    model = TreeRiskModel(SimpleNamespace(predict=lambda *a, **k: np.array([target])), artifact)

    def factory(*args, **kwargs):
        return lambda *a, **k: SimpleNamespace(values=np.array([[contribution]]), base_values=np.array([base]))

    with pytest.raises(ValueError):
        explain_tree(model, {"x": 2.0}, background=[[0.0]], background_identity="SYNTHETIC-background",
                     feature_definitions={"x": "Synthetic numeric field"}, factory=factory)


@pytest.mark.parametrize("nonfinite", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["base_value", "contributions", "target_value", "additivity_error"])
@pytest.mark.parametrize("persisted", [False, True])
def test_shap_contract_rejects_nonfinite_values_on_creation_and_reload(field, nonfinite, persisted):
    from agrogami.explainability.core import TreeExplanation

    payload = dict(model_version="SYNTHETIC-v1", model_artifact_id=str(uuid4()),
        background_identity="SYNTHETIC-background", feature_definitions={"x": "Synthetic numeric field"},
        base_value=1.0, contributions={"x": 2.0}, target_value=3.0, additivity_error=0.0)
    payload[field] = {"x": nonfinite} if field == "contributions" else nonfinite
    with pytest.raises(ValueError):
        if persisted:
            TreeExplanation.model_validate_json(json.dumps(payload))
        else:
            TreeExplanation.model_validate(payload)
