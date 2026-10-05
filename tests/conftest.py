"""Existing synthetic suites explicitly exercise the isolated local demo mode."""
import pytest


@pytest.fixture(autouse=True)
def synthetic_local_context(monkeypatch):
    monkeypatch.setenv("AGROGAMI_LOCAL_DEMO_MODE", "true")
