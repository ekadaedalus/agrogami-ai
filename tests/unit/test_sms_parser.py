from hashlib import sha256
import pytest
from agrogami.fixtures import APPLICANT
from agrogami.events.intake import intake
from agrogami.schemas import SourceType, ValidationStatus as V, ReviewReason as R
from agrogami.extraction.sms import parse_sms, KINDS


def parse(text, provider="SYNTHETIC-bKash-like"):
    return parse_sms(text, intake(text.encode(), APPLICANT, SourceType.MOBILE_MONEY_SMS, synthetic=True), provider)


@pytest.mark.parametrize("kind", list(KINDS))
@pytest.mark.parametrize("provider", ["SYNTHETIC-bKash-like", "SYNTHETIC-Nagad-like"])
def test_supported_semantics_spans_and_balance_not_amount(kind, provider):
    text = f"SYNTHETIC: {kind} Tk 100.00. Fee Tk 2.00. TrxID SYNTH-001. Balance Tk 9000.00. Counterparty demo-shop. Date 2025-12-01. Time 10:30:00+06:00."
    result = parse(text, provider)
    assert result.status == V.ACCEPTED
    fields = result.candidate.fields
    assert fields["amount"].normalized_value == "100.00"
    assert fields["balance"].normalized_value == "9000.00"
    assert fields["transaction_type"].normalized_value == KINDS[kind].value
    for field in fields.values():
        assert text[field.location.span_start:field.location.span_end] == field.raw_value
        assert field.location.source_hash == sha256(text.encode()).hexdigest()


@pytest.mark.parametrize("text", ["Balance Tk 100.00", "SYNTHETIC: Payment Tk 100 or 1000. Fee Tk 0.00. TrxID A.",
    "SYNTHETIC: Payment Tk 100.00. Fee Tk 0.00. TrxID A. arbitrary suffix", "Your balance is 2000; call 100"])
def test_ambiguous_or_unsupported_routes_review(text):
    result = parse(text)
    assert result.status == V.NEEDS_REVIEW
    assert R.UNSUPPORTED_TEMPLATE in result.reasons
    assert "amount" not in result.candidate.fields


def test_unknown_provider_not_a_production_adapter():
    assert parse("SYNTHETIC: Payment Tk 100.00. Fee Tk 0.00. TrxID A.", "bKash").status == V.NEEDS_REVIEW


def test_missing_time_not_imputed():
    result = parse("SYNTHETIC: Receipt Tk 100.00. Fee Tk 0.00. TrxID A.")
    assert R.MISSING_EVIDENCE in result.reasons
    assert "event_timestamp" not in result.candidate.fields


def test_nontransaction():
    result = parse("SYNTHETIC: Promotional notice. No transaction.")
    assert result.non_transaction
    assert not result.candidate.fields


def test_invalid_calendar_time_routes_review():
    result = parse("SYNTHETIC: Receipt Tk 100.00. Fee Tk 0.00. TrxID A. Date 2025-99-01. Time 10:30:00+06:00.")
    assert result.status == V.NEEDS_REVIEW


def test_sample_templates_are_marked_synthetic_and_parse():
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / "sample_data/provider_sms_templates.json"
    data = json.loads(path.read_text())
    assert data["synthetic"]
    assert all(parse(message["text"], message["provider"]).status == V.ACCEPTED for message in data["messages"])
