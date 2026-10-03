from datetime import timedelta
from decimal import Decimal
import pytest
from agrogami.fixtures import APPLICANT, T0, fixture_event, scenarios, coverage
from agrogami.features import build_features, build_all_windows
from agrogami.schemas import Coverage, TransactionType as T, TransactionDirection as D, ValidationStatus as V


def features(events, n=30, cov=None, t0=T0):
    return build_features(events, applicant_id=APPLICANT, t0=t0, window_days=n,
                          coverage=cov or coverage()).features


@pytest.mark.parametrize("n", [30, 60, 90])
def test_window_inclusive_start_exclusive_end(n):
    events = [fixture_event("start", day=n), fixture_event("before", day=n + 1),
              fixture_event("end", day=0), fixture_event("future", day=-1)]
    assert features(events, n)["external_inflow_total"].value == Decimal("100")
    assert features(events, n)["external_inflow_total"].contributing_event_ids == (events[0].event_id,)


def test_all_windows():
    result = build_all_windows([fixture_event("old", day=50)], applicant_id=APPLICANT, t0=T0, coverage=coverage())
    assert result[30].features["external_inflow_total"].value is None
    assert result[60].features["external_inflow_total"].value == 100
    assert result[90].features["external_inflow_total"].value == 100


@pytest.mark.parametrize("field", ["ingestion_timestamp", "created_at"])
def test_no_knowledge_leakage(field):
    event = fixture_event("late-knowledge", **{field: T0 + timedelta(seconds=1)})
    assert features([event])["external_inflow_total"].value is None


def test_missing_days_are_not_zero_for_variability():
    event = fixture_event("income")
    cov = Coverage(applicant_id=APPLICANT, known_at=T0 - timedelta(seconds=1),
                   observed_days=frozenset({event.event_timestamp.date()}), evidence_event_ids=(event.event_id,))
    f = features([event], cov=cov)
    assert f["inflow_cv"].value == 0
    assert f["observed_day_share"].value == Decimal(1) / 30
    assert f["coverage_days"].value == 1
    assert len(f["observation_gaps"].value) == 29
    assert event.event_id in f["coverage_days"].contributing_event_ids


def test_no_evidence_is_null_not_zero():
    f = features([])
    for name in ("external_inflow_total", "external_outflow_total", "net_external_cash_flow", "inflow_cv",
                 "payment_punctuality", "liquidity_floor", "turnover_circulation_proxy"):
        assert f[name].value is None


@pytest.mark.parametrize("scenario", ["own_account_transfer", "khata_unsettled", "cash_in", "cash_out"])
def test_nonexternal_economic_effect_excluded(scenario):
    f = features(scenarios()[scenario], cov=coverage(complete=True))
    assert f["external_inflow_total"].value == 0
    assert f["external_outflow_total"].value == 0


def test_settlement_cash_only():
    events = scenarios()["khata_settled"]
    f = features(events)
    assert f["external_inflow_total"].value == 100
    assert f["external_inflow_total"].contributing_event_ids == (events[1].event_id,)


@pytest.mark.parametrize("scenario", ["duplicate_sms", "receipt_sms_same_payment"])
def test_one_payment_features(scenario):
    f = features(scenarios()[scenario])
    assert f["external_outflow_total"].value == 102
    assert f["net_external_cash_flow"].value == -102


def test_reversal_cancels_and_future_reversal_does_not():
    original, reversal = scenarios()["reversal"]
    assert features([original, reversal], cov=coverage(complete=True))["net_external_cash_flow"].value == 0
    future = fixture_event("future-reversal", day=-1, transaction_type=T.REVERSAL, direction=D.OUTFLOW,
                           reversal_of_event_id=original.event_id)
    assert features([original, future])["external_inflow_total"].value == 100


def test_reviews_excluded():
    event = fixture_event("pending", validation_status=V.NEEDS_REVIEW)
    assert features([event])["external_inflow_total"].value is None


def test_punctuality_unknown_denominator_and_known():
    events = scenarios()["bill_on_time"] + scenarios()["bill_late"]
    assert features(events)["payment_punctuality"].value is None
    observed = coverage(complete=True).observed_days
    cov = Coverage(applicant_id=APPLICANT, known_at=T0 - timedelta(seconds=1), observed_days=observed,
                   obligation_complete_days=observed)
    f = features(events, cov=cov)
    assert f["payment_punctuality"].value == Decimal("0.5")
    assert f["median_payment_delay_days"].value == 1


def test_missing_receipt_not_nonpayment():
    f = features(scenarios()["bill_missing_evidence"])
    assert f["payment_punctuality"].value is None
    assert "payment_evidence_unknown" in f["missingness_reasons"].value


def test_liquidity_incomplete_null_observed_minimum_kept():
    f = features(scenarios()["incomplete_balance"])
    assert f["liquidity_floor"].value is None
    assert f["observed_minimum_balance"].value == 500


def test_complete_balances_and_turnover():
    events = [fixture_event(f"balance-{i}", day=i, balance=Decimal("500"), amount=Decimal("10"),
                           direction=D.OUTFLOW, transaction_type=T.PAYMENT) for i in range(1, 31)]
    observed = coverage(days=30, complete=True).observed_days
    cov = Coverage(applicant_id=APPLICANT, known_at=T0 - timedelta(seconds=1),
                   observed_days=observed, balance_complete_days=observed)
    f = features(events, cov=cov)
    assert f["liquidity_floor"].value == 1
    assert f["turnover_circulation_proxy"].value == Decimal("0.6")
    assert len(f["liquidity_floor"].contributing_event_ids) == 30


def test_asof_correction_history():
    original = fixture_event("original", amount=Decimal("10"))
    corrected = fixture_event("corrected", amount=Decimal("20"), supersedes_event_id=original.event_id,
                              created_at=T0 + timedelta(days=1))
    assert features([original, corrected])["external_inflow_total"].value == 10
    assert features([original, corrected], t0=T0 + timedelta(days=2))["external_inflow_total"].value == 20


def test_future_coverage_rejected():
    cov = Coverage(applicant_id=APPLICANT, known_at=T0)
    with pytest.raises(ValueError):
        features([], cov=cov)
