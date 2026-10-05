"""Separate holdout calibration, evaluators and project-only score mapping."""
from math import isfinite, log, log2
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4
import numpy as np
from pydantic import Field, model_validator
from agrogami.schemas import Contract
from agrogami.risk.models import ModelArtifact, ValidationScope
from agrogami.datasets import (RiskDataset, DatasetSplitLineage, dataset_lineage,
                              validate_dataset_scope, validate_temporal_scope, contract_fingerprint)


def probabilities(values: list[float]) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.ndim != 1 or not len(result) or not np.isfinite(result).all() or (result < 0).any() or (result > 1).any():
        raise ValueError("finite probabilities in [0,1] required")
    return result


def logits(values: np.ndarray) -> np.ndarray:
    clamped = np.clip(values, 1e-9, 1 - 1e-9)
    return np.log(clamped / (1 - clamped))


class CalibrationArtifact(Contract):
    artifact_id: UUID = Field(default_factory=uuid4)
    version: str
    method: Literal["sigmoid", "isotonic"]
    model_artifact_id: str
    model_version: str
    training_dataset_id: str
    calibration_dataset_id: str
    calibration_sample_ids: tuple[str, ...]
    scope: ValidationScope = ValidationScope.UNTRAINED
    target_definition: str = ""
    feature_names: tuple[str, ...] = ()
    feature_schema_version: str = "1.0"
    calibration_lineage: DatasetSplitLineage | None = None
    coefficient: float | None = None
    intercept: float | None = None
    x_thresholds: tuple[float, ...] = ()
    y_thresholds: tuple[float, ...] = ()

    @model_validator(mode="after")
    def valid_parameters(self) -> "CalibrationArtifact":
        if len(set(self.calibration_sample_ids)) != len(self.calibration_sample_ids) or not self.calibration_sample_ids:
            raise ValueError("unique calibration identities required")
        if self.calibration_lineage is not None:
            lineage = self.calibration_lineage
            validate_dataset_scope(lineage.identity, self.scope)
            if (lineage.identity.dataset_id != self.calibration_dataset_id
                    or lineage.identity.target_definition != self.target_definition
                    or lineage.feature_names != self.feature_names or lineage.feature_schema_version != self.feature_schema_version
                    or lineage.observed_sample_ids != self.calibration_sample_ids):
                raise ValueError("calibration split lineage mismatch")
        if self.method == "sigmoid":
            if self.coefficient is None or self.intercept is None or not isfinite(self.coefficient) or not isfinite(self.intercept):
                raise ValueError("finite sigmoid parameters required")
        else:
            if len(self.x_thresholds) < 2 or len(self.x_thresholds) != len(self.y_thresholds):
                raise ValueError("aligned isotonic thresholds required")
            if any(not isfinite(x) or not 0 <= x <= 1 for x in self.x_thresholds + self.y_thresholds):
                raise ValueError("invalid isotonic probability thresholds")
            if any(a >= b for a, b in zip(self.x_thresholds, self.x_thresholds[1:])) or any(a > b for a, b in zip(self.y_thresholds, self.y_thresholds[1:])):
                raise ValueError("isotonic thresholds must be monotone")
        return self


