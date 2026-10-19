"""Per-account running-balance continuity for provider messages that report a balance.

Convention (synthetic-provider-v1 templates): the reported balance is the wallet balance after
the movement, with the fee charged separately from the amount:

    inflow:  balance_after = balance_before + amount - fee
    outflow: balance_after = balance_before - amount - fee

The check compares an arriving event only with the stored current versions of the same
applicant/account/provider/currency that report a balance. It never imputes a balance or a
direction: unknown directions, ambiguous same-instant neighbours and missing neighbours return
None (unverifiable), not a break. Copies carrying the same transaction reference are excluded
from the neighbours so a duplicate SMS does not break its own chain.
"""
from decimal import Decimal
from agrogami.schemas import CanonicalEvent, TransactionDirection as D

CONVENTION = "synthetic-provider-v1: balance_after = balance_before + amount - fee (inflow) or - amount - fee (outflow)"


def balance_effect(event: CanonicalEvent) -> Decimal | None:
    """Signed wallet movement implied by one event, or None when it cannot be derived."""
    if event.amount is None or event.fee is None:
        return None
    if event.direction == D.INFLOW:
        return event.amount - event.fee
    if event.direction == D.OUTFLOW:
        return -(event.amount + event.fee)
    return None


def _anchor(events: list[CanonicalEvent]) -> Decimal | None:
    balances = {e.balance for e in events}
    return balances.pop() if len(balances) == 1 else None


def continuity_break(event: CanonicalEvent, stored: list[CanonicalEvent]) -> bool | None:
    """True when a stored neighbour proves the reported balance cannot follow; None if unverifiable."""
    if event.balance is None or event.account_id is None:
        return None
    superseded = {e.supersedes_event_id for e in stored if e.supersedes_event_id}
    peers = [e for e in stored if e.event_id not in superseded and e.event_id != event.event_id
             and e.applicant_id == event.applicant_id and e.account_id == event.account_id
             and e.provider == event.provider and e.currency == event.currency and e.balance is not None
             and not (event.transaction_reference and e.transaction_reference == event.transaction_reference)]
    if any(e.event_timestamp == event.event_timestamp for e in peers):
        return None
    earlier = [e for e in peers if e.event_timestamp < event.event_timestamp]
    later = [e for e in peers if e.event_timestamp > event.event_timestamp]
    checks: list[bool] = []
    if earlier:
        latest = max(e.event_timestamp for e in earlier)
        before = _anchor([e for e in earlier if e.event_timestamp == latest])
        effect = balance_effect(event)
        if before is not None and effect is not None:
            checks.append(before + effect == event.balance)
    if later:
        earliest = min(e.event_timestamp for e in later)
        following = [e for e in later if e.event_timestamp == earliest]
        effects = {balance_effect(e) for e in following}
        after, effect = _anchor(following), effects.pop() if len(effects) == 1 else None
        if after is not None and effect is not None:
            checks.append(event.balance + effect == after)
    return None if not checks else not all(checks)
