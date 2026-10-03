"""Deterministic synthetic scenarios; no real customer messages or model outputs."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid5, NAMESPACE_URL
from agrogami.schemas import (Source, SourceType as S, CanonicalEvent, Provenance,
                              TransactionType as T, TransactionDirection as D, ValidationStatus as V,
                              CandidateExtraction, CandidateField, ReviewReason as R, Coverage)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def identifier(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, "agrogami-synthetic:" + name)


APPLICANT = identifier("applicant")
ACCOUNT = identifier("account")


def fixture_event(name: str, *, day: int = 5, **changes: object) -> CanonicalEvent:
    timestamp = T0 - timedelta(days=day)
    defaults = dict(event_id=identifier(name), applicant_id=APPLICANT, account_id=ACCOUNT,
                    source_id=identifier("source:" + name), source_type=S.SYNTHETIC_FIXTURE,
                    event_timestamp=timestamp, ingestion_timestamp=timestamp + timedelta(seconds=1),
                    created_at=timestamp + timedelta(seconds=1), transaction_type=T.RECEIPT,
                    direction=D.INFLOW, amount=Decimal("100"), fee=Decimal("0"),
                    ownership="external", transaction_reference="SYNTHETIC-" + name,
                    source_provenance=Provenance(source_hash=sha256(("SYNTHETIC " + name).encode()).hexdigest()),
                    validation_status=V.ACCEPTED)
    return CanonicalEvent.model_validate(defaults | changes)


def scenarios() -> dict[str, list[CanonicalEvent]]:
    payment = fixture_event("bkash-payment", transaction_type=T.PAYMENT, direction=D.OUTFLOW,
                            provider="SYNTHETIC-bKash-like", fee=Decimal("2"))
    duplicate = fixture_event("duplicate-sms", **{k: v for k, v in payment.model_dump().items()
                            if k not in {"event_id", "source_id", "source_provenance"}})
    receipt = fixture_event("receipt", transaction_type=T.RECEIPT, direction=D.OUTFLOW,
                            transaction_reference=payment.transaction_reference, provider=payment.provider, fee=payment.fee)
    credit = fixture_event("credit-sale", day=10, transaction_type=T.CREDIT_SALE, direction=D.NEUTRAL)
    settlement = fixture_event("settlement", transaction_type=T.SETTLEMENT, settlement_of_event_id=credit.event_id)
    original = fixture_event("reversed-original", day=10)
    reversal = fixture_event("reversal", transaction_type=T.REVERSAL, direction=D.OUTFLOW,
                             reversal_of_event_id=original.event_id)
    due = (T0 - timedelta(days=8)).date()
    return {
        "external_inflow": [fixture_event("external-inflow")],
        "external_outflow": [fixture_event("external-outflow", transaction_type=T.PAYMENT, direction=D.OUTFLOW, fee=Decimal("2"))],
        "bkash_like_payment_sms": [payment],
        "nagad_like_transfer_sms": [fixture_event("nagad-transfer", transaction_type=T.TRANSFER,
                                   direction=D.OUTFLOW, provider="SYNTHETIC-Nagad-like")],
        "duplicate_sms": [payment, duplicate],
        "receipt_sms_same_payment": [payment, receipt],
        "reversal": [original, reversal],
        "own_account_transfer": [fixture_event("own-transfer", transaction_type=T.TRANSFER, ownership="own")],
        "khata_unsettled": [credit], "khata_settled": [credit, settlement],
        "bill_on_time": [fixture_event("on-time", transaction_type=T.PAYMENT, direction=D.OUTFLOW,
                        due_date=due, payment_date=due)],
        "bill_late": [fixture_event("late", transaction_type=T.PAYMENT, direction=D.OUTFLOW,
                     due_date=due, payment_date=due + timedelta(days=2))],
        "bill_missing_evidence": [fixture_event("missing-bill", transaction_type=T.PAYABLE, direction=D.NEUTRAL,
                                  due_date=due, missingness={"payment_date": "payment_evidence_unknown"})],
        "incomplete_balance": [fixture_event("balance", balance=Decimal("500"))],
        "contradictory_direction": [fixture_event("contradiction", transaction_type=T.PAYMENT)],
        "ambiguous_amount": [fixture_event("ambiguous", amount=None, review_reason=(R.AMBIGUOUS_AMOUNT,))],
        "unsupported_sms": [fixture_event("unsupported", supported_template=False)],
        "low_confidence": [fixture_event("low-confidence", amount_confidence=Decimal("0.4"))],
        "cash_in": [fixture_event("cash-in", transaction_type=T.CASH_IN)],
        "cash_out": [fixture_event("cash-out", transaction_type=T.CASH_OUT, direction=D.OUTFLOW)],
    }


def fixture_sources(events: list[CanonicalEvent]) -> list[Source]:
    return [Source(source_id=e.source_id, applicant_id=e.applicant_id, source_type=e.source_type,
                   source_hash=e.source_provenance.source_hash, ingestion_timestamp=e.ingestion_timestamp,
                   synthetic=True, metadata={"label": "SYNTHETIC"}) for e in events]


def synthetic_candidate(event: CanonicalEvent) -> CandidateExtraction:
    return CandidateExtraction(candidate_id=identifier("candidate:" + str(event.event_id)), source_id=event.source_id,
            created_at=event.created_at, fields={"amount": CandidateField(raw_value="SYNTHETIC BDT 100.00",
            normalized_value="100.00", confidence=Decimal("0.95"), location=event.source_provenance,
            parser_name="synthetic-fixture-generator", parser_version="1.0")})


def coverage(*, days: int = 90, complete: bool = False) -> Coverage:
    observed = frozenset((T0 - timedelta(days=i)).date() for i in range(1, days + 1)) if complete else frozenset()
    return Coverage(applicant_id=APPLICANT, known_at=T0 - timedelta(seconds=1), observed_days=observed,
                    reasons=() if complete else ("synthetic_incomplete_evidence",))