class Calibrator:
    def __init__(self, artifact: CalibrationArtifact):
        self.artifact = artifact

    @classmethod
    def fit(cls, raw: list[float], labels: list[int], sample_ids: list[str], *, model: ModelArtifact,
            dataset_id: str, version: str, method: Literal["sigmoid", "isotonic"] = "sigmoid",
            minimum_isotonic_samples: int = 100, data: RiskDataset | None = None) -> "Calibrator":
        lineage = None
        if data is None and model.scope == ValidationScope.REAL_LINKED_OUTCOME_EXPERIMENT:
            raise ValueError("real-linked calibration requires the complete temporal dataset")
        if data is not None:
            validate_temporal_scope(data, model.scope,
                previous=(model.training_lineage,) if model.training_lineage is not None else ())
            if model.scope == ValidationScope.REAL_LINKED_OUTCOME_EXPERIMENT and model.training_lineage is None:
                raise ValueError("real-linked calibration requires temporal training lineage")
            lineage = dataset_lineage(data)
            if (data.identity.dataset_id != dataset_id or dataset_id != model.dataset_id
                    or data.identity.target_definition != model.target_definition
                    or data.feature_names != model.feature_names or data.feature_schema_version != model.feature_schema_version
                    or lineage.observed_sample_ids != tuple(sample_ids)
                    or tuple(y for y in data.labels if y is not None) != tuple(labels)):
                raise ValueError("calibration dataset/target/schema/membership mismatch")
            if model.training_lineage and set(data.sample_ids) & set(model.training_lineage.sample_ids):
                raise ValueError("training/calibration split overlap")
        p = probabilities(raw)
        if len(labels) != len(p) or len(sample_ids) != len(p) or len(set(sample_ids)) != len(sample_ids):
            raise ValueError("aligned unique calibration sample identities required")
        if set(sample_ids) & set(model.training_sample_ids):
            raise ValueError("model-training and calibration sets must be disjoint")
        if set(labels) != {0, 1}:
            raise ValueError("calibration requires both observed classes")
        values = dict(version=version, method=method, model_artifact_id=str(model.artifact_id), model_version=model.version,
                      training_dataset_id=model.dataset_id, calibration_dataset_id=dataset_id,
                      calibration_sample_ids=tuple(sample_ids), scope=model.scope,
                      target_definition=model.target_definition, feature_names=model.feature_names,
                      feature_schema_version=model.feature_schema_version, calibration_lineage=lineage)
        if method == "sigmoid":
            from sklearn.linear_model import LogisticRegression
            fitted = LogisticRegression(C=1e6, max_iter=2000).fit(logits(p).reshape(-1, 1), labels)
            values.update(coefficient=float(fitted.coef_[0][0]), intercept=float(fitted.intercept_[0]))
        elif method == "isotonic":
            if len(p) < max(100, minimum_isotonic_samples) or min(labels.count(0), labels.count(1)) < 10 or len(set(p)) < 10:
                raise ValueError("insufficient isotonic sample/class/probability support")
            from sklearn.isotonic import IsotonicRegression
            fitted = IsotonicRegression(out_of_bounds="clip").fit(p, labels)
            values.update(x_thresholds=tuple(fitted.X_thresholds_), y_thresholds=tuple(fitted.y_thresholds_))
        else:
            raise ValueError("unsupported calibrator")
        return cls(CalibrationArtifact.model_validate(values))

    def predict(self, raw_probability: float) -> float:
        p = probabilities([raw_probability])
        if self.artifact.method == "sigmoid":
            from scipy.special import expit
            return float(expit(self.artifact.coefficient * logits(p)[0] + self.artifact.intercept))
        return float(np.interp(p[0], self.artifact.x_thresholds, self.artifact.y_thresholds))

    def save(self, path: Path) -> None:
        path.write_text(self.artifact.model_dump_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Calibrator":
        return cls(CalibrationArtifact.model_validate_json(path.read_text(encoding="utf-8")))


class ExperimentManifest(Contract):
    """Pins private artifact metadata; retain beside locally supplied model files."""
    model_artifact_id: UUID
    model_version: str
    calibrator_artifact_id: UUID
    calibrator_version: str
    model_artifact_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    calibrator_artifact_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, model: ModelArtifact, calibrator: CalibrationArtifact) -> "ExperimentManifest":
        return cls(model_artifact_id=model.artifact_id, model_version=model.version,
            calibrator_artifact_id=calibrator.artifact_id, calibrator_version=calibrator.version,
            model_artifact_fingerprint=contract_fingerprint(model),
            calibrator_artifact_fingerprint=contract_fingerprint(calibrator))


class EvaluationLineage(Contract):
    dataset_id: str
    target_definition: str
    scope: ValidationScope
    feature_names: tuple[str, ...]
    feature_schema_version: str
    model_artifact_id: UUID
    model_version: str
    calibrator_artifact_id: UUID
    calibrator_version: str
    training_lineage: DatasetSplitLineage
    calibration_lineage: DatasetSplitLineage
    evaluation_lineage: DatasetSplitLineage


def validate_model_calibrator(model: ModelArtifact, calibration: CalibrationArtifact) -> None:
    """Match metadata before evaluation or an evidence-gated assessment predicts."""
    model = ModelArtifact.model_validate(model.model_dump())
    calibration = CalibrationArtifact.model_validate(calibration.model_dump())
    if (calibration.model_artifact_id != str(model.artifact_id) or calibration.model_version != model.version
            or calibration.training_dataset_id != model.dataset_id or calibration.calibration_dataset_id != model.dataset_id
            or calibration.scope != model.scope or calibration.target_definition != model.target_definition
            or calibration.feature_names != model.feature_names or calibration.feature_schema_version != model.feature_schema_version):
        raise ValueError("model/calibrator scope, target or lineage mismatch")
    if set(model.training_sample_ids) & set(calibration.calibration_sample_ids):
        raise ValueError("model/calibrator sample overlap")
    if model.scope == ValidationScope.REAL_LINKED_OUTCOME_EXPERIMENT:
        if model.training_lineage is None or calibration.calibration_lineage is None:
            raise ValueError("real-linked model/calibrator temporal lineage required")
        validate_temporal_scope(calibration.calibration_lineage, model.scope, previous=(model.training_lineage,))


