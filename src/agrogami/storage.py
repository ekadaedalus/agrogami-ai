"""Relational envelope tables with validated immutable JSON payloads.

Decimal and timestamps round-trip in JSON strings, avoiding SQLite float money.
"""
from pathlib import Path
from typing import TypeVar
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, String, Text, create_engine, event as sql_event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.engine import make_url
from agrogami.schemas import (Contract, Source, CandidateExtraction, CanonicalEvent, Correction,
                              FeatureSnapshot, Assessment, ProtectedAuditAttributes, utcnow)
from agrogami.validation.rules import replace, validate_event


class Base(DeclarativeBase):
    pass


class SourceRow(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    applicant_id: Mapped[str] = mapped_column(String(36), index=True)
    payload: Mapped[str] = mapped_column(Text)


class CandidateRow(Base):
    __tablename__ = "candidate_extractions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    payload: Mapped[str] = mapped_column(Text)


class EventRow(Base):
    __tablename__ = "canonical_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    applicant_id: Mapped[str] = mapped_column(String(36), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("canonical_events.id"), unique=True)
    payload: Mapped[str] = mapped_column(Text)


class CorrectionRow(Base):
    __tablename__ = "event_corrections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_id: Mapped[str] = mapped_column(ForeignKey("canonical_events.id"), unique=True)
    corrected_id: Mapped[str] = mapped_column(ForeignKey("canonical_events.id"), unique=True)
    payload: Mapped[str] = mapped_column(Text)


class SnapshotRow(Base):
    __tablename__ = "feature_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    applicant_id: Mapped[str] = mapped_column(String(36), index=True)
    payload: Mapped[str] = mapped_column(Text)


class AssessmentRow(Base):
    __tablename__ = "assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    applicant_id: Mapped[str] = mapped_column(String(36), index=True)
    payload: Mapped[str] = mapped_column(Text)


class AuditRow(Base):
    __tablename__ = "protected_audit_attributes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


MODEL_ROWS = {Source: (SourceRow, "source_id"), CandidateExtraction: (CandidateRow, "candidate_id"),
              CanonicalEvent: (EventRow, "event_id"), Correction: (CorrectionRow, "correction_id"),
              FeatureSnapshot: (SnapshotRow, "snapshot_id"), Assessment: (AssessmentRow, "assessment_id"),
              ProtectedAuditAttributes: (AuditRow, "applicant_id")}
C = TypeVar("C", bound=Contract)


class Store:
    def __init__(self, database_url: str):
        url = make_url(database_url)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")
        if url.get_backend_name() == "sqlite" and url.database not in {None, "", ":memory:"}:
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(url, echo=False, hide_parameters=True)
        if self.engine.dialect.name == "sqlite":
            @sql_event.listens_for(self.engine, "connect")
            def foreign_keys(connection, record):
                connection.execute("PRAGMA foreign_keys=ON")
        Base.metadata.create_all(self.engine)

    def _insert(self, session: Session, obj: Contract) -> None:
        row_type, key = MODEL_ROWS[type(obj)]
        values = {"id": str(getattr(obj, key)), "payload": obj.model_dump_json()}
        if hasattr(row_type, "applicant_id"):
            values["applicant_id"] = str(obj.applicant_id)
        if isinstance(obj, (CandidateExtraction, CanonicalEvent)):
            source = self.get(Source, obj.source_id, session=session)
            if source is None:
                raise ValueError("source not found")
            if isinstance(obj, CanonicalEvent) and (source.applicant_id != obj.applicant_id
                    or source.source_hash != obj.source_provenance.source_hash or source.source_type != obj.source_type):
                raise ValueError("source provenance mismatch")
            if isinstance(obj, CandidateExtraction) and any(f.location.source_hash != source.source_hash for f in obj.fields.values()):
                raise ValueError("candidate source hash mismatch")
            values["source_id"] = str(obj.source_id)
        if isinstance(obj, CanonicalEvent):
            values["supersedes_id"] = str(obj.supersedes_event_id) if obj.supersedes_event_id else None
        if isinstance(obj, Correction):
            values.update(original_id=str(obj.original_event_id), corrected_id=str(obj.corrected_event_id))
        session.add(row_type(**values))
        session.flush()

    def save(self, obj: Contract) -> None:
        if isinstance(obj, Correction) or isinstance(obj, CanonicalEvent) and obj.supersedes_event_id:
            raise ValueError("use correct() for version lineage")
        with Session(self.engine) as session, session.begin():
            self._insert(session, obj)

    def get(self, model: type[C], identifier: UUID, *, session: Session | None = None) -> C | None:
        if session is None:
            with Session(self.engine) as owned:
                return self.get(model, identifier, session=owned)
        row = session.get(MODEL_ROWS[model][0], str(identifier))
        return model.model_validate_json(row.payload) if row else None

    def events(self, applicant_id: UUID) -> list[CanonicalEvent]:
        with Session(self.engine) as session:
            rows = session.scalars(select(EventRow).where(EventRow.applicant_id == str(applicant_id))).all()
            return [CanonicalEvent.model_validate_json(row.payload) for row in rows]

    def corrections(self, event_id: UUID) -> list[Correction]:
        with Session(self.engine) as session:
            rows = session.scalars(select(CorrectionRow).where(
                (CorrectionRow.original_id == str(event_id)) | (CorrectionRow.corrected_id == str(event_id)))).all()
            return [Correction.model_validate_json(row.payload) for row in rows]

    def history(self, event_id: UUID) -> list[CanonicalEvent]:
        """Recover ancestors from any version, earliest first."""
        history: list[CanonicalEvent] = []
        seen: set[UUID] = set()
        current = self.get(CanonicalEvent, event_id)
        while current is not None:
            if current.event_id in seen:
                raise ValueError("cyclic event lineage")
            seen.add(current.event_id)
            history.append(current)
            current = self.get(CanonicalEvent, current.supersedes_event_id) if current.supersedes_event_id else None
        return list(reversed(history))

    def correct(self, event_id: UUID, changes: dict[str, object], *, reason: str,
                reviewer_alias: str) -> CanonicalEvent:
        forbidden = {"event_id", "applicant_id", "source_id", "source_type", "source_provenance",
                     "supersedes_event_id", "created_at", "ingestion_timestamp", "validation_status", "reviewed"}
        if changes.keys() & forbidden:
            raise ValueError("correction cannot replace identity, provenance or lifecycle")
        with Session(self.engine) as session, session.begin():
            original = self.get(CanonicalEvent, event_id, session=session)
            if original is None:
                raise ValueError("event not found")
            if session.scalar(select(EventRow.id).where(EventRow.supersedes_id == str(event_id))):
                raise ValueError("correct latest version only")
            corrected = replace(original, **(changes | {"event_id": uuid4(), "supersedes_event_id": event_id,
                                "created_at": utcnow(), "reviewed": True, "review_reason": ()}))
            corrected = validate_event(corrected)
            correction = Correction(original_event_id=event_id, corrected_event_id=corrected.event_id,
                                    reason=reason, reviewer_alias=reviewer_alias)
            self._insert(session, corrected)
            self._insert(session, correction)
            return corrected
