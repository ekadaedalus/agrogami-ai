"""SYNTHETIC applicant "Rahim": a fictional furniture workshop owner in Dhaka.

Rahim is not part of the training population. His two wallets are registered as his own, his
92 days of messages carry running balances, and the fixture contains exactly one duplicate SMS,
one payment with its linked reversal and one own bKash-like → Nagad-like transfer, plus a
Tk 500 receipt used by the perturbation check. His score is never set here: it comes from the
trained model through ApplicationService.assessment.
"""
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import numpy as np
from agrogami.application import ApplicationService
from agrogami.assessment import AssessmentSnapshot
from agrogami.schemas import CanonicalEvent, FeatureSnapshot
from agrogami.storage import Store
from agrogami.synthetic.identities import RAHIM_APPLICANT_ID
from agrogami.synthetic.ledger import attested_coverage, corroborate_bills, ingest, own_accounts
from agrogami.synthetic.wallet import PROVIDERS, Message, Wallet, check_caps, money

FIXTURE_VERSION = "synthetic-rahim-v1"
RAHIM_SEED = 7310
HISTORY_DAYS = 92
BKASH_ALIAS, NAGAD_ALIAS = "SYN-010-RAHIM-BK", "SYN-010-RAHIM-NG"
LARGE_ORDERS = {84: Decimal("14500"), 61: Decimal("18000"), 39: Decimal("12000"), 17: Decimal("21500")}
RENT = {88: Decimal("11000"), 58: Decimal("11000"), 28: Decimal("11000")}
ELECTRICITY = {80: Decimal("2340"), 50: Decimal("2180"), 20: Decimal("2460")}
INTERNET = {72: Decimal("1000"), 42: Decimal("1000"), 14: Decimal("1000")}
DUPLICATE_DAY, REVERSAL_DAY, TRANSFER_DAY, PERTURBATION_DAY = 25, 10, 33, 6
EDGE_TAGS = ("duplicate_original", "duplicate_delivery", "reversed_payment", "reversal",
             "own_transfer_out", "own_transfer_in", "perturbation_target")


def _clock(day: datetime, hour: int, minute: int, second: int = 0) -> datetime:
    """Dhaka wall-clock time (UTC+06:00) on a UTC day; business hours stay on that UTC day."""
    return day + timedelta(hours=hour - 6, minutes=minute, seconds=second)


