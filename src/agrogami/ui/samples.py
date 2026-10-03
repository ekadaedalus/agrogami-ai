"""Safe invented messages, never labeled as real provider evidence."""
from datetime import datetime, timedelta, timezone

SCENARIOS = {"External inflow": "Receipt", "External outflow": "Payment", "Send money": "Send Money",
             "Cash in": "Cash In", "Cash out": "Cash Out", "Reversal requiring linking": "Reversal"}

def sample_sms(scenario: str, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(timezone.utc)) - timedelta(days=1)
    return (f"SYNTHETIC: {SCENARIOS[scenario]} Tk 100.00. Fee Tk 0.00. TrxID DEMO1. "
            f"Date {timestamp:%Y-%m-%d}. Time {timestamp:%H:%M:%S}+00:00.")
