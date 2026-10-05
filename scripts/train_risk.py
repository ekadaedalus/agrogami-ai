"""Train scoped local risk data and a distinct calibration split; no downloads."""
import argparse
import json
from pathlib import Path
from agrogami.datasets import RiskDataset, dataset_lineage, validate_temporal_scope
from agrogami.risk.models import LogisticRiskModel, TreeRiskModel, ValidationScope
from agrogami.calibration.core import Calibrator, ExperimentManifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--algorithm", choices=["logistic", "lightgbm", "xgboost"], required=True)
    parser.add_argument("--scope", choices=[s.value for s in ValidationScope if s != ValidationScope.UNTRAINED], required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--method", choices=["sigmoid", "isotonic"], default="sigmoid")
    args = parser.parse_args()
    training = RiskDataset.model_validate_json(args.training.read_text(encoding="utf-8"))
    calibration = RiskDataset.model_validate_json(args.calibration.read_text(encoding="utf-8"))
    if (training.feature_names != calibration.feature_names or training.identity != calibration.identity
            or training.feature_schema_version != calibration.feature_schema_version):
        raise ValueError("calibration must preserve dataset/target/features")
    if set(training.sample_ids) & set(calibration.sample_ids):
        raise ValueError("overlapping model-training/calibration splits")
    scope = ValidationScope(args.scope)
    validate_temporal_scope(training, scope)
    validate_temporal_scope(calibration, scope, previous=(dataset_lineage(training),))
    model = (LogisticRiskModel.fit(training, scope=scope, version=args.version) if args.algorithm == "logistic"
             else TreeRiskModel.fit(training, algorithm=args.algorithm, scope=scope, version=args.version))
    selected = [(sid, row, y) for sid, row, y in zip(calibration.sample_ids, calibration.values, calibration.labels) if y is not None]
    raw = [model.predict(dict(zip(calibration.feature_names, row))) for _, row, _ in selected]
    fitted = Calibrator.fit(raw, [y for _, _, y in selected], [sid for sid, _, _ in selected], model=model.artifact,
                           dataset_id=calibration.identity.dataset_id, version=args.version + "-cal",
                           method=args.method, data=calibration)
    args.output.mkdir(parents=True, exist_ok=False)
    model.save(args.output / ("model.json" if args.algorithm == "logistic" else "tree"))
    fitted.save(args.output / "calibrator.json")
    (args.output / "experiment.json").write_text(
        ExperimentManifest.create(model.artifact, fitted.artifact).model_dump_json(indent=2), encoding="utf-8")
