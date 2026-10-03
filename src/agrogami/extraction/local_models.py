"""Lazy, local-only adapters. A checkpoint manifest is required; no download fallback."""
import json
from pathlib import Path
from typing import Any, Protocol
from decimal import Decimal
from agrogami.schemas import Source, Provenance, CandidateField, CandidateExtraction
from .bio import LABELS, decode_bio


class ArtifactUnavailable(RuntimeError):
    pass


def local_manifest(path: Path, task: str) -> dict[str, Any]:
    manifest = path / "agrogami-extractor.json"
    if not path.is_dir() or not manifest.is_file():
        raise ArtifactUnavailable("local checkpoint and extractor manifest required")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("task") != task or not data.get("version"):
        raise ArtifactUnavailable("checkpoint task/version mismatch")
    if task in {"deberta", "layoutlmv3"} and data.get("labels") != list(LABELS):
        raise ArtifactUnavailable("financial BIO label manifest required")
    return data


class TextPredictor(Protocol):
    def __call__(self, text: str) -> tuple[list[tuple[int, int]], list[list[float]]]: ...


class DebertaAdapter:
    def __init__(self, predictor: TextPredictor, version: str):
        self.predictor, self.version = predictor, version

    @classmethod
    def load(cls, path: Path) -> "DebertaAdapter":
        manifest = local_manifest(path, "deberta")
        import torch
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False, use_fast=True)
        model = AutoModelForTokenClassification.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        if model.config.model_type != "deberta-v2":
            raise ArtifactUnavailable("checkpoint is not a DeBERTa-family model")
        if tuple(model.config.id2label[i] for i in range(len(LABELS))) != LABELS:
            raise ArtifactUnavailable("checkpoint labels differ from manifest")
        model.eval()

        def predict(text: str) -> tuple[list[tuple[int, int]], list[list[float]]]:
            encoded = tokenizer(text, return_offsets_mapping=True, return_tensors="pt", truncation=False)
            offsets = encoded.pop("offset_mapping")[0].tolist()
            if len(offsets) > model.config.max_position_embeddings:
                raise ValueError("text exceeds checkpoint context; explicit chunking required")
            with torch.no_grad():
                logits = model(**encoded).logits[0].tolist()
            pairs = [(tuple(offset), row) for offset, row in zip(offsets, logits) if offset[1] > offset[0]]
            return [p[0] for p in pairs], [p[1] for p in pairs]
        return cls(predict, manifest["version"])

    def extract(self, text: str, source: Source) -> CandidateExtraction:
        import numpy as np
        offsets, logits = self.predictor(text)
        if len(offsets) != len(logits):
            raise ValueError("unaligned model output")
        labels = decode_bio(logits)
        spans: list[tuple[str, int, int, list[float]]] = []
        previous_end = 0
        for (start, end), label, scores in zip(offsets, labels, logits):
            if not previous_end <= start < end <= len(text):
                raise ValueError("invalid model source offset")
            previous_end = end
            if label == "O":
                continue
            weights = np.exp(np.asarray(scores) - max(scores))
            confidence = float(weights[LABELS.index(label)] / weights.sum())
            if label.startswith("B-"):
                spans.append((label[2:], start, end, [confidence]))
            else:
                kind, begin, _, conf = spans[-1]
                spans[-1] = kind, begin, end, conf + [confidence]
        fields = {}
        for i, (kind, start, end, conf) in enumerate(spans):
            fields[f"{kind}:{i}"] = CandidateField(raw_value=text[start:end], normalized_value=None,
                confidence=Decimal(str(min(conf))), location=Provenance(source_hash=source.source_hash,
                span_start=start, span_end=end), parser_name="deberta-v3-small", parser_version=self.version)
        return CandidateExtraction(source_id=source.source_id, fields=fields)
