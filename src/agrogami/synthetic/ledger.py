"""Run SYNTHETIC wallet messages through the real intake → ledger → review → feature path."""
from datetime import date, datetime, timedelta, timezone
from typing import Callable
from uuid import UUID
from agrogami.application import ApplicationService, Job, OwnAccount
from agrogami.schemas import CanonicalEvent, Coverage, utcnow
from agrogami.synthetic.wallet import DHAKA, Message
from agrogami.ui.samples import synthetic_account


def next_assessment_time(now: datetime | None = None, *, margin: timedelta = timedelta(hours=2)) -> datetime:
    """First UTC midnight at least `margin` after now.

    Complete-day coverage needs a midnight scoring boundary, and as-of rules only admit evidence
    recorded before it, so a scoreable synthetic assessment is anchored at the next midnight.
    """
    now = (now or utcnow()).astimezone(timezone.utc)
    return datetime.combine((now + margin).date() + timedelta(days=1), datetime.min.time(), timezone.utc)


def own_accounts(applicant_id: UUID, wallets: dict[str, str]) -> tuple[OwnAccount, ...]:
    """wallets maps wallet alias -> provider."""
    return tuple(OwnAccount(account_id=synthetic_account(applicant_id, provider), provider=provider,
                            wallet_alias=alias) for alias, provider in sorted(wallets.items()))


def ingest(service: ApplicationService, applicant_id: UUID, messages: list[Message]) -> list[tuple[Message, Job]]:
    """Deliver messages in arrival order through ApplicationService.sms_intake."""
    return [(m, service.sms_intake(applicant_id=applicant_id, account_id=m.account_id(applicant_id),
                                   text=m.text, provider=m.provider)) for m in messages]


def corroborate_bills(results: list[tuple[Message, Job]],
                      correct: Callable[[UUID, dict[str, object], str], CanonicalEvent]) -> list[CanonicalEvent]:
    """Append reviewer-corroborated due/payment dates for bill payments (SMS carries no due date)."""
    corrected = []
    for message, job in results:
        if message.due_date is not None and job.event_id is not None:
            paid = message.when.astimezone(DHAKA).date()
            corrected.append(correct(job.event_id, {"due_date": message.due_date, "payment_date": paid},
                                     f"SYNTHETIC {message.tag} statement corroborates due date"))
    return corrected


def attested_coverage(applicant_id: UUID, t0: datetime, days: int, *, known_at: datetime | None = None) -> Coverage:
    """Caller-attested complete SMS and obligation coverage for the synthetic history (no balance days)."""
    complete = frozenset(t0.date() - timedelta(days=i) for i in range(1, days + 1))
    return Coverage(applicant_id=applicant_id, known_at=known_at or utcnow(), observed_days=complete,
                    obligation_complete_days=complete)


def history_days(t0: datetime, days: int) -> list[date]:
    return [t0.date() - timedelta(days=i) for i in range(days, 0, -1)]
