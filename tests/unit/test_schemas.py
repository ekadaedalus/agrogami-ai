from datetime import datetime
from decimal import Decimal
import pytest
from pydantic import ValidationError
from agrogami.fixtures import fixture_event, synthetic_candidate
from agrogami.schemas import CanonicalEvent, Provenance


def test_valid_decimal_nullable_and_json_roundtrip():
    event = fixture_event("valid", amount=Decimal("100.01"))
    assert event.amount == Decimal("100.01")
    assert event.counterparty is None
    assert CanonicalEvent.model_validate_json(event.model_dump_json()) == event


@pytest.mark.parametrize("field", ["event_timestamp", "ingestion_timestamp", "created_at"])
def test_aware_datetimes_required(field):
    with pytest.raises(ValidationError):
        fixture_event("naive", **{field: datetime(2025, 1, 1)})


@pytest.mark.parametrize("field", ["applicant_id", "source_id", "event_timestamp", "source_provenance"])
def test_missing_required(field):
    data = fixture_event("missing").model_dump()
    data.pop(field)
    with pytest.raises(ValidationError):
        CanonicalEvent.model_validate(data)


@pytest.mark.parametrize("value", [1.1, "NaN", "Infinity"])
def test_invalid_money(value):
    with pytest.raises(ValidationError):
        fixture_event("bad-money", amount=value)


def test_provenance_document_and_sms():
    digest = "a" * 64
    assert Provenance(source_hash=digest, page_number=1, region=((0, 0), (10, 10))).page_number == 1
    assert Provenance(source_hash=digest, span_start=0, span_end=20, provider="synthetic", template="v1").span_end == 20
    with pytest.raises(ValidationError):
        Provenance(source_hash=digest, span_start=5, span_end=2)
    with pytest.raises(ValidationError):
        Provenance(source_hash="not-a-hash")


def test_candidate_preserves_original_and_is_frozen():
    candidate = synthetic_candidate(fixture_event("candidate"))
    assert candidate.fields["amount"].raw_value == "SYNTHETIC BDT 100.00"
    assert candidate.fields["amount"].normalized_value == "100.00"
    with pytest.raises(ValidationError):
        candidate.created_at = datetime.now()
