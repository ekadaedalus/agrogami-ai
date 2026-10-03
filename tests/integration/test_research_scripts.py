import json
import os
import subprocess
import sys
from pathlib import Path
from agrogami.datasets import DatasetIdentity, RiskDataset
from agrogami.application import BackendRepository, EvaluationRun
from agrogami.storage import Store
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]


def run_script(name, *args, env=None):
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / name), *map(str, args)],
                            capture_output=True, text=True, env=env, timeout=90)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_local_risk_training_calibration_evaluation_and_report_persistence(tmp_path):
    identity = DatasetIdentity(dataset_id="SYNTHETIC-script-test", target_definition="Invented binary outcome", scope="synthetic", limitations=("test only",))
    paths = []
    for split, offset in (("train", 0), ("cal", .1), ("test", .2)):
        dataset = RiskDataset(identity=identity, sample_ids=tuple(f"{split}-{i}" for i in range(12)),
            feature_names=("external_inflow_total",), values=tuple((float(i + offset),) for i in range(12)),
            labels=tuple(int(i >= 6) for i in range(12)))
        path = tmp_path / (split + ".json")
        path.write_text(dataset.model_dump_json(), encoding="utf-8")
        paths.append(path)
    output = tmp_path / "artifact"
    run_script("train_risk.py", "--training", paths[0], "--calibration", paths[1], "--algorithm", "logistic",
        "--scope", "SYNTHETIC_DEMO", "--version", "synthetic-script-v1", "--output", output)
    database = "sqlite:///" + str(tmp_path / "reports.db")
    report_path = tmp_path / "evaluation.json"
    stdout = run_script("evaluate_risk.py", "--test-data", paths[2], "--model", output / "model.json",
        "--calibrator", output / "calibrator.json", "--output", report_path, "--persist",
        env=os.environ | {"AGROGAMI_DATABASE_URL": database})
    result = json.loads(report_path.read_text())
    assert result["scope"] == "SYNTHETIC_DEMO"
    assert 0 <= result["calibrated"]["brier"] <= 1
    stored_id = UUID(json.loads(stdout)["run_id"])
    store = Store(database)
    stored = BackendRepository(store).get(EvaluationRun, stored_id)
    assert stored.dataset_id == identity.dataset_id
    assert str(tmp_path) not in stdout
    store.engine.dispose()


def test_extraction_evaluation_uses_supplied_synthetic_predictions(tmp_path):
    path = tmp_path / "predictions.jsonl"
    path.write_text(json.dumps({"sample_id": "SYNTHETIC-1", "dataset_id": "SYNTHETIC",
        "expected": ["O", "B-AMOUNT"], "predicted": ["O", "B-AMOUNT"]}), encoding="utf-8")
    output = tmp_path / "metrics.json"
    run_script("evaluate_extractor.py", "--task", "deberta", "--predictions", path, "--output", output)
    result = json.loads(output.read_text())
    assert result["dataset_id"] == "SYNTHETIC"
    assert result["metrics"]["token_f1"] == 1


def test_training_script_help_does_not_load_or_download_models():
    assert "--base-checkpoint" in run_script("train_extractor.py", "--help")
