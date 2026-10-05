"""Application services and a separate immutable backend record journal.

The original deterministic Store and its seven-table metadata remain unchanged.
"""
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import Literal, TypeVar, Callable
from uuid import UUID, uuid4
from sqlalchemy import String, Text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from pydantic import AwareDatetime, Field
from agrogami.schemas import (Contract, Source, SourceType, CanonicalEvent, CandidateExtraction,
                              TransactionType as T, TransactionDirection as D, ValidationStatus as V,
                              Coverage, FeatureSnapshot, utcnow)
from agrogami.storage import Store
from agrogami.events.intake import intake
from agrogami.extraction.sms import parse_sms
from agrogami.extraction.documents import preprocess, line_regions, TrOCRAdapter, LayoutLMv3Adapter
from agrogami.extraction.local_models import DebertaAdapter
from agrogami.validation.rules import validate_event
from agrogami.features import build_all_windows
from agrogami.assessment import assess, AssessmentSnapshot, SnapshotStatus
from agrogami.risk.models import RiskModel, ValidationScope
from agrogami.calibration.core import Calibrator, EvaluationLineage
from agrogami.fairness.metrics import FairnessReport
from agrogami.explainability.core import TreeExplanation


class BackendBase(DeclarativeBase):
    pass


class BackendRecord(BackendBase):
    __tablename__ = "backend_records"
    kind: Mapped[str] = mapped_column(String(40), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class Job(Contract):
    job_id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    candidate_id: UUID | None = None
    candidate_ids: tuple[UUID, ...] = ()
    event_id: UUID | None = None
    status: Literal["NEEDS_REVIEW", "COMPLETED", "BLOCKED_MODEL_ARTIFACT"]
    reasons: tuple[str, ...] = ()
    created_at: AwareDatetime = Field(default_factory=utcnow)


class EvaluationRun(Contract):
    run_id: UUID = Field(default_factory=uuid4)
    dataset_id: str
    scope: ValidationScope
    metrics: dict[str, float | None]
    fairness: FairnessReport | None = None
    limitations: tuple[str, ...]
    private_lineage: EvaluationLineage | None = None
    created_at: AwareDatetime = Field(default_factory=utcnow)


class CandidateAcceptance(Contract):
    candidate_id: UUID
    accepted_event_id: UUID
    reason: str = Field(min_length=1)
    reviewer_alias: str = Field(pattern=r"^reviewer-[A-Za-z0-9_-]+$")
    created_at: AwareDatetime = Field(default_factory=utcnow)


MODEL_KINDS = {Job: "job", AssessmentSnapshot: "assessment_snapshot", EvaluationRun: "evaluation", CandidateAcceptance: "candidate_review"}
B = TypeVar("B", bound=Contract)


class BackendRepository:
    def __init__(self, core: Store):
        self.core = core
        BackendBase.metadata.create_all(core.engine)

    def save(self, obj: Contract, *, session: Session | None = None) -> None:
        if session is None:
            with Session(self.core.engine) as owned, owned.begin():
                self.save(obj, session=owned)
            return
        kind = MODEL_KINDS[type(obj)]
        key = (obj.job_id if isinstance(obj, Job) else obj.assessment_id if isinstance(obj, AssessmentSnapshot)
               else obj.candidate_id if isinstance(obj, CandidateAcceptance) else obj.run_id)
        session.add(BackendRecord(kind=kind, id=str(key), payload=obj.model_dump_json()))
        session.flush()

    def get(self, model: type[B], identifier: UUID) -> B | None:
        with Session(self.core.engine) as session:
            row = session.get(BackendRecord, (MODEL_KINDS[model], str(identifier)))
            return model.model_validate_json(row.payload) if row else None

    def assessments(self, applicant_id: UUID) -> list[AssessmentSnapshot]:
        with Session(self.core.engine) as session:
            rows = session.scalars(select(BackendRecord).where(BackendRecord.kind == "assessment_snapshot")).all()
            records = [AssessmentSnapshot.model_validate_json(row.payload) for row in rows]
        return sorted((record for record in records if record.applicant_id == applicant_id),
                      key=lambda record: (record.created_at, str(record.assessment_id)))


class ApplicationService:
    def __init__(self, store: Store, private_dir: Path, *, model: RiskModel | None = None,
                 calibrator: Calibrator | None = None,
                 explanation_provider: Callable[[dict[str, float]], TreeExplanation] | None = None,
                 deberta: DebertaAdapter | None = None, trocr: TrOCRAdapter | None = None,
                 layout: LayoutLMv3Adapter | None = None):
        self.store, self.private_dir = store, private_dir
        self.records = BackendRepository(store)
        self.model, self.calibrator = model, calibrator
        self.explanation_provider = explanation_provider
        self.deberta, self.trocr, self.layout = deberta, trocr, layout

    def sms_intake(self, *, applicant_id: UUID, account_id: UUID | None, text: str, provider: str) -> Job:
        synthetic = text.startswith("SYNTHETIC:")
        source = intake(text.encode("utf-8"), applicant_id, SourceType.MOBILE_MONEY_SMS,
                        synthetic=synthetic, metadata={"provider": provider})
        parsed = parse_sms(text, source, provider)
        candidates = [parsed.candidate]
        if parsed.status == V.NEEDS_REVIEW and self.deberta is not None and not parsed.non_transaction:
            candidates.append(self.deberta.extract(text, source))
        fields = parsed.candidate.fields
        event = None
        if "event_timestamp" in fields:
            direction = {T.RECEIPT: D.INFLOW, T.SEND_MONEY: D.OUTFLOW, T.CASH_IN: D.INFLOW,
                         T.CASH_OUT: D.OUTFLOW, T.PAYMENT: D.OUTFLOW, T.REVERSAL: D.UNKNOWN}
            kind = T(fields["transaction_type"].normalized_value)
            event = validate_event(CanonicalEvent(applicant_id=applicant_id, account_id=account_id,
                source_id=source.source_id, source_type=source.source_type,
                event_timestamp=fields["event_timestamp"].normalized_value, ingestion_timestamp=source.ingestion_timestamp,
                transaction_type=kind, direction=direction[kind], amount=fields["amount"].normalized_value,
                fee=fields["fee"].normalized_value, balance=fields["balance"].normalized_value if "balance" in fields else None,
                provider=provider, transaction_reference=fields["transaction_reference"].normalized_value,
                source_provenance=fields["amount"].location, ownership="unknown",
                extractor_name="deterministic-synthetic-sms", extractor_version="1.0"))
        job = Job(source_id=source.source_id, candidate_id=parsed.candidate.candidate_id,
                  candidate_ids=tuple(c.candidate_id for c in candidates),
                  event_id=event.event_id if event else None,
                  status="COMPLETED" if parsed.non_transaction else "NEEDS_REVIEW",
                  reasons=tuple(r.value for r in event.review_reason) if event else tuple(r.value for r in parsed.reasons))
        directory = self.private_dir / "objects"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (str(source.source_id) + ".bin")
        target.write_bytes(text.encode("utf-8"))
        try:
            with Session(self.store.engine) as session, session.begin():
                self.store._insert(session, source)
                for candidate in candidates:
                    self.store._insert(session, candidate)
                if event:
                    self.store._insert(session, event)
                self.records.save(job, session=session)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return job

    def document_intake(self, *, applicant_id: UUID, content: bytes, orientation: int = 0,
                        deskew_degrees: float | None = None, synthetic: bool = False) -> Job:
        document = preprocess(content, orientation=orientation, deskew_degrees=deskew_degrees)
        source = intake(content, applicant_id, SourceType.UTILITY_DOCUMENT,
                        synthetic=synthetic,
                        metadata={"preprocess_version": "1.0", "width": str(document.image.width), "height": str(document.image.height)})
        directory = self.private_dir / "objects"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (str(source.source_id) + ".bin")
        target.write_bytes(content)
        try:
            candidates = []
            boxes = line_regions(document)
            if self.trocr is not None:
                candidates.append(self.trocr.extract(document, source, boxes))
                if self.layout is not None and boxes:
                    # Coarse line regions are explicit; no invented word-level boxes.
                    words = [candidates[0].fields[f"line:{i}"].raw_value for i in range(len(boxes))]
                    candidates.append(self.layout.extract(document, source, words, boxes))
            job = Job(source_id=source.source_id, candidate_id=candidates[-1].candidate_id if candidates else None,
                candidate_ids=tuple(c.candidate_id for c in candidates),
                status="NEEDS_REVIEW" if candidates else "BLOCKED_MODEL_ARTIFACT",
                reasons=document.warnings + (("raw_model_candidates_require_review", "line_level_regions_not_word_boxes")
                    if candidates else ("local_extraction_checkpoint_unavailable",)))
            with Session(self.store.engine) as session, session.begin():
                self.store._insert(session, source)
                for candidate in candidates:
                    self.store._insert(session, candidate)
                self.records.save(job, session=session)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return job

    def review(self, event_id: UUID, changes: dict[str, object], reason: str, reviewer_alias: str) -> CanonicalEvent:
        corrected = self.store.correct(event_id, changes, reason=reason, reviewer_alias=reviewer_alias)
        now = max(utcnow(), corrected.created_at + timedelta(microseconds=1))
        previous = [record for record in self.records.assessments(corrected.applicant_id)
                    if record.assessment_time < now]
        prior = previous[-1] if previous else None
        fresh_coverage = Coverage(applicant_id=corrected.applicant_id, known_at=corrected.created_at,
            evidence_event_ids=(corrected.event_id,), reasons=("correction_requires_fresh_coverage_and_reassessment",))
        pending = assess(self.store.events(corrected.applicant_id), applicant_id=corrected.applicant_id,
            t0=now, coverage=fresh_coverage, window_days=prior.feature_snapshot.window_days if prior else 30,
            model=self.model, calibrator=self.calibrator, previous_id=prior.assessment_id if prior else None)
        pending = AssessmentSnapshot.model_validate(pending.model_dump() | {"status": SnapshotStatus.NEEDS_REVIEW,
            "limitations": pending.limitations + ("Correction appended; fresh coverage and explicit model reassessment required",)})
        self.records.save(pending)
        return corrected

    def accept_candidate(self, candidate_id: UUID, event: CanonicalEvent, reason: str, reviewer_alias: str) -> CanonicalEvent:
        candidate = self.store.get(CandidateExtraction, candidate_id)
        if candidate is None or candidate.source_id != event.source_id:
            raise ValueError("candidate/source identity mismatch")
        if event.supersedes_event_id or event.duplicate_of_event_id:
            raise ValueError("new candidate acceptance cannot assert version or duplicate lineage")
        source = self.store.get(Source, candidate.source_id)
        event = CanonicalEvent.model_validate(event.model_dump() | {
            "created_at": utcnow(), "ingestion_timestamp": source.ingestion_timestamp, "reviewed": True,
            "validation_status": V.NEEDS_REVIEW, "review_reason": (), "extractor_name": "human-reviewed-candidate",
            "extractor_version": "1.0"})
        event = validate_event(event)
        if event.validation_status != V.ACCEPTED:
            raise ValueError("critical evidence remains unresolved")
        audit = CandidateAcceptance(candidate_id=candidate_id, accepted_event_id=event.event_id,
                                    reason=reason, reviewer_alias=reviewer_alias)
        with Session(self.store.engine) as session, session.begin():
            self.store._insert(session, event)
            self.records.save(audit, session=session)
        return event

    def features(self, applicant_id: UUID, t0: datetime, coverage: Coverage) -> dict[int, FeatureSnapshot]:
        return build_all_windows(self.store.events(applicant_id), applicant_id=applicant_id, t0=t0, coverage=coverage)

    def assessment(self, *, applicant_id: UUID, t0: datetime, coverage: Coverage,
                   window_days: int = 30, previous_id: UUID | None = None) -> AssessmentSnapshot:
        if previous_id:
            previous = self.records.get(AssessmentSnapshot, previous_id)
            if previous is None or previous.applicant_id != applicant_id or previous.assessment_time > t0:
                raise ValueError("invalid prior assessment lineage")
        result = assess(self.store.events(applicant_id), applicant_id=applicant_id, t0=t0,
                        coverage=coverage, window_days=window_days, model=self.model,
                        calibrator=self.calibrator, explanation_provider=self.explanation_provider, previous_id=previous_id)
        self.records.save(result)
        return result
