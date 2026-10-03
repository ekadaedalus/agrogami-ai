from datetime import timedelta
from pathlib import Path
import pytest
from agrogami.fixtures import T0
from agrogami.datasets import DatasetIdentity, RiskDataset, LoanOutcome, PerformanceObservation, RESEARCH_TARGET
from agrogami.risk.models import LogisticRiskModel, TreeRiskModel, ValidationScope as S, ModelArtifact
from agrogami.calibration.core import Calibrator, project_score, calibration_metrics


def synthetic_data(prefix="train", feature_names=("external_inflow_total",)):
    return RiskDataset(identity=DatasetIdentity(dataset_id="SYNTHETIC-tests", target_definition="Invented binary label",
        scope="synthetic", limitations=("Not underwriting",)), sample_ids=tuple(f"{prefix}-{i}" for i in range(12)),
        feature_names=feature_names, values=tuple((float(i),) for i in range(12)), labels=tuple(int(i >= 6) for i in range(12)))


def test_censored_label_not_negative_and_observed_90dpd_positive():
    kwargs = dict(loan_id="synthetic", origination_time=T0, initially_current=True,
                  followup_end=T0 + timedelta(days=90), complete_followup=False, observations=())
    assert LoanOutcome(**kwargs).label() is None
    kwargs["observations"] = (PerformanceObservation(timestamp=T0 + timedelta(days=90), days_past_due=90),)
    assert LoanOutcome(**kwargs).label() == 1
    kwargs.update(followup_end=T0 + timedelta(days=180), complete_followup=True, observations=())
    assert LoanOutcome(**kwargs).label() == 0
    kwargs["initially_current"] = False
    assert LoanOutcome(**kwargs).label() is None


def test_post_origination_outside_performance_window_ignored():
    outcome = LoanOutcome(loan_id="synthetic", origination_time=T0, initially_current=True,
        followup_end=T0 + timedelta(days=181), complete_followup=True,
        observations=(PerformanceObservation(timestamp=T0 + timedelta(days=181), days_past_due=90),))
    assert outcome.label() == 0


def test_temporal_and_protected_feature_separation():
    data = synthetic_data()
    with pytest.raises(ValueError):
        RiskDataset.model_validate(data.model_dump() | {"protected_columns": data.feature_names})
    with pytest.raises(ValueError):
        RiskDataset.model_validate(data.model_dump() | {"decision_times": (T0,) * 12, "feature_available_times": (T0,) * 12})


def test_public_scope_cannot_become_real_linked():
    data = synthetic_data()
    identity = DatasetIdentity(dataset_id="public", target_definition="Original benchmark", scope="public credit benchmark", limitations=())
    data = RiskDataset.model_validate(data.model_dump() | {"identity": identity})
    with pytest.raises(ValueError):
        LogisticRiskModel.fit(data, scope=S.REAL_LINKED_OUTCOME_EXPERIMENT, version="test")


def test_regularized_logistic_roundtrip_and_no_missing_inputs(tmp_path):
    model = LogisticRiskModel.fit(synthetic_data(), scope=S.SYNTHETIC_DEMO, version="test")
    p = model.predict({"external_inflow_total": 4.0})
    assert 0 <= p <= 1
    path = tmp_path / "model.json"
    model.save(path)
    assert LogisticRiskModel.load(path).predict({"external_inflow_total": 4.0}) == p
    with pytest.raises(ValueError):
        model.predict({"protected_group": 1.0})


def test_untrained_model_refuses_prediction():
    artifact = ModelArtifact(version="test", algorithm="regularized_logistic", scope=S.UNTRAINED,
        dataset_id="none", target_definition=RESEARCH_TARGET, feature_names=("external_inflow_total",))
    model = LogisticRiskModel(artifact, [0], 0, [0], [1])
    with pytest.raises(ValueError):
        model.predict({"external_inflow_total": 100})


