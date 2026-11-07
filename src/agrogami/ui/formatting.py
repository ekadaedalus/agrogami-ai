"""Presentation preserves unknowns."""
from decimal import Decimal
from uuid import UUID
from agrogami.ui.i18n import has, t


def display(value: object, reasons: tuple[str, ...] = ()) -> str:
    if value is None:
        return t("fmt.unavailable_because", reasons=", ".join(reasons) if reasons else t("fmt.insufficient_support"))
    return str(value)


# English and Bangla labels for codes, source types and synthetic providers live in i18n.STRINGS
# ("label.*", "source.*", "provider.*"); the raw codes stay visible in audit codes and technical evidence.
_SYNTHETIC_PROVIDERS: tuple[str, ...] = ("SYNTHETIC-bKash-like", "SYNTHETIC-Nagad-like")


def short_id(identifier: UUID | str) -> str:
    """Short display reference; full identifiers remain in technical evidence."""
    value = str(identifier)
    return f"{value[:8]}...{value[-5:]}" if len(value) > 16 else value


def money(value: Decimal | str | int | None, currency: str = "BDT") -> str:
    """Format an existing monetary value without substituting for unknown evidence."""
    if value is None:
        return t("fmt.unavailable")
    if isinstance(value, bool) or not isinstance(value, (Decimal, str, int)):
        raise TypeError("Money display requires a decimal, decimal string or integer")
    amount = Decimal(value)
    if not amount.is_finite():
        raise ValueError("Money display requires a finite amount")
    unit = "Tk" if currency == "BDT" else currency
    return f"{unit} {amount:,.2f}"


def humanize(code: str) -> str:
    """Provide a readable label; callers retain the original code in audit details."""
    for prefix in ("label.", "source."):
        if has(prefix + code):
            return t(prefix + code)
    readable = code.replace("_", " ")
    if readable.isupper():
        readable = readable.lower()
    return readable[:1].upper() + readable[1:]


def source_label(source_type: str, provider: str | None = None, synthetic: bool = False) -> str:
    """Use declared source scope or exact invented-provider markers, never inference."""
    if source_type == "MOBILE_MONEY_SMS" and provider in _SYNTHETIC_PROVIDERS:
        return t("provider." + provider)
    label = humanize(source_type)
    if synthetic and source_type != "SYNTHETIC_FIXTURE":
        return t("fmt.synthetic_source", label=label[:1].lower() + label[1:])
    return label


def financial_summary(features: dict[str, dict]) -> tuple[str, str, str, str]:
    """Summarize one existing window; coverage labels do not certify score eligibility."""
    inflow = features.get("external_inflow_total", {}).get("value")
    observed = features.get("observed_day_share", {}).get("value")
    accepted = features.get("accepted_event_share", {}).get("value")
    if observed is None:
        coverage = t("fmt.unavailable")
    elif Decimal(str(observed)) < 1:
        coverage = t("fmt.insufficient")
    elif accepted is not None and Decimal(str(accepted)) < 1:
        coverage = t("fmt.needs_review")
    else:
        coverage = t("fmt.observed")
    available, unavailable = t("fmt.available"), t("fmt.unavailable")
    payment = available if features.get("payment_punctuality", {}).get("value") is not None else unavailable
    balance = available if features.get("liquidity_floor", {}).get("value") is not None else unavailable
    return money(inflow), coverage, payment, balance