def rahim_messages(t0: datetime) -> list[Message]:
    rng = np.random.default_rng(RAHIM_SEED)
    bk = Wallet(BKASH_ALIAS, PROVIDERS["bkash"], "SYNRB", Decimal("30000"), t0)
    ng = Wallet(NAGAD_ALIAS, PROVIDERS["nagad"], "SYNRN", Decimal("7500"), t0)
    customers = [f"SYN-CUST-R{i:02d}" for i in range(1, 46)]
    suppliers = ["SYN-SUP-TIMBER", "SYN-SUP-HARDWARE", "SYN-SUP-VARNISH"]
    out: list[Message] = []

    def post(wallet: Wallet, *args, **kwargs) -> Message:
        message = wallet.post(*args, **kwargs)
        if message is None:
            raise ValueError("Rahim fixture exceeded a synthetic generator cap or balance")
        out.append(message)
        return message

    since_supplier = Decimal(0)  # bKash receipts not yet followed by a supplier payment
    for offset in range(HISTORY_DAYS, 0, -1):
        day = t0 - timedelta(days=offset)
        open_day = offset % 7 != 3
        # Each wallet's messages are posted in wall-clock order so running balances chain.
        if offset == PERTURBATION_DAY:
            post(bk, "Receipt", Decimal("500"), "SYN-CUST-R07", _clock(day, 8, 5), tag="perturbation_target")
        if offset == REVERSAL_DAY:
            post(bk, "Payment", Decimal("3450"), "SYN-SUP-FOAM", _clock(day, 8, 20), tag="reversed_payment")
            post(bk, "Reversal", Decimal("3450"), "SYN-SUP-FOAM", _clock(day, 8, 50), tag="reversal")
        if offset == DUPLICATE_DAY:
            original = post(bk, "Receipt", Decimal("2750"), "SYN-CUST-R12", _clock(day, 8, 40), tag="duplicate_original")
            since_supplier += original.amount
            out.append(replace(original, tag="duplicate_delivery"))  # same SMS (same TrxID) delivered twice
        if open_day:
            hours = sorted(rng.choice(np.arange(9, 20), size=int(rng.integers(2, 5)), replace=False))
            for hour in hours:
                small = rng.random() < 0.7
                amount = money(rng.uniform(300, 1800), Decimal(10)) if small else money(rng.uniform(1800, 5000), Decimal(50))
                wallet = ng if rng.random() < 0.2 else bk
                received = post(wallet, "Receipt", amount, str(rng.choice(customers)),
                                _clock(day, int(hour), int(rng.integers(0, 50)), int(rng.integers(0, 60))))
                since_supplier += received.amount if wallet is bk else 0
        if offset in LARGE_ORDERS:
            since_supplier += post(bk, "Receipt", LARGE_ORDERS[offset], "SYN-CUST-R-BULK", _clock(day, 19, 55)).amount
        if offset == TRANSFER_DAY:
            post(bk, "Send Money", Decimal("8000"), NAGAD_ALIAS, _clock(day, 20, 10), tag="own_transfer_out")
            post(ng, "Receipt", Decimal("8000"), BKASH_ALIAS, _clock(day, 20, 10, 40), tag="own_transfer_in")
        for schedule, name, wallet, biller in ((RENT, "rent", bk, "SYN-BILLER-RENT"),
                                               (ELECTRICITY, "electricity", bk, "SYN-BILLER-ELECTRICITY"),
                                               (INTERNET, "internet", ng, "SYN-BILLER-INTERNET")):
            for due_offset, amount in schedule.items():
                if due_offset + 1 == offset:  # every bill is paid the day before it falls due
                    post(wallet, "Payment", amount, biller, _clock(day, 20, 30), tag=f"bill:{name}",
                         due_date=(t0 - timedelta(days=due_offset)).date())
        if offset % 3 == 0 and open_day and since_supplier > 0:
            amount = money(min(float(since_supplier) * rng.uniform(0.45, 0.55), 24000), Decimal(10))
            post(bk, "Payment", amount, str(rng.choice(suppliers)), _clock(day, 20, 45))
            since_supplier = Decimal(0)
        if offset % 7 == 1:
            for worker in ("SYN-WORKER-R1", "SYN-WORKER-R2"):
                post(bk, "Send Money", Decimal("3000"), worker, _clock(day, 21, 0 if worker.endswith("1") else 5))
        if offset % 7 == 5:
            post(bk, "Cash Out", Decimal("2000"), "SYN-AGENT-R07", _clock(day, 21, 20))
        if offset % 10 == 4 and ng.balance > Decimal("12000"):
            post(ng, "Payment", money(ng.balance * Decimal("0.4"), Decimal(10)), "SYN-SUP-VARNISH", _clock(day, 21, 30))
    check_caps(out, t0)
    return sorted(out, key=lambda m: (m.when, m.trx, m.tag == "duplicate_delivery"))


def perturbed_messages(messages: list[Message], new_amount: Decimal = Decimal("5000")) -> tuple[list[Message], Message, Message]:
    """Change the Tk 500 receipt to Tk 5,000 while its reported balance stays unchanged."""
    target = next(m for m in messages if m.tag == "perturbation_target")
    if target.amount != Decimal("500"):
        raise ValueError("perturbation target must be the Tk 500 receipt")
    changed = target.with_amount(new_amount)
    return [changed if m is target else m for m in messages], target, changed


