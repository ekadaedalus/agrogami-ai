"""Strict invented provider-like templates. No production-provider claim."""
import re
from datetime import datetime
from decimal import Decimal
from agrogami.schemas import (Contract, Source, CandidateExtraction, CandidateField, Provenance,
                              ReviewReason as R, ValidationStatus as V, TransactionType as T)


class SMSResult(Contract):
    candidate: CandidateExtraction
    status: V
    reasons: tuple[R, ...] = ()
    non_transaction: bool = False


KINDS = {"Receipt": T.RECEIPT, "Send Money": T.SEND_MONEY, "Cash In": T.CASH_IN,
         "Cash Out": T.CASH_OUT, "Payment": T.PAYMENT, "Reversal": T.REVERSAL}
NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"
PATTERN = re.compile(
    r"SYNTHETIC: (?P<transaction_type>Receipt|Send Money|Cash In|Cash Out|Payment|Reversal) "
    + rf"Tk (?P<amount>{NUMBER})\. Fee Tk (?P<fee>{NUMBER})\. "
    + r"TrxID (?P<transaction_reference>[A-Z0-9-]+)\."
    + rf"(?: Balance Tk (?P<balance>{NUMBER})\.)?"
    + r"(?: Counterparty (?P<counterparty>[A-Za-z0-9_-]+)\.)?"
    + r"(?: Date (?P<date>\d{4}-\d{2}-\d{2})\. Time (?P<time>\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2})\.)?"
)


def parse_sms(text: str, source: Source, provider: str) -> SMSResult:
    fields: dict[str, CandidateField] = {}
    template = "synthetic-provider-v1"
    supported = provider in {"SYNTHETIC-bKash-like", "SYNTHETIC-Nagad-like"}
    non_transaction = text == "SYNTHETIC: Promotional notice. No transaction."
    match = PATTERN.fullmatch(text) if supported else None
    reasons: tuple[R, ...] = ()
    if match:
        for name, raw in match.groupdict().items():
            if raw is None:
                continue
            normalized = str(Decimal(raw.replace(",", ""))) if name in {"amount", "fee", "balance"} else raw
            if name == "transaction_type":
                normalized = KINDS[raw].value
            fields[name] = CandidateField(raw_value=raw, normalized_value=normalized, confidence=Decimal(1),
                location=Provenance(source_hash=source.source_hash, span_start=match.start(name),
                                    span_end=match.end(name), provider=provider, template=template),
                parser_name="deterministic-synthetic-sms", parser_version="1.0")
        if "date" in fields:
            try:
                timestamp = datetime.fromisoformat(fields["date"].raw_value + "T" + fields["time"].raw_value)
                date_field = fields["date"]
                fields["event_timestamp"] = CandidateField.model_validate(date_field.model_dump() | {
                    "raw_value": text[match.start("date"):match.end("time")],
                    "normalized_value": timestamp.isoformat(),
                    "location": Provenance(source_hash=source.source_hash, span_start=match.start("date"),
                        span_end=match.end("time"), provider=provider, template=template)})
            except ValueError:
                reasons = (R.MISSING_EVIDENCE,)
        else:
            reasons = (R.MISSING_EVIDENCE,)
    elif not non_transaction:
        reasons = (R.UNSUPPORTED_TEMPLATE,)
        # Preserve the full original as candidate evidence; never guess its financial facts.
        if text:
            fields["unparsed"] = CandidateField(raw_value=text, normalized_value=None, confidence=Decimal(0),
                location=Provenance(source_hash=source.source_hash, span_start=0, span_end=len(text),
                                    provider=provider, template="unsupported"),
                parser_name="deterministic-synthetic-sms", parser_version="1.0")
    return SMSResult(candidate=CandidateExtraction(source_id=source.source_id, fields=fields),
                     status=V.NEEDS_REVIEW if reasons else V.ACCEPTED, reasons=reasons,
                     non_transaction=non_transaction)
