"""Exercise loader calls without torch/transformer installation or any checkpoint download."""
import json
import sys
from types import SimpleNamespace
import pytest
from agrogami.extraction.bio import LABELS
from agrogami.extraction.local_models import DebertaAdapter
from agrogami.extraction.documents import TrOCRAdapter, LayoutLMv3Adapter


@pytest.mark.parametrize("task,adapter", [("deberta", DebertaAdapter), ("trocr", TrOCRAdapter), ("layoutlmv3", LayoutLMv3Adapter)])
def test_loaders_require_local_files_and_matching_architecture(tmp_path, monkeypatch, task, adapter):
    calls = []
    def load_processor(path, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace()
    def load_model(path, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(config=SimpleNamespace(model_type="deberta-v2" if task == "deberta" else "layoutlmv3",
            decoder=SimpleNamespace(model_type="trocr"), id2label=dict(enumerate(LABELS))), eval=lambda: None)
    processor = SimpleNamespace(from_pretrained=load_processor)
    model = SimpleNamespace(from_pretrained=load_model)
    fake = SimpleNamespace(AutoTokenizer=processor, AutoProcessor=processor, TrOCRProcessor=processor,
                           AutoModelForTokenClassification=model, VisionEncoderDecoderModel=model)
    monkeypatch.setitem(sys.modules, "transformers", fake)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace())
    (tmp_path / "agrogami-extractor.json").write_text(json.dumps({"task": task, "version": "fake-loader", "labels": list(LABELS)}))
    loaded = adapter.load(tmp_path)
    assert loaded.version == "fake-loader"
    assert all(call["local_files_only"] is True for call in calls)


def test_training_preflight_fails_before_import_or_download(tmp_path):
    from agrogami.extraction.training import train_local
    from agrogami.extraction.local_models import ArtifactUnavailable
    with pytest.raises(ArtifactUnavailable):
        train_local(task="deberta", base_checkpoint=tmp_path / "missing", train_file=tmp_path / "missing-train",
                    evaluation_file=tmp_path / "missing-test", data_root=tmp_path, output=tmp_path / "out", version="test")
