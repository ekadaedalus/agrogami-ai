"""Explicit local extraction training/evaluation entrypoints; never downloads artifacts."""
import json
from pathlib import Path
from typing import Literal, Any
from pydantic import Field, model_validator
from agrogami.schemas import Contract
from agrogami.datasets import local_dataset_path
from .bio import TokenSample, LABELS, token_metrics, validate_bio
from .local_models import ArtifactUnavailable


class DocumentAnnotation(Contract):
    sample_id: str
    dataset_id: str
    image: str
    text: str | None = None
    words: tuple[str, ...] = ()
    boxes: tuple[tuple[int, int, int, int], ...] = ()  # normalized 0..1000
    labels: tuple[str, ...] = ()

    @model_validator(mode="after")
    def alignment(self) -> "DocumentAnnotation":
        if not len(self.words) == len(self.boxes) == len(self.labels):
            raise ValueError("unaligned document annotation")
        validate_bio(self.labels)
        if any(not 0 <= l < r <= 1000 or not 0 <= t < b <= 1000 for l, t, r, b in self.boxes):
            raise ValueError("invalid normalized annotation box")
        return self


def load_annotations(path: Path, task: str) -> list[TokenSample | DocumentAnnotation]:
    model = TokenSample if task == "deberta" else DocumentAnnotation
    records = [model.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records or len({r.sample_id for r in records}) != len(records) or len({r.dataset_id for r in records}) != 1:
        raise ValueError("one explicit dataset and unique annotated sample IDs required")
    return records


def validate_split(training: list[Any], evaluation: list[Any]) -> None:
    if {r.sample_id for r in training} & {r.sample_id for r in evaluation}:
        raise ValueError("extraction train/evaluation overlap")
    if {r.dataset_id for r in training} != {r.dataset_id for r in evaluation}:
        raise ValueError("cross-dataset evaluation requires a separately declared experiment")


def train_local(*, task: Literal["deberta", "trocr", "layoutlmv3"], base_checkpoint: Path,
                train_file: Path, evaluation_file: Path, data_root: Path, output: Path,
                version: str, epochs: int = 1) -> dict[str, Any]:
    """Small explicit torch loop; evaluation is held out, metrics are computed from outputs."""
    if not base_checkpoint.is_dir():
        raise ArtifactUnavailable("local base checkpoint required")
    if output.exists() or epochs < 1 or not version:
        raise ValueError("new output directory, version and positive epochs required")
    training, evaluation = load_annotations(train_file, task), load_annotations(evaluation_file, task)
    validate_split(training, evaluation)
    import torch
    torch.manual_seed(0)
    from PIL import Image
    from transformers import (AutoTokenizer, AutoModelForTokenClassification, AutoProcessor,
                              TrOCRProcessor, VisionEncoderDecoderModel)
    id2label = dict(enumerate(LABELS))
    label2id = {label: i for i, label in id2label.items()}
    if task == "trocr":
        processor = TrOCRProcessor.from_pretrained(base_checkpoint, local_files_only=True)
        model = VisionEncoderDecoderModel.from_pretrained(base_checkpoint, local_files_only=True)
    else:
        processor = (AutoTokenizer.from_pretrained(base_checkpoint, local_files_only=True, use_fast=True)
                     if task == "deberta" else AutoProcessor.from_pretrained(base_checkpoint, local_files_only=True, apply_ocr=False))
        model = AutoModelForTokenClassification.from_pretrained(base_checkpoint, local_files_only=True,
            id2label=id2label, label2id=label2id, num_labels=len(LABELS), ignore_mismatched_sizes=True, trust_remote_code=False)
    expected_type = {"deberta": "deberta-v2", "layoutlmv3": "layoutlmv3"}.get(task)
    if expected_type and model.config.model_type != expected_type:
        raise ArtifactUnavailable("local base architecture does not match extraction task")
    if task == "trocr" and model.config.decoder.model_type != "trocr":
        raise ArtifactUnavailable("local recognition decoder must be TrOCR")

    def encode(record: Any) -> dict:
        if task == "deberta":
            encoded = processor(list(record.tokens), is_split_into_words=True, return_tensors="pt", truncation=False)
        else:
            with Image.open(local_dataset_path(data_root, record.image)) as raw:
                image = raw.convert("RGB")
            if task == "trocr":
                if record.text is None:
                    raise ValueError("recognition text annotation required")
                pixels = processor(images=image, return_tensors="pt").pixel_values
                labels = processor.tokenizer(record.text, return_tensors="pt").input_ids
                return {"pixel_values": pixels, "labels": labels}
            encoded = processor(images=image, text=list(record.words), boxes=[list(b) for b in record.boxes],
                                return_tensors="pt", truncation=False)
        word_ids = encoded.word_ids(0)
        labels, previous = [], None
        for word_id in word_ids:
            labels.append(-100 if word_id is None or word_id == previous else label2id[record.labels[word_id]])
            previous = word_id
        encoded["labels"] = torch.tensor([labels])
        return dict(encoded)

    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
    model.train()
    for _ in range(epochs):
        for record in training:
            optimizer.zero_grad()
            loss = model(**encode(record)).loss
            if not torch.isfinite(loss):
                raise ValueError("nonfinite extraction training loss")
            loss.backward()
            optimizer.step()
    model.eval()
    losses = []
    with torch.no_grad():
        for record in evaluation:
            losses.append(float(model(**encode(record)).loss))
    output.mkdir(parents=True)
    model.save_pretrained(output, safe_serialization=True)
    processor.save_pretrained(output)
    manifest = {"task": task, "version": version, "dataset_id": training[0].dataset_id,
                "training_sample_ids": [r.sample_id for r in training], "evaluation_sample_ids": [r.sample_id for r in evaluation],
                "labels": list(LABELS) if task != "trocr" else [], "heldout_loss": sum(losses) / len(losses)}
    (output / "agrogami-extractor.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def character_error_rate(expected: str, observed: str) -> float | None:
    if not expected:
        return None
    previous = list(range(len(observed) + 1))
    for i, a in enumerate(expected, 1):
        row = [i]
        for j, b in enumerate(observed, 1):
            row.append(min(row[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = row
    return previous[-1] / len(expected)
