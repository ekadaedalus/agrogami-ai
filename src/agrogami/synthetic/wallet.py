"""SYNTHETIC wallet simulator emitting messages in the strict synthetic-provider-v1 SMS template.

Limits: the SMS templates encode no transaction limits and validate_event only rejects amounts
above Tk 1,000,000,000 (IMPLAUSIBLE_AMOUNT). The caps below are synthetic generator design
choices, not statements about any real provider's limits.
"""
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
from agrogami.ui.samples import synthetic_account

PROVIDERS = {"bkash": "SYNTHETIC-bKash-like", "nagad": "SYNTHETIC-Nagad-like"}
DHAKA = timezone(timedelta(hours=6))
PER_TRANSACTION_CAP = Decimal("25000.00")
MONTHLY_WALLET_CAP = Decimal("300000.00")  # per wallet, per 30-day period before t0, per direction
SEND_MONEY_FEE = Decimal("5.00")
CASH_OUT_RATE = Decimal("0.0185")
CENT = Decimal("0.01")

INFLOW_KINDS = {"Receipt", "Cash In", "Reversal"}
OUTFLOW_KINDS = {"Payment", "Send Money", "Cash Out"}


def period(anchor: datetime, when: datetime) -> int:
    """30-day period index counted back from the assessment anchor (run-date invariant)."""
    return (anchor - when) // timedelta(days=30)


def money(value: float | Decimal | int, step: Decimal = CENT) -> Decimal:
    return (Decimal(str(value)) / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step


def fee_for(kind: str, amount: Decimal) -> Decimal:
    if kind == "Send Money":
        return SEND_MONEY_FEE
    if kind == "Cash Out":
        return money(amount * CASH_OUT_RATE)
    return Decimal("0.00")


@dataclass(frozen=True)
class Message:
    """One SYNTHETIC wallet notification; `text` is exactly what intake receives."""
    provider: str
    wallet: str
    kind: str
    amount: Decimal
    fee: Decimal
    trx: str
    balance: Decimal
    counterparty: str
    when: datetime
    tag: str = ""
    due_date: date | None = None

    @property
    def text(self) -> str:
        local = self.when.astimezone(DHAKA)
        return (f"SYNTHETIC: {self.kind} Tk {self.amount:,.2f}. Fee Tk {self.fee:,.2f}. TrxID {self.trx}. "
                f"Balance Tk {self.balance:,.2f}. Counterparty {self.counterparty}. "
                f"Date {local:%Y-%m-%d}. Time {local:%H:%M:%S}+06:00.")

    def account_id(self, applicant_id: UUID) -> UUID:
        return synthetic_account(applicant_id, self.provider)

    def with_amount(self, amount: Decimal) -> "Message":
        """Edit only the amount, keeping the reported balance (used for perturbation checks)."""
        return replace(self, amount=amount)


class Wallet:
    def __init__(self, alias: str, provider: str, trx_prefix: str, opening: Decimal, anchor: datetime):
        self.alias, self.provider, self.trx_prefix, self.anchor = alias, provider, trx_prefix, anchor
        self.balance = money(opening)
        self.counter = 0
        self.monthly: dict[tuple[int, str], Decimal] = defaultdict(Decimal)
        self.last: datetime | None = None

    def can_post(self, kind: str, amount: Decimal, when: datetime) -> bool:
        direction = "in" if kind in INFLOW_KINDS else "out"
        month = period(self.anchor, when)
        if amount <= 0 or amount > PER_TRANSACTION_CAP:
            return False
        if self.monthly[(month, direction)] + amount > MONTHLY_WALLET_CAP:
            return False
        return direction == "in" or self.balance - amount - fee_for(kind, amount) >= 0

    def post(self, kind: str, amount: Decimal, counterparty: str, when: datetime, *, tag: str = "",
             due_date: date | None = None, fee: Decimal | None = None) -> Message | None:
        amount = money(amount)
        if kind not in INFLOW_KINDS | OUTFLOW_KINDS or not self.can_post(kind, amount, when):
            return None
        if self.last is not None and when <= self.last:
            when = self.last + timedelta(seconds=17)
        fee = fee_for(kind, amount) if fee is None else fee
        direction = "in" if kind in INFLOW_KINDS else "out"
        self.balance += (amount - fee) if direction == "in" else -(amount + fee)
        self.monthly[(period(self.anchor, when), direction)] += amount
        self.counter += 1
        self.last = when
        return Message(provider=self.provider, wallet=self.alias, kind=kind, amount=amount, fee=fee,
                       trx=f"{self.trx_prefix}{self.counter:05d}", balance=self.balance,
                       counterparty=counterparty, when=when, tag=tag, due_date=due_date)


def check_caps(messages: list[Message], anchor: datetime) -> None:
    """Assert generator caps and non-negative running balances on a finished message list."""
    totals: dict[tuple[str, int, str], Decimal] = defaultdict(Decimal)
    for m in messages:
        if m.tag == "duplicate_delivery":
            continue
        if not 0 < m.amount <= PER_TRANSACTION_CAP or m.balance < 0:
            raise ValueError("synthetic message outside generator caps")
        direction = "in" if m.kind in INFLOW_KINDS else "out"
        totals[(m.wallet, period(anchor, m.when), direction)] += m.amount
    if any(total > MONTHLY_WALLET_CAP for total in totals.values()):
        raise ValueError("synthetic wallet exceeds monthly generator cap")
