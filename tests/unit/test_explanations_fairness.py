from types import SimpleNamespace
import numpy as np
import pytest
from agrogami.fixtures import scenarios, APPLICANT, T0, coverage
from agrogami.features import build_features
from agrogami.explainability.core import explain_tree, evidence_reasons
from agrogami.fairness.metrics import fairness_metrics, threshold_optimizer_experiment
from agrogami.risk.models import TreeRiskModel, ModelArtifact, ValidationScope as S
from test_risk_governance import synthetic_data


def test_fake_tree_additivity_and_failure():
    artifact = ModelArtifact(version="fake", algorithm="xgboost", scope=S.SYNTHETIC_DEMO, dataset_id="synthetic",
                             target_definition="test", feature_names=("x",))
    model = TreeRiskModel(SimpleNamespace(predict=lambda x, output_margin: np.asarray([3.0])), artifact)
    factory = lambda *a, **k: lambda x, **opts: SimpleNamespace(values=np.array([[2.0]]), base_values=np.array([1.0]))
    result = explain_tree(model, {"x": 2}, background=[[0]], background_identity="synthetic-reference", feature_definitions={"x": "synthetic"}, factory=factory)
    assert result.additivity_error == 0
    bad = lambda *a, **k: lambda x, **opts: SimpleNamespace(values=np.array([[3.0]]), base_values=np.array([1.0]))
    with pytest.raises(ValueError):
        explain_tree(model, {"x": 2}, background=[[0]], background_identity="test", feature_definitions={"x": "x"}, factory=bad)


@pytest.mark.parametrize("algorithm", ["lightgbm", "xgboost"])
def test_real_treeshap_on_tiny_synthetic_tree(algorithm):
    pytest.importorskip(algorithm)
    pytest.importorskip("shap")
    data = synthetic_data()
    model = TreeRiskModel.fit(data, algorithm=algorithm, scope=S.SYNTHETIC_DEMO, version="test")
    result = explain_tree(model, {"external_inflow_total": 4}, background=[list(row) for row in data.values],
        background_identity="SYNTHETIC-tests", feature_definitions={"external_inflow_total": "Observed external inflow total"})
    assert result.additivity_error < 1e-5


def test_missing_receipt_never_generates_late_reason():
    events = scenarios()["bill_missing_evidence"]
    snapshot = build_features(events, applicant_id=APPLICANT, t0=T0, window_days=30, coverage=coverage())
    reasons = evidence_reasons(snapshot, events)
    assert "LATE_VERIFIED_BILLS" not in {reason.code for reason in reasons}
    assert "INSUFFICIENT_EVIDENCE" in {reason.code for reason in reasons}


def test_verified_late_bill_reason_preserves_evidence_and_sources():
    from datetime import timedelta
    from agrogami.schemas import Coverage
    events = scenarios()["bill_late"]
    days = coverage(complete=True).observed_days
    cov = Coverage(applicant_id=APPLICANT, known_at=T0 - timedelta(seconds=1),
                   observed_days=days, obligation_complete_days=days)
    snapshot = build_features(events, applicant_id=APPLICANT, t0=T0, window_days=30, coverage=cov)
    reason = next(r for r in evidence_reasons(snapshot, events) if r.code == "LATE_VERIFIED_BILLS")
    assert reason.contributing_event_ids == (events[0].event_id,)
    assert reason.source_references == (events[0].source_id,)
    assert reason.observed_values["median_payment_delay_days"] == 2


def test_minority_late_payments_still_have_verified_late_reason():
    from datetime import timedelta
    from agrogami.fixtures import fixture_event
    from agrogami.schemas import Coverage, TransactionType as T, TransactionDirection as D
    due = (T0 - timedelta(days=8)).date()
    events = scenarios()["bill_late"] + [fixture_event(f"on-time-{i}", day=10+i,
        transaction_type=T.PAYMENT, direction=D.OUTFLOW, due_date=due, payment_date=due) for i in range(3)]
    cov = Coverage(applicant_id=APPLICANT, known_at=T0 - timedelta(seconds=1),
                   obligation_complete_days=coverage(complete=True).observed_days)
    snapshot = build_features(events, applicant_id=APPLICANT, t0=T0, window_days=30, coverage=cov)
    assert snapshot.features["median_payment_delay_days"].value == 0
    assert "LATE_VERIFIED_BILLS" in {r.code for r in evidence_reasons(snapshot, events)}


def test_fairness_rates_counts_and_uncertainty():
    result = fairness_metrics([1, 0, 1, 0], [1, 0, 0, 1], ["A", "A", "B", "B"], positive_label_definition="test positive")
    assert result.groups["A"].tpr.value == 1
    assert result.groups["A"].fpr.value == 0
    assert result.equalized_odds_difference == 1
    assert result.groups["A"].small_group
    assert result.groups["A"].selection_rate.wilson_95 is not None


def test_undefined_and_abstained_groups():
    result = fairness_metrics([1, 1, None], [None, 1, None], ["A", "B", "B"], positive_label_definition="test")
    assert result.groups["A"].tpr.value is None
    assert result.groups["A"].review_abstention_rate.value == 1
    assert result.equalized_odds_difference is None


def test_fairlearn_offline_wrapper_and_split_guard():
    pytest.importorskip("fairlearn")
    from sklearn.linear_model import LogisticRegression
    x = np.asarray([[0], [1], [2], [3], [4], [5], [6], [7]])
    labels = [0, 1] * 4
    groups = ["A"] * 4 + ["B"] * 4
    estimator = LogisticRegression().fit(x, labels)
    with pytest.raises(ValueError):
        threshold_optimizer_experiment(estimator, x, labels, groups, optimization_sample_ids=[str(i) for i in range(8)],
                                       model_training_sample_ids=["0"])
    optimizer = threshold_optimizer_experiment(estimator, x, labels, groups, optimization_sample_ids=[str(i) for i in range(8)],
                                              model_training_sample_ids=["base-0"])
    prediction = optimizer.predict(x, sensitive_features=groups, random_state=0)
    assert len(prediction) == 8
