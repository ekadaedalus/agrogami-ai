from io import BytesIO
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
import pytest
from agrogami.fixtures import APPLICANT
from agrogami.events.intake import intake
from agrogami.schemas import SourceType
from agrogami.extraction.bio import LABELS, decode_bio, validate_bio, TokenSample, token_metrics
from agrogami.extraction.local_models import DebertaAdapter, local_manifest, ArtifactUnavailable
from agrogami.extraction.documents import preprocess, line_regions, TrOCRAdapter, LayoutLMv3Adapter
from agrogami.extraction.training import character_error_rate, load_annotations, validate_split, DocumentAnnotation


def image_bytes(size=(160, 80), blank=False):
    image = Image.new("RGB", size, "white")
    if not blank:
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 90, 16), fill="black")
        draw.rectangle((10, 35, 120, 41), fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def logits(label):
    return [10.0 if name == label else -10.0 for name in LABELS]


@pytest.mark.parametrize("labels", [["I-AMOUNT"], ["B-AMOUNT", "I-FEE"], ["UNKNOWN"]])
def test_invalid_bio(labels):
    with pytest.raises(ValueError):
        validate_bio(labels)


def test_constrained_decoder_and_fake_deberta_preserve_source():
    rows = [logits("I-AMOUNT"), logits("I-AMOUNT")]
    predicted = decode_bio(rows)
    validate_bio(predicted)
    assert predicted[0] != "I-AMOUNT"
    text = "Tk 100"
    source = intake(text.encode(), APPLICANT, SourceType.SYNTHETIC_FIXTURE, synthetic=True)
    adapter = DebertaAdapter(lambda value: ([(3, 6)], [logits("B-AMOUNT")]), "fake-v1")
    candidate = adapter.extract(text, source)
    assert list(candidate.fields.values())[0].raw_value == "100"
    assert list(candidate.fields.values())[0].normalized_value is None


@pytest.mark.parametrize("task", ["deberta", "trocr", "layoutlmv3"])
def test_missing_checkpoint_never_downloads(tmp_path, task):
    with pytest.raises(ArtifactUnavailable):
        local_manifest(tmp_path, task)


def test_generic_layout_checkpoint_not_financial_extractor(tmp_path):
    (tmp_path / "agrogami-extractor.json").write_text(json.dumps({"task": "layoutlmv3", "version": "base", "labels": ["LABEL_0"]}))
    with pytest.raises(ArtifactUnavailable):
        LayoutLMv3Adapter.load(tmp_path)


def test_preprocessing_lines_resize_and_provenance():
    content = image_bytes()
    source = intake(content, APPLICANT, SourceType.SYNTHETIC_FIXTURE, synthetic=True)
    prepared = preprocess(content, max_dimension=80, deskew_degrees=0)
    assert prepared.image.mode == "L"
    assert prepared.image.size == (80, 40)
    regions = line_regions(prepared)
    assert len(regions) == 2
    location = prepared.provenance(source, (0, 0, 80, 40))
    assert location.region == ((0, 0), (160, 0), (160, 80), (0, 80))


@pytest.mark.parametrize("orientation", [0, 90, 180, 270])
def test_orientation_map_and_image_size(orientation):
    prepared = preprocess(image_bytes(), orientation=orientation, deskew_degrees=0)
    assert prepared.image.size == ((80, 160) if orientation in {90, 270} else (160, 80))
    assert np.isfinite(prepared.output_to_original).all()


def test_deskew_transform_is_recorded():
    prepared = preprocess(image_bytes(), deskew_degrees=2)
    assert "deskew:2" in prepared.operations


def test_legibility_blank_and_invalid_image():
    assert "low_contrast_or_blank" in preprocess(image_bytes(blank=True)).warnings
    with pytest.raises(ValueError):
        preprocess(b"invalid image")


def test_trocr_and_layout_fakes_only_make_candidates():
    content = image_bytes()
    source = intake(content, APPLICANT, SourceType.SYNTHETIC_FIXTURE, synthetic=True)
    document = preprocess(content, deskew_degrees=0)
    ocr = TrOCRAdapter(lambda image: "SYNTHETIC 100", "fake").extract(document, source, [(10, 10, 90, 20)])
    assert ocr.fields["line:0"].confidence == 0
    assert ocr.fields["line:0"].normalized_value is None
    layout = LayoutLMv3Adapter(lambda image, words, boxes: [logits("B-AMOUNT")], "fake")
    candidate = layout.extract(document, source, ["100"], [(10, 10, 90, 20)])
    assert list(candidate.fields.values())[0].location.region is not None
    with pytest.raises(ValueError):
        layout.extract(document, source, ["100"], [])


def test_token_annotation_alignment_and_evaluation():
    sample = TokenSample(sample_id="1", dataset_id="synthetic", text="Tk 100", tokens=("Tk", "100"),
                         offsets=((0, 2), (3, 6)), labels=("O", "B-AMOUNT"))
    assert token_metrics(list(sample.labels), list(sample.labels))["token_f1"] == 1
    assert character_error_rate("abc", "adc") == pytest.approx(1 / 3)
    assert character_error_rate("", "abc") is None
    with pytest.raises(ValueError):
        validate_split([sample], [sample])


def test_document_annotations_validate_boxes():
    with pytest.raises(ValueError):
        DocumentAnnotation(sample_id="1", dataset_id="synthetic", image="a.png", words=("a",),
                           boxes=((100, 0, 10, 100),), labels=("B-AMOUNT",))
