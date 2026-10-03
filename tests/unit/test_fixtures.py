from agrogami.fixtures import scenarios, fixture_sources


def test_fixture_determinism_and_labels():
    first, second = scenarios(), scenarios()
    assert first == second
    assert len(first) == 20
    assert all(source.synthetic and source.metadata["label"] == "SYNTHETIC"
               for events in first.values() for source in fixture_sources(events))
