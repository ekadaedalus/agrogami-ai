from datetime import timedelta
from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError
from agrogami.fixtures import APPLICANT, T0, fixture_event, fixture_sources, synthetic_candidate, coverage
from agrogami.schemas import Source, CandidateExtraction, CanonicalEvent, Assessment, ProtectedAuditAttributes, Correction
from agrogami.storage import Store, Base
from agrogami.features import build_features


@pytest.fixture
def store(tmp_path):
    value = Store("sqlite:///" + str(tmp_path / "evidence.db"))
    yield value
    value.engine.dispose()


def seed(store):
    event = fixture_event("persist", amount=Decimal("100.123456789"))
    store.save(fixture_sources([event])[0])
    store.save(event)
    return event


def test_roundtrip_all_tables_and_separate_audit(store):
    event = seed(store)
    candidate = synthetic_candidate(event)
    store.save(candidate)
    assert store.get(CanonicalEvent, event.event_id) == event
    assert store.get(CandidateExtraction, candidate.candidate_id) == candidate
    snapshot = build_features([event], applicant_id=APPLICANT, t0=T0, window_days=30, coverage=coverage())
    store.save(snapshot)
    assert store.get(type(snapshot), snapshot.snapshot_id) == snapshot
    assessment = Assessment(applicant_id=APPLICANT, scoring_time=T0)
    store.save(assessment)
    assert store.get(Assessment, assessment.assessment_id) == assessment
    audit = ProtectedAuditAttributes(applicant_id=APPLICANT, attributes={"synthetic_group": "test"}, consent_reference="SYNTHETIC")
    store.save(audit)
    assert store.get(ProtectedAuditAttributes, APPLICANT) == audit
    assert "synthetic_group" not in snapshot.model_dump_json()
    assert len(Base.metadata.tables) == 7


def test_correction_preserves_original_candidate_and_lineage(store):
    event = seed(store)
    candidate = synthetic_candidate(event)
    store.save(candidate)
    corrected = store.correct(event.event_id, {"amount": Decimal("150")}, reason="Synthetic manual review",
                              reviewer_alias="reviewer-demo")
    assert corrected.supersedes_event_id == event.event_id
    assert corrected.event_id != event.event_id
    assert corrected.reviewed
    assert store.get(CanonicalEvent, event.event_id) == event
    assert store.get(CandidateExtraction, candidate.candidate_id) == candidate
    assert len(store.events(APPLICANT)) == 2
    corrections = store.corrections(corrected.event_id)
    assert len(corrections) == 1
    assert corrections[0].reason == "Synthetic manual review"
    assert corrections[0].reviewer_alias == "reviewer-demo"
    assert store.history(corrected.event_id) == [event, corrected]
    with pytest.raises(ValueError):
        store.correct(event.event_id, {"amount": "160"}, reason="again", reviewer_alias="reviewer-demo")


def test_correction_failure_is_atomic(store):
    event = seed(store)
    with pytest.raises(ValueError):
        store.correct(event.event_id, {"amount": "150"}, reason="", reviewer_alias="private-person-name")
    assert len(store.events(APPLICANT)) == 1


def test_immutable_insert_and_missing_source(store):
    event = seed(store)
    with pytest.raises(IntegrityError):
        store.save(event)
    with pytest.raises(ValueError):
        store.save(fixture_event("source-missing"))


def test_provenance_identity_cannot_be_corrected(store):
    event = seed(store)
    with pytest.raises(ValueError):
        store.correct(event.event_id, {"source_id": APPLICANT}, reason="wrong", reviewer_alias="reviewer-demo")


def test_schema_compiles_for_postgresql():
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable
    for table in Base.metadata.sorted_tables:
        assert "CREATE TABLE" in str(CreateTable(table).compile(dialect=postgresql.dialect()))
