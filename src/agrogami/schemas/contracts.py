"""Immutable, versioned evidence contracts. Money serializes as decimal strings."""
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

Money = Annotated[Decimal, Field(allow_inf_nan=False)]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(StrEnum):
    KHATA_IMAGE = "KHATA_IMAGE"
    UTILITY_DOCUMENT = "UTILITY_DOCUMENT"
    MOBILE_MONEY_SMS = "MOBILE_MONEY_SMS"
    PUBLIC_BENCHMARK = "PUBLIC_BENCHMARK"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class TransactionType(StrEnum):
    RECEIPT = "RECEIPT"
    SEND_MONEY = "SEND_MONEY"
    CASH_IN = "CASH_IN"
    CASH_OUT = "CASH_OUT"
    PAYMENT = "PAYMENT"
    REVERSAL = "REVERSAL"
    TRANSFER = "TRANSFER"
    CREDIT_SALE = "CREDIT_SALE"
    RECEIVABLE = "RECEIVABLE"
    PAYABLE = "PAYABLE"
    SETTLEMENT = "SETTLEMENT"
    BALANCE_SNAPSHOT = "BALANCE_SNAPSHOT"
    OTHER = "OTHER"


class TransactionDirection(StrEnum):
    INFLOW = "INFLOW"
    OUTFLOW = "OUTFLOW"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class ValidationStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"


class ReviewReason(StrEnum):
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    AMBIGUOUS_AMOUNT = "AMBIGUOUS_AMOUNT"
    CONTRADICTORY_DIRECTION = "CONTRADICTORY_DIRECTION"
    AMBIGUOUS_OWNERSHIP = "AMBIGUOUS_OWNERSHIP"
    UNSUPPORTED_TEMPLATE = "UNSUPPORTED_TEMPLATE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    IMPLAUSIBLE_AMOUNT = "IMPLAUSIBLE_AMOUNT"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    BALANCE_INCONSISTENCY = "BALANCE_INCONSISTENCY"
    INVALID_LINK = "INVALID_LINK"


class AssessmentStatus(StrEnum):
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FEATURES_READY = "FEATURES_READY"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Provenance(Contract):
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    page_number: int | None = Field(default=None, ge=1)
    region: tuple[tuple[float, float], ...] | None = None
    span_start: int | None = Field(default=None, ge=0)
    span_end: int | None = Field(default=None, ge=0)
    provider: str | None = None
    template: str | None = None

    @model_validator(mode="after")
    def span(self) -> "Provenance":
        if (self.span_start is None) != (self.span_end is None):
            raise ValueError("span requires both offsets")
        if self.span_start is not None and self.span_end <= self.span_start:
            raise ValueError("empty or reversed span")
        if self.region is not None and len(self.region) < 2:
            raise ValueError("region requires at least two coordinates")
        return self


class Source(Contract):
    source_id: UUID = Field(default_factory=uuid4)
    applicant_id: UUID
    source_type: SourceType
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    ingestion_timestamp: AwareDatetime = Field(default_factory=utcnow)
    synthetic: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class CandidateField(Contract):
    raw_value: str
    normalized_value: str | None
    confidence: Decimal = Field(ge=0, le=1)
    location: Provenance
    parser_name: str
    parser_version: str


class CandidateExtraction(Contract):
    candidate_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    created_at: AwareDatetime = Field(default_factory=utcnow)
    fields: dict[str, CandidateField]
    schema_version: str = "1.0"


class CanonicalEvent(Contract):
    event_id: UUID = Field(default_factory=uuid4)
    applicant_id: UUID
    account_id: UUID | None = None
    source_id: UUID
    source_type: SourceType
    event_timestamp: AwareDatetime
    ingestion_timestamp: AwareDatetime
    transaction_type: TransactionType
    direction: TransactionDirection
    amount: Money | None = None
    fee: Money | None = None
    currency: str = Field(default="BDT", pattern=r"^[A-Z]{3}$")
    transaction_reference: str | None = None
    counterparty: str | None = None
    balance: Money | None = None
    due_date: date | None = None
    payment_date: date | None = None
    payment_record_complete: bool = False
    provider: str | None = None
    validation_status: ValidationStatus = ValidationStatus.NEEDS_REVIEW
    review_reason: tuple[ReviewReason, ...] = ()
    extractor_name: str = "manual"
    extractor_version: str = "1.0"
    schema_version: str = "1.0"
    created_at: AwareDatetime = Field(default_factory=utcnow)
    supersedes_event_id: UUID | None = None
    duplicate_of_event_id: UUID | None = None
    reversal_of_event_id: UUID | None = None
    settlement_of_event_id: UUID | None = None
    source_provenance: Provenance
    missingness: dict[str, str] = Field(default_factory=dict)
    ownership: str = Field(default="unknown", pattern=r"^(external|own|unknown)$")
    external_medium_evidence: bool = False
    supported_template: bool = True
    amount_confidence: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    reviewed: bool = False

    @field_validator("amount", "fee", "balance", mode="before")
    @classmethod
    def no_float_money(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("use Decimal or decimal strings for money")
        return value

    @field_validator("event_timestamp", "ingestion_timestamp", "created_at")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class Correction(Contract):
    correction_id: UUID = Field(default_factory=uuid4)
    original_event_id: UUID
    corrected_event_id: UUID
    reason: str = Field(min_length=1)
    reviewer_alias: str = Field(pattern=r"^reviewer-[a-zA-Z0-9_-]+$")
    created_at: AwareDatetime = Field(default_factory=utcnow)


class ReviewDecision(Contract):
    subject_id: UUID
    validation_status: ValidationStatus
    reasons: tuple[ReviewReason, ...] = ()
    rule_version: str = "1.0"


class Assessment(Contract):
    assessment_id: UUID = Field(default_factory=uuid4)
    applicant_id: UUID
    scoring_time: AwareDatetime
    status: AssessmentStatus = AssessmentStatus.EVIDENCE_PENDING


class ProtectedAuditAttributes(Contract):
    applicant_id: UUID
    attributes: dict[str, str]
    consent_reference: str


class Coverage(Contract):
    """Caller-attested complete days; event presence alone never proves completeness."""
    applicant_id: UUID
    known_at: AwareDatetime
    observed_days: frozenset[date] = frozenset()
    balance_complete_days: frozenset[date] = frozenset()
    obligation_complete_days: frozenset[date] = frozenset()
    evidence_event_ids: tuple[UUID, ...] = ()
    reasons: tuple[str, ...] = ()


class FeatureValue(Contract):
    value: Decimal | int | dict[str, int] | tuple[str, ...] | None
    contributing_event_ids: tuple[UUID, ...] = ()
    reasons: tuple[str, ...] = ()

    @field_validator("value", mode="wrap")
    @classmethod
    def structured_values(cls, value: object, handler):
        # Decimal also accepts a 3-item tuple. Dispatch collections explicitly so a
        # three-reason JSON array cannot be misinterpreted as a Decimal tuple.
        if isinstance(value, (list, tuple)):
            return TypeAdapter(tuple[str, ...]).validate_python(value)
        if isinstance(value, dict):
            return TypeAdapter(dict[str, int]).validate_python(value)
        return handler(value)


class FeatureSnapshot(Contract):
    snapshot_id: UUID = Field(default_factory=uuid4)
    applicant_id: UUID
    scoring_time: AwareDatetime
    window_days: int
    feature_schema_version: str = "1.0"
    features: dict[str, FeatureValue]
