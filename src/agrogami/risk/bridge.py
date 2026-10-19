"""Bridge stored feature snapshots into RiskDataset rows without imputing anything.

A snapshot contributes a row only when every selected feature has a scalar, non-null value and
no coverage/review reasons: the same eligibility rule assess() applies before scoring. Any other
snapshot is excluded and the exclusion is reported; a missing feature never becomes 0.
"""
from decimal import Decimal
from typing import Iterable
import numpy as np
from pydantic import Field
from agrogami.datasets import DatasetIdentity, RiskDataset
from agrogami.schemas import Contract, FeatureSnapshot

# Ordered numeric subset of one window. Window-level coverage features are not risk inputs.
# The demo model uses the 90-day window: the full attested history carries far more of each
# borrower's behaviour than 30 days (see data/synthetic/DATA_CARD.md).
MODEL_WINDOW = 90
MODEL_FEATURES = ("external_inflow_total", "external_outflow_total", "net_external_cash_flow", "inflow_cv",
                  "payment_punctuality", "median_payment_delay_days", "active_day_share")


class BridgeExclusion(Contract):
    sample_id: str
    feature: str
    reason: str


class BridgeResult(Contract):
    dataset: RiskDataset
    exclusions: tuple[BridgeExclusion, ...] = ()
    window_days: int = Field(ge=1)


def model_inputs(snapshot: FeatureSnapshot, feature_names: tuple[str, ...]) -> tuple[dict[str, float] | None, BridgeExclusion | None]:
    """Return the numeric vector or the first reason it is ineligible (sample_id filled by caller)."""
    values: dict[str, float] = {}
    for name in feature_names:
        feature = snapshot.features.get(name)
        if feature is None:
            return None, BridgeExclusion(sample_id="", feature=name, reason="feature_absent")
        if feature.value is None:
            return None, BridgeExclusion(sample_id="", feature=name,
                                         reason="null:" + ";".join(feature.reasons) if feature.reasons else "null")
        if isinstance(feature.value, (dict, tuple)):
            return None, BridgeExclusion(sample_id="", feature=name, reason="non_scalar")
        if feature.reasons:
            return None, BridgeExclusion(sample_id="", feature=name, reason="reasons:" + ";".join(feature.reasons))
        if isinstance(feature.value, Decimal) and not feature.value.is_finite():
            return None, BridgeExclusion(sample_id="", feature=name, reason="non_finite")
        values[name] = float(feature.value)
    return values, None


def snapshots_to_dataset(rows: Iterable[tuple[str, FeatureSnapshot, int | None]], *, identity: DatasetIdentity,
                         feature_names: tuple[str, ...] = MODEL_FEATURES, window_days: int = MODEL_WINDOW) -> BridgeResult:
    sample_ids, values, labels, exclusions = [], [], [], []
    for sample_id, snapshot, label in rows:
        if snapshot.window_days != window_days:
            exclusions.append(BridgeExclusion(sample_id=sample_id, feature="*", reason="window_mismatch"))
            continue
        vector, exclusion = model_inputs(snapshot, feature_names)
        if vector is None:
            exclusions.append(exclusion.model_copy(update={"sample_id": sample_id}))
            continue
        sample_ids.append(sample_id)
        values.append(tuple(vector[name] for name in feature_names))
        labels.append(label)
    dataset = RiskDataset(identity=identity, sample_ids=tuple(sample_ids), feature_names=feature_names,
                          values=tuple(values), labels=tuple(labels))
    return BridgeResult(dataset=dataset, exclusions=tuple(exclusions), window_days=window_days)


def subset(data: RiskDataset, sample_ids: Iterable[str]) -> RiskDataset:
    wanted = set(sample_ids)
    keep = [i for i, sid in enumerate(data.sample_ids) if sid in wanted]
    return RiskDataset.model_validate(data.model_dump() | {
        "sample_ids": tuple(data.sample_ids[i] for i in keep), "values": tuple(data.values[i] for i in keep),
        "labels": tuple(data.labels[i] for i in keep)})


def stratified_split(data: RiskDataset, *, seed: int, fractions: tuple[float, float, float] = (0.6, 0.2, 0.2)
                     ) -> tuple[RiskDataset, RiskDataset, RiskDataset]:
    """Seeded per-class shuffle into disjoint train/calibration/test splits; censored rows excluded."""
    if len(fractions) != 3 or any(f <= 0 for f in fractions) or abs(sum(fractions) - 1) > 1e-9:
        raise ValueError("three positive split fractions summing to 1 required")
    rng = np.random.default_rng(seed)
    parts: list[list[str]] = [[], [], []]
    for label in (0, 1):
        members = sorted(sid for sid, y in zip(data.sample_ids, data.labels) if y == label)
        if len(members) < 3:
            raise ValueError("each class needs at least three labelled rows")
        order = [members[i] for i in rng.permutation(len(members))]
        first = max(1, round(len(order) * fractions[0]))
        second = max(first + 1, round(len(order) * (fractions[0] + fractions[1])))
        for part, chunk in zip(parts, (order[:first], order[first:second], order[second:])):
            part.extend(chunk)
    return tuple(subset(data, part) for part in parts)  # type: ignore[return-value]
