"""TreeSHAP on raw model margin and evidence-controlled descriptive reasons."""
from typing import Any, Callable
from uuid import UUID
from decimal import Decimal
import numpy as np
from pydantic import Field, FiniteFloat, TypeAdapter, field_validator
from agrogami.schemas import Contract, FeatureSnapshot, CanonicalEvent, Source
from agrogami.risk.models import TreeRiskModel, vector


class TreeExplanation(Contract):
    model_version: str
    model_artifact_id: UUID
    target: str = "raw_margin_log_odds"
    background_identity: str = Field(min_length=1)
    feature_definitions: dict[str, str]
    base_value: FiniteFloat
    contributions: dict[str, FiniteFloat]
    target_value: FiniteFloat
    additivity_error: FiniteFloat = Field(ge=0)
    limitation: str = "Associational model attribution, not causality; not calibrated-probability or score contributions"


def explain_tree(model: TreeRiskModel, features: dict[str, float], *, background: list[list[float]],
                 background_identity: str, feature_definitions: dict[str, str],
                 factory: Callable[..., Any] | None = None) -> TreeExplanation:
    if model.artifact.algorithm not in {"lightgbm", "xgboost"}:
        raise ValueError("TreeSHAP requires supported tree artifact")
    if set(feature_definitions) != set(model.artifact.feature_names):
        raise ValueError("explanation feature definitions must match model")
    reference = np.asarray(background, dtype=float)
    if reference.ndim != 2 or not len(reference) or reference.shape[1] != len(model.artifact.feature_names) or not np.isfinite(reference).all():
        raise ValueError("finite aligned background required")
    if factory is None:
        import shap
        factory = shap.TreeExplainer
    explainer = factory(getattr(model, "shap_estimator", model.estimator), data=reference,
                        model_output="raw", feature_perturbation="interventional",
                        feature_names=list(model.artifact.feature_names))
    result = explainer(vector(features, model.artifact), check_additivity=True)
    contributions = np.asarray(result.values, dtype=float)
    if contributions.shape != (1, len(features)):
        raise ValueError("only binary single-margin explanations supported")
    base = float(np.asarray(result.base_values).reshape(-1)[0])
    target = float(model.raw_margin(features))
    # Reject NaN/inf explicitly: NaN comparisons are False and would otherwise pass the additivity bound.
    if not np.isfinite(contributions).all() or not np.isfinite(base) or not np.isfinite(target):
        raise ValueError("TreeSHAP produced nonfinite values")
    error = abs(base + float(contributions.sum()) - target)
    if not np.isfinite(error) or error > 1e-5 * max(1, abs(target)):
        raise ValueError("TreeSHAP additivity failed")
    return TreeExplanation(model_version=model.artifact.version, model_artifact_id=model.artifact.artifact_id,
        background_identity=background_identity, feature_definitions=feature_definitions, base_value=base,
        contributions=dict(zip(model.artifact.feature_names, contributions[0].tolist())),
        target_value=target, additivity_error=error)


CATALOG = {
    "LATE_VERIFIED_BILLS": {"required_evidence": "Complete schedule and verified late payment dates",
        "features": ("payment_punctuality", "median_payment_delay_days"),
        "meaning": "Some verified obligations were paid after their due dates"},
    "LOWER_TAIL_LIQUIDITY": {"required_evidence": "Complete verified daily closing balance history",
        "features": ("liquidity_floor",), "meaning": "Observed lower-tail balance ratio was below research threshold 0.5"},
    "INSUFFICIENT_EVIDENCE": {"required_evidence": "Explicit missingness or incomplete observed-day coverage",
        "features": ("observed_day_share", "missingness_reasons"), "meaning": "Evidence coverage is incomplete; not a repayment judgment"},
}


class EvidenceReason(Contract):
    code: str
    required_evidence: str
    feature_names: tuple[str, ...]
    window_days: int
    observed_values: dict[str, Decimal | int | tuple[str, ...] | None]
    contributing_event_ids: tuple[UUID, ...]
    source_references: tuple[UUID, ...]
    description: str

    @field_validator("observed_values", mode="wrap")
    @classmethod
    def structured_observations(cls, values: dict, handler):
        # Explicitly dispatch reason/date collections instead of Decimal's tuple constructor.
        structured = {key: TypeAdapter(tuple[str, ...]).validate_python(value)
                      for key, value in values.items() if isinstance(value, (tuple, list))}
        scalars = handler({key: value for key, value in values.items() if key not in structured})
        return scalars | structured


def evidence_reasons(snapshot: FeatureSnapshot, events: list[CanonicalEvent]) -> tuple[EvidenceReason, ...]:
    f = snapshot.features
    selected = []
    by_id = {e.event_id: e for e in events}
    if f["payment_punctuality"].value is not None and f["median_payment_delay_days"].value is not None:
        payment_ids = f["median_payment_delay_days"].contributing_event_ids
        late_verified = any(i in by_id and by_id[i].due_date is not None and by_id[i].payment_date is not None
            and by_id[i].due_date < by_id[i].payment_date < snapshot.scoring_time.date() for i in payment_ids)
        if late_verified and f["obligation_coverage"].value == 1:
            selected.append("LATE_VERIFIED_BILLS")
    if f["liquidity_floor"].value is not None and f["balance_coverage"].value == 1 and f["liquidity_floor"].value < Decimal("0.5"):
        selected.append("LOWER_TAIL_LIQUIDITY")
    if f["observed_day_share"].value < 1 or f["missingness_count"].value > 0:
        selected.append("INSUFFICIENT_EVIDENCE")
    result = []
    for code in selected:
        entry = CATALOG[code]
        names = entry["features"]
        ids = tuple(sorted({i for name in names for i in f[name].contributing_event_ids}, key=str))
        result.append(EvidenceReason(code=code, required_evidence=entry["required_evidence"], feature_names=names,
            window_days=snapshot.window_days, observed_values={name: f[name].value for name in names},
            contributing_event_ids=ids, source_references=tuple(sorted({by_id[i].source_id for i in ids if i in by_id}, key=str)),
            description=entry["meaning"]))
    return tuple(result)
