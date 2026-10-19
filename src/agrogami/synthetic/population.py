"""SYNTHETIC labelled borrower population for the demo risk model.

Every borrower is a fictional microbusiness with latent traits. Their 92 days of wallet messages
are delivered through ApplicationService.sms_intake into a per-borrower in-memory SQLite ledger,
bill due dates are appended as reviewer corrections, and features come from the real feature
engine. Labels come from a documented latent-trait rule with an unobserved driver and label
noise; they are synthetic and say nothing about any real person's repayment.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from math import exp
from pathlib import Path
import tempfile
from uuid import UUID, uuid5, NAMESPACE_URL
import numpy as np
from agrogami.application import ApplicationService
from agrogami.schemas import FeatureSnapshot, ValidationStatus as V
from agrogami.storage import Store
from agrogami.synthetic.ledger import attested_coverage, corroborate_bills, ingest, own_accounts
from agrogami.synthetic.wallet import PER_TRANSACTION_CAP, PROVIDERS, Message, Wallet, check_caps, money

GENERATOR_VERSION = "synthetic-population-v1"
DEFAULT_SEED = 20261016
DEFAULT_N = 2000
HISTORY_DAYS = 92
LABEL_NOISE = 0.05
# Chosen so the expected observed (post-noise) default rate is ~15% under the trait distributions
# below (latent ~11%); see DATA_CARD.md. The realised rate is reported per generated population.
INTERCEPT = -3.5
LABEL_WEIGHTS = {"instability": 1.2, "low_margin": 1.0, "indiscipline": 0.9, "hidden_shock": 2.0, "hidden_burden": 0.6}
REVIEWER = "reviewer-synthetic-generator"
# Bill schedule as days before t0: every 30-day window holds at least one due date of each bill.
BILLS = {"rent": (88, 58, 28), "electricity": (80, 50, 20), "internet": (72, 42, 14)}
MAX_LATE_DAYS = 12


@dataclass(frozen=True)
class Traits:
    monthly_income: float  # typical digital customer receipts per 30 days, Tk
    stability: float       # 0..1, regularity of customer receipts (observed via inflow CV)
    margin: float          # share of receipts retained after business spending (observed via net flow)
    discipline: float      # probability a bill is paid by its due date (observed via punctuality)
    activity: float        # mean customer receipts per open day
    second_wallet: bool
    hidden_shock: bool     # UNOBSERVED: adverse shock after the assessment date
    hidden_burden: float   # UNOBSERVED: off-ledger informal debt burden (z-score)


def sample_id(seed: int, index: int) -> str:
    return f"SYNTHETIC-POP-{seed}-{index:05d}"


def applicant_id(seed: int, index: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"agrogami-synthetic:population:{GENERATOR_VERSION}:{seed}:{index}")


def rng_for(seed: int, index: int, stream: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([seed, index, stream]))


def draw_traits(rng: np.random.Generator) -> Traits:
    return Traits(monthly_income=float(np.clip(rng.lognormal(np.log(65000), 0.45), 20000, 220000)),
                  stability=float(rng.beta(6, 3)), margin=float(np.clip(rng.normal(0.12, 0.09), -0.2, 0.4)),
                  discipline=float(rng.beta(8, 1.5)), activity=float(rng.uniform(0.8, 2.4)),
                  second_wallet=bool(rng.random() < 0.35), hidden_shock=bool(rng.random() < 0.10),
                  hidden_burden=float(rng.normal(0, 1)))


def latent_logit(t: Traits) -> float:
    """Documented labelling rule (DATA_CARD.md); standardised around the trait means."""
    w = LABEL_WEIGHTS
    return (INTERCEPT + w["instability"] * (0.66 - t.stability) / 0.15 + w["low_margin"] * (0.12 - t.margin) / 0.09
            + w["indiscipline"] * (0.84 - t.discipline) / 0.10 + w["hidden_shock"] * float(t.hidden_shock)
            + w["hidden_burden"] * t.hidden_burden)


def default_probability(t: Traits) -> float:
    return 1 / (1 + exp(-latent_logit(t)))


def draw_label(rng: np.random.Generator, t: Traits) -> tuple[int, int, bool]:
    latent = int(rng.random() < default_probability(t))
    flipped = bool(rng.random() < LABEL_NOISE)
    return (1 - latent if flipped else latent), latent, flipped


def _at(day_start: datetime, rng: np.random.Generator, start_hour: int = 9, end_hour: int = 20) -> datetime:
    # Dhaka business hours (UTC+06:00) stay on the same UTC calendar day.
    seconds = int(rng.integers((start_hour - 6) * 3600, (end_hour - 6) * 3600))
    return day_start + timedelta(seconds=seconds)


def borrower_messages(rng: np.random.Generator, t: Traits, t0: datetime, index: int) -> list[Message]:
    tag = f"P{index:05d}"
    bk = Wallet(f"SYN-{tag}-BK", PROVIDERS["bkash"], f"SYN{tag}B", money(t.monthly_income * rng.uniform(0.08, 0.25), Decimal(10)), t0)
    ng = Wallet(f"SYN-{tag}-NG", PROVIDERS["nagad"], f"SYN{tag}N", money(t.monthly_income * rng.uniform(0.03, 0.1), Decimal(10)), t0) if t.second_wallet else None
    customers = [f"SYN-CUST-{tag}-{i:02d}" for i in range(1, 31)]
    suppliers = [f"SYN-SUP-{tag}-{i}" for i in range(1, 5)]
    workers = [f"SYN-WORKER-{tag}-{i}" for i in range(1, 3)]
    agent = f"SYN-AGENT-{tag}"
    rent = money(t.monthly_income * rng.uniform(0.07, 0.11), Decimal(100))
    electricity = [money(t.monthly_income * rng.uniform(0.015, 0.025), Decimal(10)) for _ in range(3)]
    internet = money(rng.uniform(500, 1200), Decimal(50))
    wage = money(t.monthly_income * rng.uniform(0.12, 0.2) / 4.3 / len(workers), Decimal(50))
    bill_days: dict[int, list[tuple[str, Decimal, int]]] = {}
    for name, offsets in BILLS.items():
        for cycle, due_offset in enumerate(offsets):
            amount = rent if name == "rent" else internet if name == "internet" else electricity[cycle]
            if rng.random() < t.discipline:
                pay_offset = due_offset + int(rng.integers(0, 4))
            else:
                pay_offset = due_offset - min(MAX_LATE_DAYS, 1 + int(rng.geometric(0.35)))
            bill_days.setdefault(max(1, pay_offset), []).append((name, amount, due_offset))
    messages: list[Message] = []
    pool = Decimal(0)  # business spending owed out of receipts at (1 - margin)
    spend_share = Decimal(str(round(1 - t.margin, 4)))

    def outflow(wallet: Wallet, kind: str, amount: Decimal, counterparty: str, when: datetime, **extra) -> Message | None:
        needed = amount + (Decimal("5") if kind == "Send Money" else Decimal(0))
        if wallet.balance < needed:
            top_up = money(min(PER_TRANSACTION_CAP, needed - wallet.balance + Decimal(500)), Decimal(10))
            cash = wallet.post("Cash In", top_up, agent, when - timedelta(minutes=7))
            if cash:
                messages.append(cash)
        posted = wallet.post(kind, amount, counterparty, when, **extra)
        if posted:
            messages.append(posted)
        return posted

    for offset in range(HISTORY_DAYS, 0, -1):
        day = t0 - timedelta(days=offset)
        planned: list[tuple[datetime, str, object]] = []
        open_day = offset % 7 != 3
        if open_day and rng.random() >= 0.05 + 0.45 * (1 - t.stability) ** 1.5:
            day_target = t.monthly_income / 26 * rng.lognormal(0, 0.6 * (1 - t.stability))
            count = 1 + int(rng.poisson(max(t.activity - 1, 0.01)))
            for _ in range(count):
                amount = day_target / count * rng.lognormal(0, 0.25 + 0.6 * (1 - t.stability))
                planned.append((_at(day, rng), "receipt", money(min(max(amount, 50), 25000), Decimal(10))))
            if rng.random() < 0.02:
                planned.append((_at(day, rng), "receipt", money(min(t.monthly_income * rng.uniform(0.08, 0.2), 24000), Decimal(100))))
        for name, amount, due_offset in bill_days.get(offset, []):
            planned.append((_at(day, rng, 10, 18), "bill", (name, amount, due_offset)))
        if offset % 7 == 1:
            for worker in workers:
                planned.append((_at(day, rng, 17, 20), "wage", worker))
        if open_day and rng.random() < 0.35:
            planned.append((_at(day, rng, 11, 19), "supplier", rng.choice(suppliers)))
        if offset % 7 == 5 and rng.random() < 0.3:
            planned.append((_at(day, rng, 18, 20), "cash_out", None))
        for when, kind, detail in sorted(planned, key=lambda item: item[0]):
            if kind == "receipt":
                wallet = ng if ng is not None and rng.random() < 0.3 else bk
                posted = wallet.post("Receipt", detail, rng.choice(customers), when)
                if posted:
                    messages.append(posted)
                    pool += posted.amount * spend_share
            elif kind == "bill":
                name, amount, due_offset = detail
                posted = outflow(bk, "Payment", amount, f"SYN-BILLER-{name.upper()}", when, tag=f"bill:{name}",
                                 due_date=(t0 - timedelta(days=due_offset)).date())
                if posted:
                    pool -= posted.amount
            elif kind == "wage":
                posted = outflow(bk, "Send Money", wage, detail, when)
                if posted:
                    pool -= posted.amount
            elif kind == "supplier" and pool > 500:
                amount = money(min(float(pool) * rng.uniform(0.4, 0.9), 24000), Decimal(10))
                posted = outflow(bk, "Payment", amount, detail, when)
                if posted:
                    pool -= posted.amount
            elif kind == "cash_out":
                amount = money(t.monthly_income * rng.uniform(0.02, 0.06), Decimal(100))
                posted = bk.post("Cash Out", amount, agent, when)
                if posted:
                    messages.append(posted)
    check_caps(messages, t0)
    return sorted(messages, key=lambda m: (m.when, m.trx))


def process_borrower(seed: int, index: int, t0: datetime, model_window: int = 90) -> dict:
    """Generate one borrower and run it through intake, ledger corrections and features."""
    traits = draw_traits(rng_for(seed, index, 0))
    label, latent, flipped = draw_label(rng_for(seed, index, 1), traits)
    messages = borrower_messages(rng_for(seed, index, 2), traits, t0, index)
    applicant = applicant_id(seed, index)
    with tempfile.TemporaryDirectory(prefix="agrogami-synthetic-") as scratch:
        store = Store("sqlite://")
        try:
            service = ApplicationService(store, Path(scratch))
            service.register_accounts(applicant, own_accounts(applicant, {m.wallet: m.provider for m in messages}),
                                      "SYNTHETIC attested complete own-wallet list", REVIEWER)
            results = ingest(service, applicant, messages)
            corroborate_bills(results, lambda event_id, changes, reason: store.correct(
                event_id, changes, reason=reason, reviewer_alias=REVIEWER))
            coverage = attested_coverage(applicant, t0, HISTORY_DAYS)
            snapshots = service.features(applicant, t0, coverage)
            events = store.events(applicant)
        finally:
            store.engine.dispose()
    superseded = {e.supersedes_event_id for e in events if e.supersedes_event_id}
    current = [e for e in events if e.event_id not in superseded]
    return {"sample_id": sample_id(seed, index), "index": index, "applicant_id": str(applicant),
            "label": label, "latent_label": latent, "label_flipped": flipped,
            "latent_default_probability": round(default_probability(traits), 6), "traits": asdict(traits),
            "sms_count": len(messages),
            "current_event_status": {s.value: sum(e.validation_status == s for e in current) for s in V},
            "review_reasons": sorted({r.value for e in current for r in e.review_reason}),
            # The model-window snapshot is the bridge input; every window also travels as compact values.
            "model_window": model_window, "model_snapshot": snapshots[model_window].model_dump_json(),
            "features": {str(window): compact_features(snapshot) for window, snapshot in snapshots.items()}}


def compact_features(snapshot: FeatureSnapshot) -> dict[str, object]:
    """Scalar feature values (null stays null) for data-card summaries; no event identifiers."""
    out = {}
    for name, feature in snapshot.features.items():
        if isinstance(feature.value, (dict, tuple)):
            continue
        out[name] = None if feature.value is None else float(feature.value)
    return out
