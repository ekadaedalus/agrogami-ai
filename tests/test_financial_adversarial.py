"""Permanent synthetic adversarial regressions; no external audit files required."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from agrogami.api.app import create_app, Role
from agrogami.application import ApplicationService
from agrogami.assessment import assess, SnapshotStatus
from agrogami.features import build_features
from agrogami.features.engine import current_as_of
from agrogami.fixtures import APPLICANT, ACCOUNT, T0, fixture_event, coverage, identifier
from agrogami.schemas import CanonicalEvent, Coverage, TransactionType as T, TransactionDirection as D, ValidationStatus as V, ReviewReason as R
from agrogami.storage import Store
from agrogami.ui.api_client import APIClient
from agrogami.ui.samples import sample_sms
from agrogami.validation.rules import replace, reconcile


@pytest.fixture
def service(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "synthetic.db"))
    yield ApplicationService(store, tmp_path / "sources")
    store.engine.dispose()


def snapshot(events, cov=None):
    return build_features(events, applicant_id=APPLICANT, t0=T0,
                          window_days=30, coverage=cov or coverage(complete=True))


def test_repeated_ui_submission_same_synthetic_account_counts_once(service, monkeypatch):
    from streamlit.testing.v1 import AppTest
    original = APIClient.__init__
    with TestClient(create_app(service, tokens={"synthetic-review": Role.reviewer})) as transport:
        def initialize(self, base_url, token="", **kwargs):
            original(self, base_url, token, transport)
        monkeypatch.setattr(APIClient, "__init__", initialize)
        app = AppTest.from_file(Path("src/agrogami/ui/app.py").resolve(), default_timeout=15).run()
        app.sidebar.radio[0].set_value("Applicant Evidence").run()
        jobs = []
        for _ in range(2):
            next(b for b in app.button if b.label == "Submit SMS").click().run()
            assert not app.exception and not app.error
            jobs.append(app.session_state["job"])
        originals = [service.store.get(CanonicalEvent, UUID(j["event_id"])) for j in jobs]
        assert originals[0].account_id == originals[1].account_id
        assert originals[0].account_id is not None
        for e in originals:
            service.review(e.event_id, changes={"ownership": "external"},
                           reason="Synthetic ownership corroboration", reviewer_alias="reviewer-synthetic")
        t0 = datetime.now(timezone.utc) + timedelta(seconds=1)
        events = service.store.events(originals[0].applicant_id)
        cov = Coverage(applicant_id=originals[0].applicant_id, known_at=t0 - timedelta(microseconds=1))
        result = build_features(events, applicant_id=cov.applicant_id, t0=t0, window_days=30, coverage=cov)
        assert result.features["external_inflow_total"].value == Decimal("100")
        assert len(events) == 4  # Both sources and append-only reviews remain traceable.
        assert sum(e.duplicate_of_event_id is not None for e in reconcile(current_as_of(events, t0))) == 1


@pytest.mark.parametrize("same_account,expected", [(True, "100"), (False, "200")])
def test_repeated_api_submission_preserves_account_scope(service, same_account, expected):
    text = sample_sms("External inflow")
    jobs = []
    with TestClient(create_app(service)) as client:
        for i in range(2):
            response = client.post("/api/v1/intake/sms", json={"applicant_id": str(APPLICANT),
                "account_id": str(ACCOUNT if same_account or i == 0 else identifier("other-account")),
                "provider": "SYNTHETIC-bKash-like", "text": text})
            assert response.status_code == 201
            jobs.append(response.json())
    for job in jobs:
        service.review(UUID(job["event_id"]), changes={"ownership": "external"},
                       reason="Synthetic corroboration", reviewer_alias="reviewer-synthetic")
    t0 = datetime.now(timezone.utc) + timedelta(seconds=1)
    cov = Coverage(applicant_id=APPLICANT, known_at=t0 - timedelta(microseconds=1))
    result = build_features(service.store.events(APPLICANT), applicant_id=APPLICANT,
                            t0=t0, window_days=30, coverage=cov)
    assert result.features["external_inflow_total"].value == Decimal(expected)
    assert len({j["source_id"] for j in jobs}) == 2
    assert len({j["candidate_id"] for j in jobs}) == 2


@pytest.mark.parametrize("account", [None, ACCOUNT])
def test_ui_real_evidence_never_invents_account(service, monkeypatch, account):
    from streamlit.testing.v1 import AppTest
    original_init, original_intake = APIClient.__init__, APIClient.intake_sms
    submitted = []
    with TestClient(create_app(service, tokens={"synthetic-review": Role.reviewer})) as transport:
        def initialize(self, base_url, token="", **kwargs):
            original_init(self, base_url, token, transport)
        def capture(self, payload):
            submitted.append(payload)
            return original_intake(self, payload)
        monkeypatch.setattr(APIClient, "__init__", initialize)
        monkeypatch.setattr(APIClient, "intake_sms", capture)
        app = AppTest.from_file(Path("src/agrogami/ui/app.py").resolve(), default_timeout=15).run()
        next(x for x in app.sidebar.text_input if x.label == "Demo credential").set_value("synthetic-review")
        app.sidebar.radio[0].set_value("Applicant Evidence").run()
        next(x for x in app.selectbox if x.label == "Evidence scope").set_value("REAL/DE-IDENTIFIED").run()
        next(x for x in app.text_area if x.label == "SMS evidence").set_value("Invented unsupported text for identity test")
        if account:
            next(x for x in app.text_input if x.label == "Account UUID (optional)").set_value(str(account))
        next(b for b in app.button if b.label == "Submit SMS").click().run()
        assert not app.exception
        assert submitted[0]["account_id"] == (str(account) if account else None)


@pytest.mark.parametrize("versions", [2, 3])
@pytest.mark.parametrize("economic_day,expected", [(-1, "0"), (40, "0"), (2, "100")])
def test_supersession_resolved_before_economic_time(versions, economic_day, expected):
    original = fixture_event("asof-original", day=10)
    chain = [original]
    for n in range(1, versions):
        chain.append(replace(chain[-1], event_id=identifier(f"asof-v{n}"),
            supersedes_event_id=chain[-1].event_id, created_at=T0 - timedelta(days=4-n),
            event_timestamp=T0 - timedelta(days=economic_day)))
    result = snapshot(chain)
    assert result.features["external_inflow_total"].value == Decimal(expected)
    assert original.event_id not in result.features["external_inflow_total"].contributing_event_ids
    assert snapshot(list(reversed(chain))) == result


@pytest.mark.parametrize("availability_field", ["created_at", "ingestion_timestamp"])
@pytest.mark.parametrize("known_before", [False, True])
def test_correction_availability_preserves_historical_assessment(availability_field, known_before):
    original = fixture_event("asof-known-original", day=10)
    revised = replace(original, event_id=identifier("asof-known-revised"), supersedes_event_id=original.event_id,
        created_at=T0 - timedelta(days=1), event_timestamp=T0 + timedelta(days=1),
        **({availability_field: T0 - timedelta(seconds=1)} if availability_field != "created_at" else {}))
    revised = replace(revised, **{availability_field: T0 - timedelta(seconds=1) if known_before else T0 + timedelta(seconds=1)})
    assert snapshot([original, revised]).features["external_inflow_total"].value == (0 if known_before else 100)


def test_correction_moves_future_event_into_past_without_rewriting_original():
    original = fixture_event("asof-future-original", day=-1,
                             ingestion_timestamp=T0 - timedelta(days=2), created_at=T0 - timedelta(days=2))
    corrected = replace(original, event_id=identifier("asof-past-correction"),
                        supersedes_event_id=original.event_id, created_at=T0 - timedelta(days=1),
                        event_timestamp=T0 - timedelta(days=5))
    assert snapshot([original, corrected]).features["external_inflow_total"].value == 100
    assert original.event_timestamp > T0


def reversed_versions(**changes):
    original = fixture_event("lineage-original", day=10)
    reversal = fixture_event("lineage-reversal", day=5, transaction_type=T.REVERSAL,
                             direction=D.OUTFLOW, reversal_of_event_id=original.event_id)
    corrected = replace(original, event_id=identifier("lineage-corrected"),
                        supersedes_event_id=original.event_id, created_at=T0 - timedelta(days=2), **changes)
    return original, reversal, corrected


@pytest.mark.parametrize("changes", [{"counterparty": "SYNTHETIC corrected alias"},
                                    {"extractor_version": "synthetic-reviewed-v2"}])
def test_reversal_survives_nonfinancial_correction(changes):
    original, reversal, corrected = reversed_versions(**changes)
    result = snapshot([original, reversal, corrected])
    assert result.features["external_inflow_total"].value == 0
    assert reversal.event_id in result.features["external_inflow_total"].contributing_event_ids
    assert reversal.reversal_of_event_id == original.event_id
    assert corrected.supersedes_event_id == original.event_id


@pytest.mark.parametrize("changes", [{"amount": Decimal("200")}, {"direction": D.OUTFLOW},
                                    {"event_timestamp": T0 - timedelta(days=4)},
                                    {"event_timestamp": T0 - timedelta(days=12)}])
def test_incompatible_reversed_correction_quarantines_relationship(changes):
    events = list(reversed_versions(**changes))
    result = snapshot(events)
    assert result.features["external_inflow_total"].value == 0
    assert result.features["external_outflow_total"].value == 0
    assessment = assess(events, applicant_id=APPLICANT, t0=T0, coverage=coverage(complete=True))
    assert assessment.status == SnapshotStatus.NEEDS_REVIEW
    assert assessment.display_score is None
    assert "INVALID_LINK" in result.features["missingness_reasons"].value


def test_multiversion_original_and_reversal_corrections_preserve_cancellation():
    original, reversal, corrected = reversed_versions(counterparty="SYNTHETIC alias")
    latest = replace(corrected, event_id=identifier("lineage-v3"), supersedes_event_id=corrected.event_id,
                     created_at=T0 - timedelta(days=1), extractor_version="reviewed-v3")
    revised_reversal = replace(reversal, event_id=identifier("reversal-v2"), supersedes_event_id=reversal.event_id,
                               created_at=T0 - timedelta(days=1), counterparty="SYNTHETIC reversal alias")
    events = [original, reversal, corrected, latest, revised_reversal]
    result = snapshot(events)
    assert result.features["external_inflow_total"].value == 0
    assert revised_reversal.event_id in result.features["external_inflow_total"].contributing_event_ids
    assert reversal.event_id not in result.features["external_inflow_total"].contributing_event_ids
    assert snapshot(list(reversed(events))) == result


def test_reversal_economic_correction_requires_review_for_both_sides():
    original, reversal, _ = reversed_versions()
    corrected = replace(reversal, event_id=identifier("reversal-amount-v2"), supersedes_event_id=reversal.event_id,
                        created_at=T0 - timedelta(days=1), amount=Decimal("50"))
    result = snapshot([original, reversal, corrected])
    assert result.features["external_inflow_total"].value == 0
    assert result.features["accepted_event_share"].value == 0


@pytest.mark.parametrize("changes", [
    {"validation_status": V.NEEDS_REVIEW, "ownership": "unknown", "review_reason": (R.AMBIGUOUS_OWNERSHIP,)},
    {"event_timestamp": T0 + timedelta(days=1)},
    {"transaction_type": T.PAYMENT},
])
def test_ineligible_corrected_reversal_cannot_resurrect_original(changes):
    original, reversal, _ = reversed_versions()
    corrected = replace(reversal, event_id=identifier("ineligible-reversal-v2"),
                        supersedes_event_id=reversal.event_id, created_at=T0 - timedelta(days=1), **changes)
    result = snapshot([original, reversal, corrected])
    assert result.features["external_inflow_total"].value == 0
    assert result.features["external_outflow_total"].value == 0
    assert "INVALID_LINK" in result.features["missingness_reasons"].value


def test_changed_reversal_pointer_requires_review_of_both_relationships():
    original, reversal, _ = reversed_versions()
    other = fixture_event("reversal-other-target", day=9)
    corrected = replace(reversal, event_id=identifier("reversal-relinked"), supersedes_event_id=reversal.event_id,
                        created_at=T0 - timedelta(days=1), reversal_of_event_id=other.event_id)
    result = snapshot([original, other, reversal, corrected])
    assert result.features["external_inflow_total"].value == 0
    assert result.features["accepted_event_share"].value == 0
    assert "INVALID_LINK" in result.features["missingness_reasons"].value


def obligation_scenario(*, unresolved=True, due_inside=True, complete=True, late=False):
    due = (T0 - timedelta(days=10 if due_inside else 40)).date()
    paid = fixture_event("old-paid", day=50, transaction_type=T.PAYMENT, direction=D.OUTFLOW,
        due_date=(T0 - timedelta(days=8)).date(), payment_date=(T0 - timedelta(days=8)).date())
    other = fixture_event("old-unresolved", day=50, transaction_type=T.PAYABLE, direction=D.NEUTRAL,
        due_date=due, payment_date=due + timedelta(days=2 if late else 0),
        validation_status=V.NEEDS_REVIEW if unresolved else V.ACCEPTED,
        review_reason=(R.MISSING_EVIDENCE,) if unresolved else ())
    observed = coverage(complete=True).observed_days
    cov = Coverage(applicant_id=APPLICANT, known_at=T0 - timedelta(seconds=1), observed_days=observed,
                   obligation_complete_days=observed if complete else sorted(observed)[:-1])
    return [paid, other], cov


def test_unresolved_old_obligation_due_in_window_makes_denominator_unknown():
    events, cov = obligation_scenario()
    result = snapshot(events, cov)
    punctuality = result.features["payment_punctuality"]
    assert punctuality.value is None
    assert "complete_obligation_denominator_unknown" in punctuality.reasons
    assert events[1].event_id in punctuality.contributing_event_ids
    assert result.features["median_payment_delay_days"].value is None
    assert result.features["obligation_coverage"].reasons
    assert "MISSING_EVIDENCE" in result.features["missingness_reasons"].value
    assert result.features["external_outflow_total"].value == 0


def test_known_unresolved_obligation_due_inside_window_survives_future_economic_filter():
    events, cov = obligation_scenario()
    events[1] = replace(events[1], event_timestamp=T0 + timedelta(days=1))
    result = snapshot(events, cov)
    assert result.features["payment_punctuality"].value is None
    assert events[1].event_id in result.features["payment_punctuality"].contributing_event_ids
    assert assess(events, applicant_id=APPLICANT, t0=T0, coverage=cov).status == SnapshotStatus.NEEDS_REVIEW


@pytest.mark.parametrize("unresolved,due_inside,complete,late,expected", [
    (True, False, True, False, Decimal("1")),
    (False, True, True, False, Decimal("1")),
    (False, True, True, True, Decimal("0.5")),
    (False, True, False, False, None),
])
def test_obligation_due_relevance_and_complete_denominator(unresolved, due_inside, complete, late, expected):
    events, cov = obligation_scenario(unresolved=unresolved, due_inside=due_inside, complete=complete, late=late)
    assert snapshot(events, cov).features["payment_punctuality"].value == expected


@pytest.mark.parametrize("unresolved,complete", [(True, True), (False, False)])
def test_unresolved_denominator_blocks_even_model_without_punctuality_feature(unresolved, complete):
    from agrogami.datasets import DatasetIdentity, RiskDataset
    from agrogami.risk.models import LogisticRiskModel, ValidationScope
    from agrogami.calibration.core import Calibrator
    data = RiskDataset(identity=DatasetIdentity(dataset_id="SYNTHETIC-denominator", scope="synthetic",
        target_definition="Invented label", limitations=("Synthetic only",)),
        sample_ids=tuple(f"train-{i}" for i in range(12)), feature_names=("external_inflow_total",),
        values=tuple((float(i),) for i in range(12)), labels=tuple(int(i >= 6) for i in range(12)))
    model = LogisticRiskModel.fit(data, scope=ValidationScope.SYNTHETIC_DEMO, version="synthetic-test")
    calibrator = Calibrator.fit([.1, .2, .8, .9], [0, 0, 1, 1], [f"cal-{i}" for i in range(4)],
        model=model.artifact, dataset_id=data.identity.dataset_id, version="synthetic-test")
    events, cov = obligation_scenario(unresolved=unresolved, complete=complete)
    result = assess(events, applicant_id=APPLICANT, t0=T0, coverage=cov, model=model, calibrator=calibrator)
    assert result.status == (SnapshotStatus.NEEDS_REVIEW if unresolved else SnapshotStatus.INSUFFICIENT_EVIDENCE)
    assert result.display_score is None and result.calibrated_probability is None


@pytest.mark.parametrize("count", [2, 3, 5, 8])
def test_all_unreferenced_ambiguity_group_members_remain_review(count):
    from itertools import permutations
    events = [fixture_event(f"unreferenced-{n}", transaction_reference=None) for n in range(count)]
    orders = list(permutations(events)) if count <= 3 else [events, list(reversed(events))]
    for order in orders:
        result = reconcile(list(order))
        assert all(e.validation_status == V.NEEDS_REVIEW for e in result)
        assert all(R.AMBIGUOUS_MATCH in e.review_reason for e in result)
        assert snapshot(list(order)).features["external_inflow_total"].value == 0


def test_previous_ambiguous_records_still_quarantine_later_member():
    a, b, c = [fixture_event(f"ongoing-ambiguity-{n}", transaction_reference=None) for n in range(3)]
    prior = reconcile([a, b])
    result = snapshot([*prior, c])
    assert result.features["external_inflow_total"].value == 0
    assert result.features["accepted_event_share"].value == 0


@pytest.mark.parametrize("first,second,direction,medium_a,medium_b,compatible", [
    (T.PAYMENT, T.RECEIPT, D.OUTFLOW, False, False, True),
    (T.SEND_MONEY, T.TRANSFER, D.OUTFLOW, False, False, True),
    (T.CASH_IN, T.RECEIPT, D.INFLOW, False, False, False),
    (T.CASH_OUT, T.PAYMENT, D.OUTFLOW, False, False, False),
    (T.CASH_IN, T.CASH_IN, D.INFLOW, False, True, False),
    (T.RECEIPT, T.RECEIPT, D.INFLOW, False, True, False),
])
def test_reference_deduplication_respects_economic_semantics(first, second, direction, medium_a, medium_b, compatible):
    a = fixture_event("semantic-a", transaction_reference="SYNTHETIC-common", transaction_type=first,
                      direction=direction, external_medium_evidence=medium_a)
    b = fixture_event("semantic-b", transaction_reference=a.transaction_reference, transaction_type=second,
                      direction=direction, external_medium_evidence=medium_b)
    result = reconcile([a, b])
    if compatible:
        assert all(e.validation_status == V.ACCEPTED for e in result)
        assert sum(e.duplicate_of_event_id is not None for e in result) == 1
        name = "external_inflow_total" if direction == D.INFLOW else "external_outflow_total"
        assert snapshot([a, b]).features[name].value == 100
    else:
        assert all(e.validation_status == V.NEEDS_REVIEW for e in result)
        assert all(R.AMBIGUOUS_MATCH in e.review_reason for e in result)
        assert all(e.duplicate_of_event_id is None for e in result)


def test_same_reference_conflicting_direction_quarantines_both():
    a = fixture_event("semantic-direction-a", transaction_reference="SYNTHETIC-common")
    b = fixture_event("semantic-direction-b", transaction_reference=a.transaction_reference, direction=D.OUTFLOW)
    assert all(e.validation_status == V.NEEDS_REVIEW for e in reconcile([a, b]))


@pytest.mark.parametrize("original_direction,reversal_direction,accepted", [
    (D.INFLOW, D.OUTFLOW, True), (D.OUTFLOW, D.INFLOW, True),
    (D.INFLOW, D.NEUTRAL, False), (D.OUTFLOW, D.NEUTRAL, False),
    (D.INFLOW, D.INFLOW, False), (D.OUTFLOW, D.OUTFLOW, False),
    (D.INFLOW, D.UNKNOWN, False), (D.OUTFLOW, D.UNKNOWN, False),
])
def test_reversal_requires_exact_opposite_movement(original_direction, reversal_direction, accepted):
    original = fixture_event("opposite-original", day=10, direction=original_direction)
    reversal = fixture_event("opposite-reversal", transaction_type=T.REVERSAL,
                             reversal_of_event_id=original.event_id, direction=reversal_direction)
    result = next(e for e in reconcile([original, reversal]) if e.event_id == reversal.event_id)
    assert result.validation_status == (V.ACCEPTED if accepted else V.NEEDS_REVIEW)