def validate_evaluation(data: RiskDataset, model: ModelArtifact, calibration: CalibrationArtifact,
                        experiment: ExperimentManifest | None = None) -> EvaluationLineage:
    """Validate lineage and scope before any heldout prediction can execute."""
    model = ModelArtifact.model_validate(model.model_dump())
    calibration = CalibrationArtifact.model_validate(calibration.model_dump())
    validate_dataset_scope(data.identity, model.scope)
    evaluation = dataset_lineage(data)
    if model.training_lineage is None or calibration.calibration_lineage is None:
        raise ValueError("complete training/calibration split lineage required")
    validate_temporal_scope(calibration.calibration_lineage, model.scope, previous=(model.training_lineage,))
    validate_temporal_scope(data, model.scope, previous=(model.training_lineage, calibration.calibration_lineage))
    if (data.identity.dataset_id != model.dataset_id or data.identity.target_definition != model.target_definition
            or data.feature_names != model.feature_names or data.feature_schema_version != model.feature_schema_version):
        raise ValueError("evaluation dataset/target/schema mismatch")
    validate_model_calibrator(model, calibration)
    training_ids = set(model.training_lineage.sample_ids)
    calibration_ids = set(calibration.calibration_lineage.sample_ids)
    if training_ids & calibration_ids or set(data.sample_ids) & (training_ids | calibration_ids):
        raise ValueError("evaluation requires disjoint split membership")
    if experiment is not None and experiment != ExperimentManifest.create(model, calibration):
        raise ValueError("experiment artifact identity/version/fingerprint mismatch")
    return EvaluationLineage(dataset_id=data.identity.dataset_id, target_definition=data.identity.target_definition,
        scope=model.scope, feature_names=data.feature_names, feature_schema_version=data.feature_schema_version,
        model_artifact_id=model.artifact_id, model_version=model.version,
        calibrator_artifact_id=calibration.artifact_id, calibrator_version=calibration.version,
        training_lineage=model.training_lineage, calibration_lineage=calibration.calibration_lineage,
        evaluation_lineage=evaluation)


class DisplayScore(Contract):
    calibrated_probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    unclipped_score: float
    display_score: int = Field(ge=300, le=850)
    mapping_version: str = "project-300-850-v1"
    label: str = "Agrogami project-specific display score; not FICO or bureau-equivalent; not an approval decision"


def project_score(probability: float) -> DisplayScore:
    probabilities([probability])
    p = min(1 - 1e-9, max(1e-9, probability))
    raw = 600 + 40 * log2((1 - p) / (9 * p))
    return DisplayScore(calibrated_probability=probability, unclipped_score=raw,
                        display_score=round(min(850, max(300, raw))))


def calibration_metrics(raw: list[float], labels: list[int], bins: int = 10) -> dict:
    from sklearn.metrics import brier_score_loss, log_loss
    from sklearn.linear_model import LogisticRegression
    p = probabilities(raw)
    if len(p) != len(labels) or not set(labels) <= {0, 1} or bins < 1:
        raise ValueError("aligned binary calibration evaluation required")
    curve = []
    for index in range(bins):
        selected = (p >= index / bins) & ((p < (index + 1) / bins) if index < bins - 1 else (p <= 1))
        if selected.any():
            curve.append({"count": int(selected.sum()), "mean_probability": float(p[selected].mean()),
                          "observed_rate": float(np.asarray(labels)[selected].mean())})
    slope, intercept = None, None
    if len(set(labels)) == 2 and len(set(p)) > 1:
        fitted = LogisticRegression(C=1e6, max_iter=2000).fit(logits(p).reshape(-1, 1), labels)
        slope, intercept = float(fitted.coef_[0][0]), float(fitted.intercept_[0])
    return {"brier": float(brier_score_loss(labels, p)), "log_loss": float(log_loss(labels, p, labels=[0, 1])),
            "reliability_curve": curve, "slope": slope, "intercept": intercept}
