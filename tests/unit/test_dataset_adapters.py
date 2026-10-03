import json
import pytest
from agrogami.datasets import load_risk_csv, load_funsd_annotation, load_handwriting_manifest, local_dataset_path


def test_public_risk_csv_retains_original_target_and_protected_separation(tmp_path):
    path = tmp_path / "risk.csv"
    path.write_text("id,amount,target,group\na,10,good,A\nb,20,bad,B\n")
    data = load_risk_csv(path, dataset_key="south_german", target_column="target", id_column="id",
                         feature_columns=("amount",), target_mapping={"good": 0, "bad": 1}, protected_columns=("group",))
    assert data.identity.dataset_id == "UCI South German Credit"
    assert data.labels == (0, 1)
    assert data.feature_names == ("amount",)
    with pytest.raises(ValueError):
        load_risk_csv(path, dataset_key="south_german", target_column="target", id_column="id",
                      feature_columns=("group",), target_mapping={"good": 0, "bad": 1}, protected_columns=("group",))


def test_funsd_original_labels_are_not_financial_fields(tmp_path):
    path = tmp_path / "form.json"
    path.write_text(json.dumps({"form": [{"label": "question", "words": [{"text": "Total", "box": [0, 0, 20, 10]}], "linking": [[1, 2]]}]}))
    sample = load_funsd_annotation(path, sample_id="SYNTHETIC-test", image_reference="a.png")
    assert sample.original_labels == ("question",)
    assert sample.original_relations == ((1, 2),)


def test_banglawriting_normalized_manifest_and_path_boundary(tmp_path):
    (tmp_path / "image.png").write_bytes(b"synthetic path-only fixture")
    path = tmp_path / "manifest.jsonl"
    path.write_text(json.dumps({"sample_id": "SYNTHETIC", "image_reference": "image.png", "transcript": "invented"}))
    assert load_handwriting_manifest(path, root=tmp_path)[0].transcript == "invented"
    with pytest.raises(ValueError):
        local_dataset_path(tmp_path, "../outside.png")
