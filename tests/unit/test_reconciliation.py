from decimal import Decimal
import pytest
from agrogami.fixtures import scenarios, fixture_event
from agrogami.schemas import ReviewReason as R, ValidationStatus as V, TransactionDirection as D, TransactionType as T
from agrogami.validation.rules import reconcile, validate_event, reconcile_balance


@pytest.mark.parametrize("scenario", ["duplicate_sms", "receipt_sms_same_payment"])
def test_exact_reference_counted_once(scenario):
    result = reconcile(scenarios()[scenario])
    assert sum(e.duplicate_of_event_id is not None for e in result) == 1
    assert all(e.validation_status == V.ACCEPTED for e in result)


def test_reference_collision_reviews_both():
    a = fixture_event("a")
    b = fixture_event("b", amount=Decimal("200"), transaction_reference=a.transaction_reference)
    assert all(R.AMBIGUOUS_MATCH in e.review_reason for e in reconcile([a, b]))


def test_proximity_without_reference_is_review():
    a = fixture_event("a", transaction_reference=None)
    b = fixture_event("b", transaction_reference=None)
    assert all(e.validation_status == V.NEEDS_REVIEW for e in reconcile([a, b]))


@pytest.mark.parametrize("scenario,reason", [("contradictory_direction", R.CONTRADICTORY_DIRECTION),
    ("ambiguous_amount", R.AMBIGUOUS_AMOUNT), ("unsupported_sms", R.UNSUPPORTED_TEMPLATE),
    ("low_confidence", R.LOW_CONFIDENCE)])
def test_unsafe_fields_review(scenario, reason):
    assert reason in reconcile(scenarios()[scenario])[0].review_reason


@pytest.mark.parametrize("changes,reason", [({"ownership": "unknown"}, R.AMBIGUOUS_OWNERSHIP),
    ({"currency": "USD"}, R.CURRENCY_MISMATCH), ({"fee": None}, R.MISSING_EVIDENCE),
    ({"amount": Decimal("-1")}, R.IMPLAUSIBLE_AMOUNT), ({"direction": D.UNKNOWN}, R.CONTRADICTORY_DIRECTION)])
def test_validation_rules(changes, reason):
    assert reason in validate_event(fixture_event("v", **changes)).review_reason


def test_reversal_valid_and_invalid_link():
    assert all(e.validation_status == V.ACCEPTED for e in reconcile(scenarios()["reversal"]))
    invalid = fixture_event("invalid", transaction_type=T.REVERSAL, direction=D.OUTFLOW)
    assert R.INVALID_LINK in reconcile([invalid])[0].review_reason


def test_settlement_requires_receivable_and_cannot_overpay():
    events = scenarios()["khata_settled"]
    assert all(e.validation_status == V.ACCEPTED for e in reconcile(events))
    bad = fixture_event("overpay", transaction_type=T.SETTLEMENT, amount=Decimal("101"),
                        settlement_of_event_id=events[0].event_id)
    assert R.INVALID_LINK in reconcile([events[0], bad])[-1].review_reason


def test_valid_and_inconsistent_balance():
    movement = fixture_event("payment", transaction_type=T.PAYMENT, direction=D.OUTFLOW,
                             amount=Decimal("100"), fee=Decimal("2"))
    assert reconcile_balance(Decimal("500"), Decimal("398"), [movement], complete=True, fees_separate=True)
    assert reconcile_balance(Decimal("500"), Decimal("399"), [movement], complete=True, fees_separate=True) is False


@pytest.mark.parametrize("complete,fees", [(False, True), (True, None)])
def test_incomplete_balance_unknown(complete, fees):
    assert reconcile_balance(Decimal("500"), Decimal("999"), [], complete=complete, fees_separate=fees) is None
