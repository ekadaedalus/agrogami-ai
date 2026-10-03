"""Opt-in load checks for explicitly supplied trained local artifacts; no downloads."""
import os
from pathlib import Path
import pytest
from agrogami.extraction.local_models import DebertaAdapter
from agrogami.extraction.documents import TrOCRAdapter, LayoutLMv3Adapter


@pytest.mark.heavy
@pytest.mark.parametrize("variable,adapter", [("AGROGAMI_TEST_DEBERTA_CHECKPOINT", DebertaAdapter),
    ("AGROGAMI_TEST_TROCR_CHECKPOINT", TrOCRAdapter), ("AGROGAMI_TEST_LAYOUTLMV3_CHECKPOINT", LayoutLMv3Adapter)])
def test_supplied_checkpoint_loads_locally(variable, adapter):
    configured = os.environ.get(variable)
    if not configured:
        pytest.skip("Explicit trained local checkpoint not supplied")
    loaded = adapter.load(Path(configured))
    assert loaded.version
