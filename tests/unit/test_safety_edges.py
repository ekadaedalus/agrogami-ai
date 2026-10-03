from datetime import timedelta
from decimal import Decimal
import pytest
from agrogami.fixtures import APPLICANT, T0, fixture_event, coverage, scenarios
from agrogami.features import build_features
from agrogami.schemas import Coverage, TransactionType as T, TransactionDirection as D, ValidationStatus as V
from agrogami.validation.rules import reconcile


def snapshot(events, cov=None):
    return build_features(events, applicant_id=APPLICANT, t0=T0, window_days=30, coverage=cov or coverage())


def complete_obligations():
    return Coverage(applicant_id=APPLICANT, known_at=T0 - timedelta(seconds=1),
                    obligation_complete_days=coverage(complete=True).observed_days)


def test_obligation_created_before_window_is_in_denominator():
    event = fixture_event("old-obligation", day=50, transaction_type=T.PAYMENT, direction=D.OUTFLOW,
                          due_date=(T0 - timedelta(days=10)).date(), payment_date=(T0 - timedelta(days=11)).date())
    assert snapshot([event], complete_obligations()).features["payment_punctuality"].value == 1


def test_complete_schedule_missing_payment_still_unknown():
    event = fixture_event("missing-receipt", transaction_type=T.PAYABLE, direction=D.NEUTRAL,
                          due_date=(T0 - timedelta(days=10)).date())
    f = snapshot([event], complete_obligations()).features["payment_punctuality"]
    assert f.value is None
    assert "absence_is_not_nonpayment" in f.reasons[0]


def test_verified_complete_nonpayment_counts_in_denominator():
    event = fixture_event("verified-unpaid", transaction_type=T.PAYABLE, direction=D.NEUTRAL,
                          due_date=(T0 - timedelta(days=10)).date(), payment_record_complete=True)
    assert snapshot([event], complete_obligations()).features["payment_punctuality"].value == 0


def test_rejected_record_never_reaccepted():
    event = fixture_event("rejected", validation_status=V.REJECTED)
    assert reconcile([event])[0].validation_status == V.REJECTED
    assert snapshot([event]).features["net_external_cash_flow"].value is None


def test_feature_snapshot_is_deterministic_and_order_independent():
    a, b = fixture_event("one", day=10), fixture_event("two", day=5)
    assert snapshot([a, b]) == snapshot([b, a])


def test_wrong_applicant_not_included():
    from agrogami.fixtures import identifier
    event = fixture_event("foreign", applicant_id=identifier("other"))
    assert snapshot([event]).features["net_external_cash_flow"].value is None


def test_currency_mismatch_excluded():
    event = fixture_event("foreign-currency", currency="USD")
    assert snapshot([event]).features["net_external_cash_flow"].value is None


def test_ambiguity_excluded_and_coverage_reports_review():
    a, b = fixture_event("a", transaction_reference=None), fixture_event("b", transaction_reference=None)
    f = snapshot([a, b]).features
    assert f["net_external_cash_flow"].value is None
    assert f["accepted_event_share"].value == 0
    assert "AMBIGUOUS_MATCH" in f["missingness_reasons"].value


def test_medium_evidence_explicitly_allows_external_cash():
    event = fixture_event("proven-cash-in", transaction_type=T.CASH_IN, external_medium_evidence=True)
    assert snapshot([event]).features["external_inflow_total"].value == 100


def test_partial_reversal_is_reviewed():
    original, reversal = scenarios()["reversal"]
    from agrogami.validation.rules import replace
    reversal = replace(reversal, amount=Decimal("50"))
    assert reconcile([original, reversal])[-1].validation_status == V.NEEDS_REVIEW


def test_third_copy_of_conflicting_reference_stays_review():
    a = fixture_event("a", transaction_reference="SYNTHETIC-collision", amount=Decimal("100"))
    b = fixture_event("b", transaction_reference="SYNTHETIC-collision", amount=Decimal("200"))
    c = fixture_event("c", transaction_reference="SYNTHETIC-collision", amount=Decimal("100"))
    assert all(e.validation_status == V.NEEDS_REVIEW for e in reconcile([a, b, c]))


def test_daily_balances_need_no_invented_cash_movements():
    records = [fixture_event(f"closing-{i}", day=i, transaction_type=T.BALANCE_SNAPSHOT,
                            direction=D.NEUTRAL, amount=None, fee=None, ownership="own", balance=Decimal("500"))
               for i in range(1, 31)]
    observed = coverage(days=30, complete=True).observed_days
    cov = Coverage(applicant_id=APPLICANT, known_at=T0 - timedelta(seconds=1),
                   observed_days=observed, balance_complete_days=observed)
    f = snapshot(records, cov).features
    assert f["liquidity_floor"].value == 1
    assert f["external_inflow_total"].value == 0
    assert f["active_day_count"].value == 0
    assert f["turnover_circulation_proxy"].value == 0


def test_duplicate_settlement_does_not_consume_receivable_twice():
    from agrogami.validation.rules import replace
    from agrogami.fixtures import identifier
    sale, settlement = scenarios()["khata_settled"]
    duplicate = replace(settlement, event_id=identifier("settlement-copy"))
    result = reconcile([sale, settlement, duplicate])
    assert all(e.validation_status == V.ACCEPTED for e in result)
    assert sum(e.duplicate_of_event_id is not None for e in result) == 1
    assert snapshot([sale, settlement, duplicate]).features["external_inflow_total"].value == 100
