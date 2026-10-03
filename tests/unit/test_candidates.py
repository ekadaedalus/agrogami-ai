from decimal import Decimal
import pytest
from agrogami.fixtures import fixture_event, synthetic_candidate
from agrogami.schemas import CandidateExtraction, CandidateField, ReviewReason as R, ValidationStatus as V
from agrogami.validation.rules import validate_candidate


def candidate(**changes):
    original = synthetic_candidate(fixture_event("candidate"))
    amount = original.fields["amount"]
    fields = {"amount": amount, "event_timestamp": CandidateField.model_validate(amount.model_dump() | {
        "normalized_value": "2025-12-01T00:00:00+00:00"}),
        "direction": CandidateField.model_validate(amount.model_dump() | {"normalized_value": "INFLOW"})}
    fields["amount"] = CandidateField.model_validate(amount.model_dump() | changes)
    return CandidateExtraction.model_validate(original.model_dump() | {"fields": fields})


def test_valid_candidate_is_distinct_from_canonical_acceptance():
    value = candidate()
    assert validate_candidate(value).validation_status == V.ACCEPTED
    assert value.fields["amount"].raw_value == "SYNTHETIC BDT 100.00"


@pytest.mark.parametrize("changes,reason", [({"normalized_value": None}, R.AMBIGUOUS_AMOUNT),
    ({"normalized_value": "maybe 100"}, R.AMBIGUOUS_AMOUNT), ({"normalized_value": "NaN"}, R.IMPLAUSIBLE_AMOUNT),
    ({"confidence": Decimal("0.5")}, R.LOW_CONFIDENCE)])
def test_critical_candidate_fields(changes, reason):
    assert reason in validate_candidate(candidate(**changes)).reasons


def test_missing_candidate_fields():
    value = synthetic_candidate(fixture_event("missing"))
    assert R.MISSING_EVIDENCE in validate_candidate(value).reasons
