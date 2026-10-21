"""Existing synthetic suites explicitly exercise the isolated local demo mode."""
from pathlib import Path

import pytest


def pytest_configure(config):
    # pytest recreates only the final basetemp folder; the gitignored .pytest_temp parent
    # does not exist in a fresh clone, so create it before any tmp_path is requested.
    if config.option.basetemp:
        Path(config.option.basetemp).absolute().parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def synthetic_local_context(monkeypatch):
    monkeypatch.setenv("AGROGAMI_LOCAL_DEMO_MODE", "true")
