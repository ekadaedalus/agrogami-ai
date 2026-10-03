"""Scoped numerical model interfaces. No implicit training or untrained predictions."""
from enum import StrEnum
from math import isfinite
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4
import numpy as np
from pydantic import Field, model_validator
from agrogami.schemas import Contract
from agrogami.datasets import RiskDataset, RESEARCH_TARGET


class ValidationScope(StrEnum):
    REAL_LINKED_OUTCOME_EXPERIMENT = "REAL_LINKED_OUTCOME_EXPERIMENT"
    PUBLIC_DATASET_BENCHMARK = "PUBLIC_DATASET_BENCHMARK"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    UNTRAINED = "UNTRAINED"


class ModelArtifact(Contract):
    artifact_id: UUID = Field(default_factory=uuid4)
    version: str = Field(min_length=1)
    algorithm: str
    scope: ValidationScope
    dataset_id: str
    target_definition: str
    feature_names: tuple[str, ...]
    feature_schema_version: str = "1.0"
    window_days: int = Field(default=30, ge=1)
    training_sample_ids: tuple[str, ...] = ()
    protected_columns: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def separation(self) -> "ModelArtifact":
        if len(set(self.feature_names)) != len(self.feature_names) or not self.feature_names:
            raise ValueError("unique feature definitions required")
        if set(self.feature_names) & set(self.protected_columns):
            raise ValueError("protected feature leakage")
        return self


class RiskModel(Protocol):
    artifact: ModelArtifact
    def predict(self, features: dict[str, float]) -> float: ...


def vector(features: dict[str, float], artifact: ModelArtifact) -> np.ndarray:
    if artifact.scope == ValidationScope.UNTRAINED:
        raise ValueError("untrained artifact cannot predict")
    if set(features) != set(artifact.feature_names) or any(not isfinite(float(v)) for v in features.values()):
        raise ValueError("complete finite feature vector required")
    return np.asarray([[float(features[name]) for name in artifact.feature_names]])


def training_rows(data: RiskDataset, scope: ValidationScope) -> tuple[np.ndarray, np.ndarray]:
    if scope == ValidationScope.UNTRAINED:
        raise ValueError("training must declare actual experiment scope")
    public = data.identity.scope in {"public credit benchmark", "relational financial benchmark"}
    if public and scope != ValidationScope.PUBLIC_DATASET_BENCHMARK:
        raise ValueError("public benchmark cannot become a linked-outcome experiment")
    if scope == ValidationScope.PUBLIC_DATASET_BENCHMARK and not public:
        raise ValueError("public benchmark scope requires a public risk dataset identity")
    if scope == ValidationScope.SYNTHETIC_DEMO and data.identity.scope != "synthetic":
        raise ValueError("synthetic scope requires explicitly synthetic dataset identity")
    if scope == ValidationScope.REAL_LINKED_OUTCOME_EXPERIMENT:
        if data.identity.scope != "real linked outcomes" or data.identity.target_definition != RESEARCH_TARGET or not data.decision_times:
            raise ValueError("linked outcome requires research target and point-in-time availability")
    selected = [i for i, y in enumerate(data.labels) if y is not None]
    y = np.asarray([data.labels[i] for i in selected], dtype=int)
    if len(set(y)) != 2:
        raise ValueError("both observed outcome classes required; censored rows excluded")
    return np.asarray([data.values[i] for i in selected]), y


def artifact_for(data: RiskDataset, algorithm: str, scope: ValidationScope, version: str) -> ModelArtifact:
    return ModelArtifact(version=version, algorithm=algorithm, scope=scope, dataset_id=data.identity.dataset_id,
        target_definition=data.identity.target_definition, feature_names=data.feature_names,
        training_sample_ids=tuple(sid for sid, y in zip(data.sample_ids, data.labels) if y is not None),
        protected_columns=data.protected_columns, limitations=data.identity.limitations)


