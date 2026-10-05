"""Presentation preserves unknowns."""
from decimal import Decimal
from uuid import UUID


def display(value: object, reasons: tuple[str, ...] = ()) -> str:
    if value is None:
        return "Unavailable — " + (", ".join(reasons) if reasons else "insufficient supporting evidence")
    return str(value)


_LABELS: dict[str, str] = {
    "external_inflow_total": "External inflow",
    "external_outflow_total": "External outflow",
    "inflow_cv": "Inflow variability",
    "coverage_length_days": "Coverage span (days)",
    "ACCEPTED": "Accepted",
    "NEEDS_REVIEW": "Needs review",
    "REJECTED": "Rejected",
    "INSUFFICIENT_EVIDENCE": "Insufficient evidence to assess",
    "EVIDENCE_PENDING": "Evidence pending",
    "REVIEW_REQUIRED": "Review required",
    "FEATURES_READY": "Financial evidence ready",
    "READY": "Assessment computation complete",
    "ILLUSTRATIVE": "Illustrative assessment",
    "COMPLETED": "Completed",
    "BLOCKED_MODEL_ARTIFACT": "Required model artifact unavailable",
    "MISSING_EVIDENCE": "Supporting evidence is missing",
    "AMBIGUOUS_AMOUNT": "Amount not confirmed",
    "CONTRADICTORY_DIRECTION": "Transaction direction conflicts with the evidence",
    "AMBIGUOUS_OWNERSHIP": "Ownership not confirmed",
    "UNSUPPORTED_TEMPLATE": "Source template requires review",
    "LOW_CONFIDENCE": "Extraction requires review",
    "CURRENCY_MISMATCH": "Currencies do not match",
    "IMPLAUSIBLE_AMOUNT": "Amount requires review",
    "AMBIGUOUS_MATCH": "Possible matching transaction requires review",
    "BALANCE_INCONSISTENCY": "Balance does not reconcile",
    "INVALID_LINK": "Linked transaction could not be verified",
    "RECEIPT": "Receipt",
    "SEND_MONEY": "Money sent",
    "CASH_IN": "Cash in",
    "CASH_OUT": "Cash out",
    "PAYMENT": "Payment",
    "REVERSAL": "Reversal",
    "TRANSFER": "Transfer",
    "CREDIT_SALE": "Credit sale",
    "RECEIVABLE": "Receivable",
    "PAYABLE": "Payable",
    "SETTLEMENT": "Settlement",
    "BALANCE_SNAPSHOT": "Balance observation",
    "OTHER": "Other",
    "INFLOW": "Inflow",
    "OUTFLOW": "Outflow",
    "NEUTRAL": "No cash-flow direction",
    "UNKNOWN": "Unknown",
    "UNTRAINED": "Untrained",
    "SYNTHETIC_DEMO": "Synthetic demonstration",
    "PUBLIC_DATASET_BENCHMARK": "Public dataset benchmark",
    "REAL_LINKED_OUTCOME_EXPERIMENT": "Experiment with linked borrower outcomes",
    "LATE_VERIFIED_BILLS": "Verified bills paid after their due dates",
    "LOWER_TAIL_LIQUIDITY": "Lower observed daily balance ratio",
    "complete_obligation_denominator_unknown": (
        "Payment history unavailable — complete obligation history is missing"
    ),
    "payment_record_incomplete; absence_is_not_nonpayment": (
        "Payment history is incomplete — missing records do not establish nonpayment"
    ),
    "no_verified_obligations_due": "No verified obligations due in this period",
    "no_verified_payments": "No verified payment records available",
    "incomplete_or_invalid_daily_balance_history": (
        "Balance history unavailable — complete valid daily balances are missing"
    ),
    "incomplete_cash_observation": "Cash-flow history is incomplete",
    "incomplete_cash_observation; totals cover verified evidence only": (
        "Cash-flow history is incomplete — totals cover verified evidence only"
    ),
    "CV uses attested complete days only; unobserved days omitted": (
        "Inflow variability uses complete observed days only; unobserved days are excluded"
    ),
    "observed_values_only": "Observed balances only; complete history is unavailable",
    "no_verified_coverage_supplied": "Verified observation coverage has not been supplied",
    "correction_requires_fresh_coverage_and_reassessment": (
        "Corrected evidence requires fresh coverage and a new assessment"
    ),
    "raw_model_candidates_require_review": "Extracted candidates require review",
    "line_level_regions_not_word_boxes": "Source locations identify lines, not individual words",
}

_SOURCE_LABELS: dict[str, str] = {
    "KHATA_IMAGE": "Informal ledger image",
    "UTILITY_DOCUMENT": "Utility document",
    "MOBILE_MONEY_SMS": "Mobile-money SMS",
    "PUBLIC_BENCHMARK": "Public benchmark record",
    "SYNTHETIC_FIXTURE": "Synthetic fixture",
}

_SYNTHETIC_PROVIDERS: dict[str, str] = {
    "SYNTHETIC-bKash-like": "Synthetic bKash-like SMS",
    "SYNTHETIC-Nagad-like": "Synthetic Nagad-like SMS",
}


def short_id(identifier: UUID | str) -> str:
    """Short display reference; full identifiers remain in technical evidence."""
    value = str(identifier)
    return f"{value[:8]}...{value[-5:]}" if len(value) > 16 else value


def money(value: Decimal | str | int | None, currency: str = "BDT") -> str:
    """Format an existing monetary value without substituting for unknown evidence."""
    if value is None:
        return "Unavailable"
    if isinstance(value, bool) or not isinstance(value, (Decimal, str, int)):
        raise TypeError("Money display requires a decimal, decimal string or integer")
    amount = Decimal(value)
    if not amount.is_finite():
        raise ValueError("Money display requires a finite amount")
    unit = "Tk" if currency == "BDT" else currency
    return f"{unit} {amount:,.2f}"


def humanize(code: str) -> str:
    """Provide a readable label; callers retain the original code in audit details."""
    if code in _LABELS:
        return _LABELS[code]
    if code in _SOURCE_LABELS:
        return _SOURCE_LABELS[code]
    readable = code.replace("_", " ")
    if readable.isupper():
        readable = readable.lower()
    return readable[:1].upper() + readable[1:]


def source_label(source_type: str, provider: str | None = None, synthetic: bool = False) -> str:
    """Use declared source scope or exact invented-provider markers, never inference."""
    if source_type == "MOBILE_MONEY_SMS" and provider in _SYNTHETIC_PROVIDERS:
        return _SYNTHETIC_PROVIDERS[provider]
    label = _SOURCE_LABELS.get(source_type, humanize(source_type))
    if synthetic and source_type != "SYNTHETIC_FIXTURE":
        return "Synthetic " + label[:1].lower() + label[1:]
    return label


def financial_summary(features: dict[str, dict]) -> tuple[str, str, str, str]:
    """Summarize one existing window; coverage labels do not certify score eligibility."""
    inflow = features.get("external_inflow_total", {}).get("value")
    observed = features.get("observed_day_share", {}).get("value")
    accepted = features.get("accepted_event_share", {}).get("value")
    if observed is None:
        coverage = "Unavailable"
    elif Decimal(str(observed)) < 1:
        coverage = "Insufficient"
    elif accepted is not None and Decimal(str(accepted)) < 1:
        coverage = "Needs review"
    else:
        coverage = "Observed"
    payment = "Available" if features.get("payment_punctuality", {}).get("value") is not None else "Unavailable"
    balance = "Available" if features.get("liquidity_floor", {}).get("value") is not None else "Unavailable"
    return money(inflow), coverage, payment, balance
