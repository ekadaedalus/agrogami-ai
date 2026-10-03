"""Offline audit metrics; protected membership is supplied explicitly, never inferred."""
from math import sqrt
from typing import Any
from agrogami.schemas import Contract


class Rate(Contract):
    value: float | None
    numerator: int
    denominator: int
    wilson_95: tuple[float, float] | None


def rate(numerator: int, denominator: int) -> Rate:
    if not denominator:
        return Rate(value=None, numerator=numerator, denominator=0, wilson_95=None)
    p, z = numerator / denominator, 1.959963984540054
    center = (p + z * z / (2 * denominator)) / (1 + z * z / denominator)
    half = z * sqrt(p * (1 - p) / denominator + z * z / (4 * denominator ** 2)) / (1 + z * z / denominator)
    return Rate(value=p, numerator=numerator, denominator=denominator, wilson_95=(max(0, center - half), min(1, center + half)))


class GroupMetrics(Contract):
    count: int
    labeled_decided_count: int
    small_group: bool
    tpr: Rate
    fpr: Rate
    selection_rate: Rate
    review_abstention_rate: Rate


class FairnessReport(Contract):
    groups: dict[str, GroupMetrics]
    equalized_odds_difference: float | None
    undefined_reasons: tuple[str, ...]
    positive_label_definition: str
    limitations: tuple[str, ...] = ("Offline descriptive audit; no future parity or production fairness guarantee",
                                    "TPR/FPR condition on labeled non-abstained decisions; report abstention separately")


def fairness_metrics(labels: list[int | None], predictions: list[int | None], groups: list[str], *,
                     positive_label_definition: str, small_group_threshold: int = 30) -> FairnessReport:
    if not groups or len(labels) != len(groups) or len(predictions) != len(groups):
        raise ValueError("aligned nonempty explicit audit groups required")
    if any(x not in {0, 1, None} for x in labels + predictions) or not positive_label_definition:
        raise ValueError("binary outcomes/decisions and positive-label definition required")
    result = {}
    undefined = []
    for group in sorted(set(groups)):
        indices = [i for i, g in enumerate(groups) if g == group]
        decided = [i for i in indices if labels[i] is not None and predictions[i] is not None]
        positives = [i for i in decided if labels[i] == 1]
        negatives = [i for i in decided if labels[i] == 0]
        metric = GroupMetrics(count=len(indices), labeled_decided_count=len(decided), small_group=len(indices) < small_group_threshold,
            tpr=rate(sum(predictions[i] == 1 for i in positives), len(positives)),
            fpr=rate(sum(predictions[i] == 1 for i in negatives), len(negatives)),
            selection_rate=rate(sum(predictions[i] == 1 for i in indices), len(indices)),
            review_abstention_rate=rate(sum(predictions[i] is None for i in indices), len(indices)))
        result[group] = metric
        if not positives or not negatives:
            undefined.append(f"undefined_class_rate:{group}")
        if metric.small_group:
            undefined.append(f"small_group:{group}")
    eo = None
    if len(result) >= 2 and all(g.tpr.value is not None and g.fpr.value is not None for g in result.values()):
        eo = max(max(g.tpr.value for g in result.values()) - min(g.tpr.value for g in result.values()),
                 max(g.fpr.value for g in result.values()) - min(g.fpr.value for g in result.values()))
    else:
        undefined.append("equalized_odds_requires_two_groups_with_both_observed_classes")
    return FairnessReport(groups=result, equalized_odds_difference=eo, undefined_reasons=tuple(undefined),
                          positive_label_definition=positive_label_definition)


def threshold_optimizer_experiment(estimator: Any, x: Any, labels: list[int], groups: list[str], *,
                                   optimization_sample_ids: list[str], model_training_sample_ids: list[str]) -> Any:
    """OFFLINE RESEARCH ONLY; caller must evaluate on another disjoint holdout."""
    if (set(optimization_sample_ids) & set(model_training_sample_ids) or len(optimization_sample_ids) != len(labels)
            or len(set(optimization_sample_ids)) != len(optimization_sample_ids)):
        raise ValueError("offline optimization must be separate from model-training samples")
    if len(groups) != len(labels) or any(set(y for y, g in zip(labels, groups) if g == group) != {0, 1} for group in set(groups)):
        raise ValueError("both outcome classes required in each audit group")
    from fairlearn.postprocessing import ThresholdOptimizer
    optimizer = ThresholdOptimizer(estimator=estimator, constraints="equalized_odds", prefit=True,
                                   predict_method="predict_proba")
    optimizer.fit(x, labels, sensitive_features=groups)
    return optimizer