class LogisticRiskModel:
    def __init__(self, artifact: ModelArtifact, coefficients: list[float], intercept: float,
                 mean: list[float], scale: list[float]):
        if not all(len(v) == len(artifact.feature_names) for v in (coefficients, mean, scale)):
            raise ValueError("invalid logistic artifact shape")
        if not all(isfinite(x) for row in (coefficients, mean, scale, [intercept]) for x in row) or any(x <= 0 for x in scale):
            raise ValueError("invalid logistic parameters")
        self.artifact, self.coefficients, self.intercept, self.mean, self.scale = artifact, coefficients, intercept, mean, scale

    @classmethod
    def fit(cls, data: RiskDataset, *, scope: ValidationScope, version: str, c: float = 1.0) -> "LogisticRiskModel":
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        if c <= 0:
            raise ValueError("positive inverse regularization required")
        x, y = training_rows(data, scope)
        scaler = StandardScaler().fit(x)
        fitted = LogisticRegression(C=c, solver="lbfgs", max_iter=2000, random_state=0).fit(scaler.transform(x), y)
        return cls(artifact_for(data, "regularized_logistic", scope, version), fitted.coef_[0].tolist(),
                   float(fitted.intercept_[0]), scaler.mean_.tolist(), scaler.scale_.tolist())

    def predict(self, features: dict[str, float]) -> float:
        from scipy.special import expit
        x = vector(features, self.artifact)[0]
        return float(expit(((x - self.mean) / self.scale) @ self.coefficients + self.intercept))

    def save(self, path: Path) -> None:
        import json
        path.write_text(json.dumps({"artifact": self.artifact.model_dump(mode="json"),
            "coefficients": self.coefficients, "intercept": self.intercept, "mean": self.mean, "scale": self.scale}), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "LogisticRiskModel":
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(ModelArtifact.model_validate(data["artifact"]), data["coefficients"], data["intercept"], data["mean"], data["scale"])


class TreeRiskModel:
    def __init__(self, estimator: Any, artifact: ModelArtifact):
        self.estimator, self.artifact = estimator, artifact

    def predict(self, features: dict[str, float]) -> float:
        probability = float(self.estimator.predict_proba(vector(features, self.artifact))[0][1])
        if not isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("invalid model probability")
        return probability

    def raw_margin(self, features: dict[str, float]) -> float:
        x = vector(features, self.artifact)
        if self.artifact.algorithm == "lightgbm":
            return float(self.estimator.predict(x, raw_score=True)[0])
        if self.artifact.algorithm == "xgboost":
            return float(self.estimator.predict(x, output_margin=True)[0])
        raise ValueError("unsupported tree model")

    @classmethod
    def fit(cls, data: RiskDataset, *, algorithm: str, scope: ValidationScope, version: str) -> "TreeRiskModel":
        x, y = training_rows(data, scope)
        if algorithm == "lightgbm":
            from lightgbm import LGBMClassifier
            estimator = LGBMClassifier(n_estimators=50, max_depth=3, num_leaves=7, min_child_samples=2,
                                       random_state=0, n_jobs=1, verbosity=-1)
        elif algorithm == "xgboost":
            from xgboost import XGBClassifier
            estimator = XGBClassifier(n_estimators=50, max_depth=3, random_state=0, n_jobs=1,
                                       eval_metric="logloss", tree_method="hist", enable_categorical=False)
        else:
            raise ValueError("supported tree algorithm required")
        estimator.fit(x, y)
        return cls(estimator, artifact_for(data, algorithm, scope, version))

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "artifact.json").write_text(self.artifact.model_dump_json(), encoding="utf-8")
        if self.artifact.algorithm == "lightgbm":
            self.estimator.booster_.save_model(str(directory / "model.txt"))
        elif self.artifact.algorithm == "xgboost":
            self.estimator.save_model(directory / "model.ubj")
        else:
            raise ValueError("unsupported tree artifact")

    @classmethod
    def load(cls, directory: Path) -> "TreeRiskModel":
        artifact = ModelArtifact.model_validate_json((directory / "artifact.json").read_text(encoding="utf-8"))
        if artifact.algorithm == "lightgbm":
            import lightgbm
            booster = lightgbm.Booster(model_file=str(directory / "model.txt"))
            class NativeLightGBM:
                def predict_proba(self, x):
                    p = booster.predict(x)
                    return np.column_stack((1 - p, p))
                def predict(self, x, raw_score=False):
                    return booster.predict(x, raw_score=raw_score)
            loaded = cls(NativeLightGBM(), artifact)
            loaded.shap_estimator = booster
            return loaded
        if artifact.algorithm == "xgboost":
            from xgboost import XGBClassifier
            estimator = XGBClassifier(enable_categorical=False)
            estimator.load_model(directory / "model.ubj")
            return cls(estimator, artifact)
        raise ValueError("unsupported native tree artifact")
