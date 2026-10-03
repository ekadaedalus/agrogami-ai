"""As-of feature computation with explicit coverage and per-feature lineage."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from hashlib import sha256
from uuid import UUID, uuid5, NAMESPACE_URL
from agrogami.schemas import (CanonicalEvent, Coverage, FeatureSnapshot, FeatureValue,
                              TransactionType as T, TransactionDirection as D, ValidationStatus as V)
from agrogami.validation.rules import reconcile

EPSILON = Decimal("0.01")  # one hundredth of a BDT; numeric stability only


def quantile(values: list[Decimal], q: Decimal) -> Decimal:
    ordered = sorted(values)
    position = Decimal(len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def current_as_of(events: list[CanonicalEvent], t0: datetime) -> list[CanonicalEvent]:
    available = [e for e in events if e.created_at < t0 and e.ingestion_timestamp < t0
                 and e.event_timestamp < t0]
    superseded = {e.supersedes_event_id for e in available}
    return [e for e in available if e.event_id not in superseded]


def build_features(events: list[CanonicalEvent], *, applicant_id: UUID, t0: datetime,
                   window_days: int, coverage: Coverage, currency: str = "BDT") -> FeatureSnapshot:
    if t0.tzinfo is None or t0.utcoffset() is None:
        raise ValueError("scoring time must be timezone-aware")
    if window_days not in {30, 60, 90}:
        raise ValueError("supported windows are 30/60/90 days")
    if coverage.applicant_id != applicant_id or coverage.known_at >= t0:
        raise ValueError("coverage must belong to applicant and be available before scoring")
    t0 = t0.astimezone(timezone.utc)
    start = t0 - timedelta(days=window_days)
    # Observation dates are UTC calendar days. Partial endpoint days cannot prove full coverage.
    days = {start.date() + timedelta(days=i) for i in range(window_days)}
    if t0.time() != datetime.min.time():
        days = {d for d in days if datetime.combine(d, datetime.min.time(), timezone.utc) >= start}
    available = current_as_of([e for e in events if e.applicant_id == applicant_id], t0)
    accepted_input = [e for e in available if e.validation_status == V.ACCEPTED and e.currency == currency]
    reconciled = reconcile(accepted_input)
    valid = [e for e in reconciled if e.validation_status == V.ACCEPTED and not e.duplicate_of_event_id]
    cancelled = {e.reversal_of_event_id for e in valid if e.transaction_type == T.REVERSAL}
    cancellations = [e for e in valid if e.transaction_type == T.REVERSAL]
    economic = [e for e in valid if e.event_id not in cancelled and e.transaction_type != T.REVERSAL
                and start <= e.event_timestamp < t0]
    reconciled_by_id = {e.event_id: e for e in reconciled}
    window = [reconciled_by_id.get(e.event_id, e) for e in available if start <= e.event_timestamp < t0]
    window_ids = tuple(sorted((e.event_id for e in window), key=str))
    evidence_ids = tuple(sorted(set(coverage.evidence_event_ids) & {e.event_id for e in available}, key=str))
    # Fees on own/medium movements require a separate, explicitly external event in v1.
    cash = [e for e in economic if e.ownership == "external"
            and e.transaction_type not in {T.CREDIT_SALE, T.RECEIVABLE, T.PAYABLE}
            and (e.transaction_type not in {T.CASH_IN, T.CASH_OUT} or e.external_medium_evidence)
            and e.direction in {D.INFLOW, D.OUTFLOW}]
    inflows = [e for e in cash if e.direction == D.INFLOW]
    outflows = [e for e in cash if e.direction == D.OUTFLOW]
    observed = days & set(coverage.observed_days)
    complete = len(observed) == window_days
    unknown = () if complete else ("incomplete_cash_observation; totals cover verified evidence only",)
    features: dict[str, FeatureValue] = {}

    def put(name: str, value, contributing=(), reasons=()):
        ids = tuple(sorted({e.event_id if isinstance(e, CanonicalEvent) else e for e in contributing}, key=str))
        features[name] = FeatureValue(value=value, contributing_event_ids=ids, reasons=tuple(reasons))

    inflow = sum((e.amount for e in inflows), Decimal(0))
    outflow = sum((e.amount + e.fee for e in outflows), Decimal(0))
    reversal_evidence = [e for e in cancellations if e.reversal_of_event_id in {x.event_id for x in window}]
    put("external_inflow_total", inflow if inflows or complete else None, inflows + reversal_evidence, unknown)
    put("external_outflow_total", outflow if outflows or complete else None, outflows + reversal_evidence, unknown)
    put("net_external_cash_flow", inflow - outflow if cash or complete else None, cash + reversal_evidence, unknown)
    daily = [sum((e.amount for e in inflows if e.event_timestamp.astimezone(timezone.utc).date() == day), Decimal(0))
             for day in sorted(observed)]
    if daily:
        with localcontext() as ctx:
            ctx.prec = 28
            mean = sum(daily) / len(daily)
            variance = sum((x - mean) ** 2 for x in daily) / len(daily)
            cv = variance.sqrt() / (mean + EPSILON)
    else:
        cv = None
    put("inflow_cv", cv, [e for e in inflows if e.event_timestamp.date() in observed] + list(evidence_ids),
        () if complete else ("CV uses attested complete days only; unobserved days omitted",))
    obligations = [e for e in valid if e.event_id not in cancelled and e.transaction_type != T.REVERSAL
                   and e.due_date is not None and start.date() <= e.due_date < t0.date()]
    obligation_complete = days <= set(coverage.obligation_complete_days) and len(days) == window_days
    payment_complete = all(e.payment_date is not None and e.payment_date < t0.date()
                           or e.payment_record_complete for e in obligations)
    paid = [e for e in obligations if e.payment_date is not None and e.payment_date < t0.date()]
    punctual = sum(e.payment_date <= e.due_date for e in paid)
    delays = [Decimal(max(0, (e.payment_date - e.due_date).days)) for e in paid]
    obligation_reason = () if obligation_complete else ("complete_obligation_denominator_unknown",)
    if obligation_complete and not payment_complete:
        obligation_reason = ("payment_record_incomplete; absence_is_not_nonpayment",)
    if obligation_complete and not obligations:
        obligation_reason = ("no_verified_obligations_due",)
    put("payment_punctuality", Decimal(punctual) / len(obligations) if obligation_complete and payment_complete and obligations else None,
        obligations + list(evidence_ids), obligation_reason)
    put("median_payment_delay_days", quantile(delays, Decimal("0.5")) if obligation_complete and payment_complete and delays else None,
        paid + list(evidence_ids), obligation_reason or (() if delays else ("no_verified_payments",)))
    # v1 balances require one account and exactly one verified daily closing value per complete day.
    balances = [e for e in economic if e.balance is not None and e.event_timestamp.date() in days]
    balance_complete = (days <= set(coverage.balance_complete_days) and len(days) == window_days
                        and len({e.account_id for e in balances}) == 1
                        and Counter(e.event_timestamp.date() for e in balances) == Counter({d: 1 for d in days}))
    values = [e.balance for e in balances]
    mean_balance = sum(values) / len(values) if values else None
    denominator_valid = balance_complete and mean_balance is not None and mean_balance > 0 and all(x >= 0 for x in values)
    balance_reason = () if denominator_valid else ("incomplete_or_invalid_daily_balance_history",)
    put("liquidity_floor", quantile(values, Decimal("0.10")) / mean_balance if denominator_valid else None,
        balances + list(evidence_ids), balance_reason)
    put("observed_minimum_balance", min(values) if values else None, balances,
        () if balance_complete else ("observed_values_only",))
    put("turnover_circulation_proxy", outflow / mean_balance if denominator_valid and complete else None,
        balances + outflows + list(evidence_ids), balance_reason + (() if complete else ("incomplete_cash_observation",)))
    active_events = [e for e in economic if e.transaction_type != T.BALANCE_SNAPSHOT]
    active = {e.event_timestamp.astimezone(timezone.utc).date() for e in active_events}
    put("coverage_days", len(observed), evidence_ids, coverage.reasons)
    put("coverage_length_days", (max(observed) - min(observed)).days + 1 if observed else 0, evidence_ids)
    put("observed_day_share", Decimal(len(observed)) / window_days, evidence_ids)
    put("observation_gaps", tuple(d.isoformat() for d in sorted(days - observed)), evidence_ids, coverage.reasons)
    put("active_day_count", len(active), active_events)
    put("active_day_share", Decimal(len(active)) / window_days, active_events)
    put("source_count", len({e.source_id for e in window}), window)
    put("source_mix", dict(Counter(e.source_type.value for e in window)), window)
    put("balance_coverage", Decimal(len(days & set(coverage.balance_complete_days))) / window_days, evidence_ids, balance_reason)
    put("obligation_coverage", Decimal(len(days & set(coverage.obligation_complete_days))) / window_days, evidence_ids, obligation_reason)
    reasons = tuple(sorted(set(coverage.reasons) | {r.value for e in window for r in e.review_reason}
                           | {r for e in window for r in e.missingness.values()}))
    put("missingness_count", sum(len(e.missingness) + len(e.review_reason) for e in window) + len(coverage.reasons), window)
    put("missingness_reasons", reasons, window_ids)
    put("reviewed_event_share", Decimal(sum(e.reviewed for e in window)) / len(window) if window else None, window)
    put("accepted_event_share", Decimal(sum(e.validation_status == V.ACCEPTED for e in window)) / len(window) if window else None, window)
    snapshot = FeatureSnapshot(applicant_id=applicant_id, scoring_time=t0, window_days=window_days, features=features)
    payload = snapshot.model_dump_json(exclude={"snapshot_id"})
    return FeatureSnapshot.model_validate(snapshot.model_dump() | {
        "snapshot_id": uuid5(NAMESPACE_URL, "agrogami-feature:" + sha256(payload.encode()).hexdigest())})


def build_all_windows(events: list[CanonicalEvent], *, applicant_id: UUID, t0: datetime,
                      coverage: Coverage) -> dict[int, FeatureSnapshot]:
    return {n: build_features(events, applicant_id=applicant_id, t0=t0, window_days=n, coverage=coverage)
            for n in (30, 60, 90)}
