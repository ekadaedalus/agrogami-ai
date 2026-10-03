import pytest
from agrogami.fixtures import scenarios, fixture_sources, synthetic_candidate, APPLICANT, T0, coverage
from agrogami.schemas import CanonicalEvent, FeatureSnapshot
from agrogami.storage import Store
from agrogami.validation.rules import reconcile
from agrogami.features import build_all_windows


@pytest.mark.parametrize("name", sorted(scenarios()))
def test_synthetic_persist_reconcile_feature_roundtrip(tmp_path, name):
    url = "sqlite:///" + str(tmp_path / "pipeline.db")
    store = Store(url)
    originals = scenarios()[name]
    for source in fixture_sources(originals):
        store.save(source)
    for event in originals:
        store.save(synthetic_candidate(event))
    accepted = reconcile(originals)
    for event in accepted:
        store.save(event)
    snapshots = build_all_windows(store.events(APPLICANT), applicant_id=APPLICANT, t0=T0, coverage=coverage())
    for value in snapshots.values():
        store.save(value)
    store.engine.dispose()
    reopened = Store(url)
    for event in accepted:
        assert reopened.get(CanonicalEvent, event.event_id) == event
    for value in snapshots.values():
        assert reopened.get(FeatureSnapshot, value.snapshot_id) == value
        assert value == build_all_windows(reopened.events(APPLICANT), applicant_id=APPLICANT,
                                         t0=T0, coverage=coverage())[value.window_days]
    reopened.engine.dispose()
