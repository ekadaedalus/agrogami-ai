"""Safe invented messages, never labeled as real provider evidence."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid5, NAMESPACE_URL

SCENARIOS = {"External inflow": "Receipt", "External outflow": "Payment", "Send money": "Send Money",
             "Cash in": "Cash In", "Cash out": "Cash Out", "Reversal requiring linking": "Reversal"}


def synthetic_account(applicant_id: UUID, provider: str) -> UUID:
    """Explicit invented account stable across submissions of this demo context."""
    return uuid5(NAMESPACE_URL, f"agrogami-synthetic-account:{applicant_id}:{provider}")

def sample_sms(scenario: str, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(timezone.utc)) - timedelta(days=1)
    return (f"SYNTHETIC: {SCENARIOS[scenario]} Tk 100.00. Fee Tk 0.00. TrxID DEMO1. "
            f"Date {timestamp:%Y-%m-%d}. Time {timestamp:%H:%M:%S}+00:00.")