def test_calibration_separation_roundtrip_and_evaluation(tmp_path):
    model = LogisticRiskModel.fit(synthetic_data(), scope=S.SYNTHETIC_DEMO, version="test")
    with pytest.raises(ValueError):
        Calibrator.fit([.1, .9], [0, 1], ["train-0", "cal-1"], model=model.artifact, dataset_id="SYNTHETIC-tests", version="cal")
    cal = Calibrator.fit([.1, .2, .8, .9], [0, 0, 1, 1], [f"cal-{i}" for i in range(4)],
                         model=model.artifact, dataset_id="SYNTHETIC-tests", version="cal")
    path = tmp_path / "cal.json"
    cal.save(path)
    assert Calibrator.load(path).predict(.2) == cal.predict(.2)
    metrics = calibration_metrics([.1, .9], [0, 1])
    assert metrics["brier"] == pytest.approx(.01)
    assert sum(bin["count"] for bin in metrics["reliability_curve"]) == 2


def test_isotonic_small_support_refused():
    model = LogisticRiskModel.fit(synthetic_data(), scope=S.SYNTHETIC_DEMO, version="test")
    with pytest.raises(ValueError):
        Calibrator.fit([.1, .9], [0, 1], ["a", "b"], model=model.artifact, dataset_id="synthetic", version="cal", method="isotonic")


def test_isotonic_sufficient_support_predicts_monotonically():
    model = LogisticRiskModel.fit(synthetic_data(), scope=S.SYNTHETIC_DEMO, version="test")
    raw = [i / 199 for i in range(200)]
    labels = [int(i >= 100) for i in range(200)]
    calibrator = Calibrator.fit(raw, labels, [f"isotonic-{i}" for i in range(200)], model=model.artifact,
        dataset_id="SYNTHETIC-tests", version="cal", method="isotonic")
    assert calibrator.predict(.1) <= calibrator.predict(.9)


def test_censored_training_rows_are_excluded():
    original = synthetic_data()
    data = RiskDataset.model_validate(original.model_dump() | {"labels": (None,) + original.labels[1:]})
    model = LogisticRiskModel.fit(data, scope=S.SYNTHETIC_DEMO, version="test")
    assert "train-0" not in model.artifact.training_sample_ids


def test_linked_scope_requires_real_identity_and_temporal_metadata():
    original = synthetic_data()
    identity = DatasetIdentity(dataset_id="SYNTHETIC-test-not-real", scope="synthetic", target_definition=RESEARCH_TARGET, limitations=())
    data = RiskDataset.model_validate(original.model_dump() | {"identity": identity,
        "decision_times": (T0,) * 12, "feature_available_times": (T0 - timedelta(days=1),) * 12})
    with pytest.raises(ValueError):
        LogisticRiskModel.fit(data, scope=S.REAL_LINKED_OUTCOME_EXPERIMENT, version="not-real")


@pytest.mark.parametrize("p,expected", [(.10, 600), (.05, 643), (.20, 553)])
def test_score_formula(p, expected):
    score = project_score(p)
    assert score.display_score == expected
    assert "not FICO" in score.label


@pytest.mark.parametrize("p,expected", [(0, 850), (1, 300), (1e-20, 850), (1 - 1e-15, 300)])
def test_score_clipping(p, expected):
    score = project_score(p)
    assert score.display_score == expected
    assert score.calibrated_probability == p


@pytest.mark.parametrize("p", [-.1, 1.1, float("nan"), float("inf")])
def test_invalid_probability(p):
    with pytest.raises(ValueError):
        project_score(p)


@pytest.mark.parametrize("algorithm", ["lightgbm", "xgboost"])
def test_native_tree_fit_roundtrip(tmp_path, algorithm):
    pytest.importorskip(algorithm)
    model = TreeRiskModel.fit(synthetic_data(), algorithm=algorithm, scope=S.SYNTHETIC_DEMO, version="test")
    path = tmp_path / "tree"
    model.save(path)
    loaded = TreeRiskModel.load(path)
    assert loaded.predict({"external_inflow_total": 4}) == pytest.approx(model.predict({"external_inflow_total": 4}), abs=1e-7)