def build_rahim(service: ApplicationService, t0: datetime, *, messages: list[Message] | None = None,
                reviewer: str = "reviewer-demo", save_snapshots: bool = True) -> dict:
    """Register wallets, ingest SMS, record reviewer links/dates, compute features and assess."""
    applicant = RAHIM_APPLICANT_ID
    messages = rahim_messages(t0) if messages is None else messages
    service.register_accounts(applicant, own_accounts(applicant, {BKASH_ALIAS: PROVIDERS["bkash"], NAGAD_ALIAS: PROVIDERS["nagad"]}),
                              "SYNTHETIC applicant attests these are his only two wallets", reviewer)
    results = ingest(service, applicant, messages)
    jobs = {m.tag: job for m, job in results if m.tag}
    reversal, payment = jobs["reversal"].event_id, jobs["reversed_payment"].event_id
    service.review(reversal, {"direction": "INFLOW", "reversal_of_event_id": payment},
                   "SYNTHETIC reviewer: reversal SMS returns the same-day foam supplier payment", reviewer)
    corroborate_bills(results, lambda event_id, changes, reason: service.review(event_id, changes, reason, reviewer))
    coverage = attested_coverage(applicant, t0, HISTORY_DAYS)
    snapshots = service.features(applicant, t0, coverage)
    if save_snapshots:
        for snapshot in snapshots.values():
            service.store.save(snapshot)
    pending = service.records.assessments(applicant)[-1]
    window = service.model.artifact.window_days if service.model is not None else 30
    assessment = service.assessment(applicant_id=applicant, t0=t0, coverage=coverage, window_days=window,
                                    previous_id=pending.assessment_id)
    target_job = jobs["perturbation_target"]
    target = service.store.get(CanonicalEvent, target_job.event_id) if target_job.event_id else None
    return {"applicant_id": str(applicant), "fixture_version": FIXTURE_VERSION, "sms_count": len(messages),
            "assessment": assessment, "snapshots": snapshots, "target_event": target,
            "edge_case_event_ids": {tag: str(jobs[tag].event_id) for tag in EDGE_TAGS if tag in jobs}}


def run_scenario(workdir: Path, t0: datetime, messages: list[Message], *, model, calibrator,
                 explanation_provider=None) -> dict:
    """Rahim's full candidate → event → features → probability → score path in an isolated ledger."""
    workdir.mkdir(parents=True, exist_ok=False)
    store = Store("sqlite:///" + (workdir / "scenario.db").as_posix())
    try:
        service = ApplicationService(store, workdir / "private", model=model, calibrator=calibrator,
                                     explanation_provider=explanation_provider)
        built = build_rahim(service, t0, messages=messages, save_snapshots=False)
    finally:
        store.engine.dispose()
    assessment, target = built["assessment"], built["target_event"]
    return {"assessment_status": assessment.status.value, "raw_probability": assessment.raw_probability,
            "calibrated_probability": assessment.calibrated_probability, "display_score": assessment.display_score,
            "target_event_status": target.validation_status.value,
            "target_event_flags": [reason.value for reason in target.review_reason],
            "target_amount": str(target.amount), "target_reported_balance": str(target.balance),
            "withheld_because": [item for item in assessment.limitations if "withheld" in item.lower()]}


def perturbation_check(workdir: Path, t0: datetime, *, model, calibrator, explanation_provider=None) -> dict:
    clean = rahim_messages(t0)
    changed, original, perturbed = perturbed_messages(clean)
    before = run_scenario(workdir / "clean", t0, clean, model=model, calibrator=calibrator,
                          explanation_provider=explanation_provider)
    after = run_scenario(workdir / "perturbed", t0, changed, model=model, calibrator=calibrator,
                         explanation_provider=explanation_provider)
    return {"original_sms": original.text, "perturbed_sms": perturbed.text, "before": before, "after": after}


def summarize(assessment: AssessmentSnapshot, snapshots: dict[int, FeatureSnapshot]) -> dict:
    """Plain values for printing; reason codes are the stored TreeSHAP contributions, ranked."""
    shap = assessment.explanation_metadata
    ranked = sorted(shap.contributions.items(), key=lambda item: -abs(item[1])) if shap else []
    return {"assessment_id": str(assessment.assessment_id), "status": assessment.status.value,
            "assessment_time": assessment.assessment_time.isoformat(),
            "model_validation_scope": assessment.model_validation_scope.value,
            "raw_probability": assessment.raw_probability, "calibrated_probability": assessment.calibrated_probability,
            "display_score": assessment.display_score, "calibrator_version": assessment.calibrator_version,
            "treeshap_reason_codes": [{"feature": name, "raw_margin_contribution": round(value, 6),
                                       "direction": "raises modelled risk" if value > 0 else "lowers modelled risk"}
                                      for name, value in ranked],
            "evidence_reasons": [reason.code for reason in assessment.reasons],
            "windows": {window: {name: (None if snapshots[window].features[name].value is None
                                        else str(snapshots[window].features[name].value))
                                 for name in ("net_external_cash_flow", "inflow_cv", "payment_punctuality",
                                              "coverage_days", "accepted_event_share")}
                        for window in sorted(snapshots)}}
