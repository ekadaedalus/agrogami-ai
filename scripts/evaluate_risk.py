"""Evaluate an explicit disjoint local test set; optionally run separate protected audit."""
import argparse
import json
from pathlib import Path
from agrogami.datasets import RiskDataset
from agrogami.risk.models import LogisticRiskModel, TreeRiskModel
from agrogami.calibration.core import Calibrator, ExperimentManifest, calibration_metrics, validate_evaluation
from agrogami.fairness.metrics import fairness_metrics

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-data", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--calibrator", type=Path, required=True)
    parser.add_argument("--experiment", type=Path, help="Private experiment manifest; defaults to beside the model")
    parser.add_argument("--audit-groups", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--persist", action="store_true", help="Append report metadata to configured local backend database")
    args = parser.parse_args()
    model = TreeRiskModel.load(args.model) if args.model.is_dir() else LogisticRiskModel.load(args.model)
    calibrator = Calibrator.load(args.calibrator)
    data = RiskDataset.model_validate_json(args.test_data.read_text(encoding="utf-8"))
    manifest_path = args.experiment or args.model.parent / "experiment.json"
    if not manifest_path.is_file():
        raise ValueError("private experiment manifest required")
    manifest = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    lineage = validate_evaluation(data, model.artifact, calibrator.artifact, manifest)
    rows = [(sid, row, y) for sid, row, y in zip(data.sample_ids, data.values, data.labels) if y is not None]
    labels = [y for _, _, y in rows]
    raw = [model.predict(dict(zip(data.feature_names, row))) for _, row, _ in rows]
    calibrated = [calibrator.predict(p) for p in raw]
    result = {"dataset_id": data.identity.dataset_id, "scope": lineage.scope.value,
              "raw": calibration_metrics(raw, labels), "calibrated": calibration_metrics(calibrated, labels),
              "limitations": list(data.identity.limitations), "private_lineage": lineage.model_dump(mode="json")}
    if args.audit_groups:
        groups = json.loads(args.audit_groups.read_text(encoding="utf-8"))
        result["fairness"] = fairness_metrics(labels, [int(p >= 0.5) for p in calibrated], [groups[sid] for sid, _, _ in rows],
            positive_label_definition="Adverse-outcome flag at research threshold 0.5, not approval").model_dump(mode="json")
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.persist:
        from agrogami.config import Settings
        from agrogami.storage import Store
        from agrogami.application import BackendRepository, EvaluationRun
        from agrogami.fairness.metrics import FairnessReport
        store = Store(Settings().database_url)
        report = EvaluationRun(dataset_id=data.identity.dataset_id, scope=lineage.scope, private_lineage=lineage,
            metrics={f"{stage}_{metric}": result[stage][metric] for stage in ("raw", "calibrated") for metric in ("brier", "log_loss", "slope", "intercept")},
            fairness=FairnessReport.model_validate(result["fairness"]) if "fairness" in result else None,
            limitations=data.identity.limitations + ("Separate local benchmark/research run; no underwriting validation",))
        BackendRepository(store).save(report)
        print(json.dumps({"run_id": str(report.run_id), "scope": report.scope.value}))
        store.engine.dispose()
