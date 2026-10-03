"""Conservative deterministic reconciliation. Outputs new objects, never mutates input."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID
from agrogami.schemas import (CanonicalEvent, CandidateExtraction, ReviewDecision, SourceType as S,
                              ReviewReason as R, TransactionType as T, TransactionDirection as D, ValidationStatus as V)


def validate_candidate(candidate: CandidateExtraction) -> ReviewDecision:
    """Assess critical extracted fields; never promotes a candidate into a canonical event."""
    reasons: list[R] = []
    for name in ("amount", "event_timestamp", "direction"):
        field = candidate.fields.get(name)
        if field is None:
            reasons.append(R.MISSING_EVIDENCE)
            continue
        if field.confidence < Decimal("0.9"):
            reasons.append(R.LOW_CONFIDENCE)
        if field.normalized_value is None:
            reasons.append(R.AMBIGUOUS_AMOUNT if name == "amount" else R.MISSING_EVIDENCE)
            continue
        try:
            if name == "amount":
                amount = Decimal(field.normalized_value)
                if not amount.is_finite() or amount <= 0:
                    reasons.append(R.IMPLAUSIBLE_AMOUNT)
            elif name == "event_timestamp":
                stamp = datetime.fromisoformat(field.normalized_value)
                if stamp.tzinfo is None or stamp.utcoffset() is None:
                    reasons.append(R.MISSING_EVIDENCE)
            elif D(field.normalized_value) == D.UNKNOWN:
                reasons.append(R.CONTRADICTORY_DIRECTION)
        except (ValueError, InvalidOperation):
            reasons.append(R.AMBIGUOUS_AMOUNT if name == "amount" else R.MISSING_EVIDENCE)
    return ReviewDecision(subject_id=candidate.candidate_id,
                          validation_status=V.NEEDS_REVIEW if reasons else V.ACCEPTED,
                          reasons=tuple(dict.fromkeys(reasons)))


def replace(event: CanonicalEvent, **changes: object) -> CanonicalEvent:
    return CanonicalEvent.model_validate(event.model_dump() | changes)


def review(event: CanonicalEvent, reason: R) -> CanonicalEvent:
    return replace(event, validation_status=V.NEEDS_REVIEW,
                   review_reason=tuple(dict.fromkeys((*event.review_reason, reason))))


def validate_event(event: CanonicalEvent, currency: str = "BDT",
                   maximum_amount: Decimal = Decimal("1000000000")) -> CanonicalEvent:
    if event.validation_status == V.REJECTED:
        return event
    reasons = list(event.review_reason)
    is_balance = event.transaction_type == T.BALANCE_SNAPSHOT
    if ((not is_balance and (event.amount is None or event.fee is None))
            or event.account_id is None or event.missingness or is_balance and event.balance is None):
        reasons.append(R.MISSING_EVIDENCE)
    if event.amount is not None and (event.amount <= 0 or event.amount > maximum_amount):
        reasons.append(R.IMPLAUSIBLE_AMOUNT)
    if event.fee is not None and event.fee < 0:
        reasons.append(R.IMPLAUSIBLE_AMOUNT)
    if event.currency != currency:
        reasons.append(R.CURRENCY_MISMATCH)
    if not event.supported_template:
        reasons.append(R.UNSUPPORTED_TEMPLATE)
    if event.source_type == S.MOBILE_MONEY_SMS and (not event.provider or not event.source_provenance.template):
        reasons.append(R.UNSUPPORTED_TEMPLATE)
    if event.amount_confidence < Decimal("0.9"):
        reasons.append(R.LOW_CONFIDENCE)
    if event.direction == D.UNKNOWN:
        reasons.append(R.CONTRADICTORY_DIRECTION)
    expected = {T.PAYMENT: D.OUTFLOW, T.SEND_MONEY: D.OUTFLOW, T.CREDIT_SALE: D.NEUTRAL,
                T.RECEIVABLE: D.NEUTRAL, T.PAYABLE: D.NEUTRAL, T.CASH_IN: D.INFLOW,
                T.CASH_OUT: D.OUTFLOW, T.BALANCE_SNAPSHOT: D.NEUTRAL}
    if event.transaction_type in expected and event.direction != expected[event.transaction_type]:
        reasons.append(R.CONTRADICTORY_DIRECTION)
    if event.ownership == "unknown":
        reasons.append(R.AMBIGUOUS_OWNERSHIP)
    if event.transaction_type == T.OTHER:
        reasons.append(R.UNSUPPORTED_TEMPLATE)
    return replace(event, validation_status=V.NEEDS_REVIEW if reasons else V.ACCEPTED,
                   review_reason=tuple(dict.fromkeys(reasons)))


def same_economic_fields(a: CanonicalEvent, b: CanonicalEvent) -> bool:
    return (a.applicant_id, a.account_id, a.currency, a.amount, a.fee, a.direction,
            a.ownership) == (b.applicant_id, b.account_id, b.currency, b.amount, b.fee,
                             b.direction, b.ownership)


def reconcile(events: list[CanonicalEvent]) -> list[CanonicalEvent]:
    """Reference matches are scoped by applicant/account/provider; proximity alone is review."""
    if len({e.event_id for e in events}) != len(events):
        raise ValueError("event IDs must be unique")
    result = [validate_event(replace(e, duplicate_of_event_id=None))
              for e in sorted(events, key=lambda e: (e.event_timestamp, str(e.event_id)))]
    # Contradictory reference groups are quarantined together, including the third copy.
    groups: dict[tuple[object, ...], list[int]] = {}
    for i, e in enumerate(result):
        if e.transaction_reference and e.transaction_type not in {T.REVERSAL, T.CREDIT_SALE, T.RECEIVABLE, T.PAYABLE, T.BALANCE_SNAPSHOT}:
            groups.setdefault((e.applicant_id, e.account_id, e.provider, e.transaction_reference), []).append(i)
    for indices in groups.values():
        if len(indices) > 1 and any(not same_economic_fields(result[indices[0]], result[j]) for j in indices[1:]):
            for j in indices:
                if result[j].validation_status != V.REJECTED:
                    result[j] = review(result[j], R.AMBIGUOUS_MATCH)
    for i, event in enumerate(result):
        if event.validation_status != V.ACCEPTED or event.transaction_type in {T.REVERSAL, T.CREDIT_SALE, T.RECEIVABLE, T.PAYABLE, T.BALANCE_SNAPSHOT}:
            continue
        earlier = [(j, p) for j, p in enumerate(result[:i]) if p.validation_status == V.ACCEPTED
                   and p.duplicate_of_event_id is None and p.applicant_id == event.applicant_id
                   and p.account_id == event.account_id and p.provider == event.provider
                   and p.transaction_type not in {T.REVERSAL, T.CREDIT_SALE, T.RECEIVABLE, T.PAYABLE, T.BALANCE_SNAPSHOT}]
        matches = [(j, p) for j, p in earlier if event.transaction_reference
                   and event.transaction_reference == p.transaction_reference]
        if len(matches) == 1 and same_economic_fields(event, matches[0][1]):
            result[i] = replace(event, duplicate_of_event_id=matches[0][1].event_id)
        elif matches:
            result[i] = review(event, R.AMBIGUOUS_MATCH)
            for j, p in matches:
                result[j] = review(p, R.AMBIGUOUS_MATCH)
        else:
            nearby = [(j, p) for j, p in earlier if same_economic_fields(event, p)
                      and abs((event.event_timestamp - p.event_timestamp).total_seconds()) <= 300
                      and (not event.transaction_reference or not p.transaction_reference)]
            if nearby:
                result[i] = review(event, R.AMBIGUOUS_MATCH)
                for j, p in nearby:
                    result[j] = review(p, R.AMBIGUOUS_MATCH)
    by_id = {e.event_id: e for e in result}
    reversed_ids: set[UUID] = set()
    settled: dict[UUID, Decimal] = {}
    for i, event in enumerate(result):
        if event.validation_status != V.ACCEPTED or event.duplicate_of_event_id:
            continue
        if event.transaction_type == T.REVERSAL:
            original = by_id.get(event.reversal_of_event_id)
            valid = (original is not None and original.validation_status == V.ACCEPTED
                     and original.duplicate_of_event_id is None and original.transaction_type != T.REVERSAL
                     and original.applicant_id == event.applicant_id and original.account_id == event.account_id
                     and original.currency == event.currency and original.amount == event.amount
                     and original.fee == event.fee and original.event_timestamp <= event.event_timestamp
                     and original.direction != event.direction and original.direction in {D.INFLOW, D.OUTFLOW}
                     and original.event_id not in reversed_ids)
            if not valid:
                result[i] = review(event, R.INVALID_LINK)
            else:
                reversed_ids.add(original.event_id)
        if event.transaction_type == T.SETTLEMENT:
            original = by_id.get(event.settlement_of_event_id)
            amount = settled.get(event.settlement_of_event_id, Decimal(0)) + event.amount
            valid = (original is not None and original.validation_status == V.ACCEPTED
                     and original.transaction_type in {T.CREDIT_SALE, T.RECEIVABLE}
                     and original.applicant_id == event.applicant_id and original.currency == event.currency
                     and original.event_timestamp <= event.event_timestamp and event.direction == D.INFLOW
                     and amount <= original.amount)
            if not valid:
                result[i] = review(event, R.INVALID_LINK)
            else:
                settled[original.event_id] = amount
    return result


def reconcile_balance(before: Decimal | None, after: Decimal | None,
                      movements: list[CanonicalEvent], *, complete: bool,
                      fees_separate: bool | None) -> bool | None:
    """None means insufficient evidence, including unknown fee conventions."""
    if not complete or before is None or after is None or fees_separate is None:
        return None
    if any(e.amount is None or e.fee is None or e.direction not in {D.INFLOW, D.OUTFLOW}
           or e.validation_status != V.ACCEPTED for e in movements):
        return None
    accounts = {(e.applicant_id, e.account_id, e.currency) for e in movements}
    if len(accounts) > 1:
        return None
    expected = before
    for e in movements:
        if e.duplicate_of_event_id:
            continue
        expected += e.amount if e.direction == D.INFLOW else -e.amount
        expected -= e.fee if fees_separate else Decimal(0)
    return expected == after
