"""Raster preprocessing with an explicit map back to original image coordinates."""
from dataclasses import dataclass
from io import BytesIO
from math import cos, sin, radians
from typing import Any, Callable
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from agrogami.schemas import Source, Provenance, CandidateField, CandidateExtraction
from decimal import Decimal
from .local_models import local_manifest, ArtifactUnavailable
from .bio import LABELS, decode_bio


@dataclass(frozen=True)
class PreparedDocument:
    image: Image.Image
    original_size: tuple[int, int]
    output_to_original: np.ndarray
    warnings: tuple[str, ...]
    operations: tuple[str, ...]

    def provenance(self, source: Source, box: tuple[int, int, int, int], page: int = 1) -> Provenance:
        left, top, right, bottom = box
        if not 0 <= left < right <= self.image.width or not 0 <= top < bottom <= self.image.height:
            raise ValueError("region outside prepared image")
        points = []
        for x, y in ((left, top), (right, top), (right, bottom), (left, bottom)):
            ox, oy, _ = self.output_to_original @ [x, y, 1]
            points.append((float(ox), float(oy)))
        return Provenance(source_hash=source.source_hash, page_number=page, region=tuple(points))


def preprocess(content: bytes, *, orientation: int = 0, deskew_degrees: float | None = None,
               max_dimension: int = 1600) -> PreparedDocument:
    if len(content) > 10_000_000 or not content:
        raise ValueError("image upload exceeds limit or is empty")
    if orientation not in {0, 90, 180, 270} or max_dimension < 32:
        raise ValueError("invalid preprocessing parameters")
    try:
        with Image.open(BytesIO(content)) as raw:
            if raw.width * raw.height > 20_000_000:
                raise ValueError("image pixel limit exceeded")
            # Require orientation to be explicit when EXIF exists; no hidden provenance transform.
            if raw.getexif().get(274, 1) != 1:
                raise ValueError("nontrivial EXIF orientation requires normalized export")
            image = raw.convert("L")
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("invalid raster image") from exc
    original_size = image.size
    warnings = []
    if min(image.size) < 32:
        warnings.append("small_image")
    pixels = np.asarray(image, dtype=float)
    if pixels.std() < 8:
        warnings.append("low_contrast_or_blank")
    if min(image.size) > 2:
        edge_variance = float(np.diff(pixels, axis=0).var() + np.diff(pixels, axis=1).var())
        if edge_variance < 2:
            warnings.append("low_detail")
    transform = np.eye(3)
    operations = ["grayscale"]
    if orientation:
        w, h = image.size
        mapping = {90: [[0, -1, w], [1, 0, 0], [0, 0, 1]],
                   180: [[-1, 0, w], [0, -1, h], [0, 0, 1]],
                   270: [[0, 1, 0], [-1, 0, h], [0, 0, 1]]}[orientation]
        image = image.rotate(orientation, expand=True, fillcolor=255)
        transform = transform @ np.asarray(mapping)
        operations.append(f"orientation:{orientation}")
    if deskew_degrees is None:
        # Conservative line-projection estimate; retain original when no clear improvement.
        base = np.asarray(image) < 128
        base_score = float(base.sum(axis=1).var())
        choices = [(base_score, 0.0)]
        thumb = image.copy()
        thumb.thumbnail((600, 600))
        for angle in (-3.0, -2.0, -1.0, 1.0, 2.0, 3.0):
            candidate = np.asarray(thumb.rotate(angle, fillcolor=255)) < 128
            choices.append((float(candidate.sum(axis=1).var()) * (image.width / thumb.width) ** 2, angle))
        best, angle = max(choices)
        deskew_degrees = angle if best > base_score * 1.2 else 0.0
    if not -10 <= deskew_degrees <= 10:
        raise ValueError("deskew angle outside safe range")
    if deskew_degrees:
        angle = radians(deskew_degrees)
        cx, cy = image.width / 2, image.height / 2
        a, b = cos(angle), -sin(angle)
        transform = transform @ np.array([[a, b, cx - a * cx - b * cy],
                                         [-b, a, cy + b * cx - a * cy], [0, 0, 1]])
        image = image.rotate(deskew_degrees, resample=Image.Resampling.BICUBIC, fillcolor=255)
        operations.append(f"deskew:{deskew_degrees}")
    w, h = image.size
    if max(w, h) > max_dimension:
        ratio = max_dimension / max(w, h)
        image = image.resize((max(1, round(w * ratio)), max(1, round(h * ratio))))
        transform = transform @ np.diag([w / image.width, h / image.height, 1])
        operations.append("resize")
    image = ImageOps.autocontrast(image)
    operations.append("autocontrast")
    return PreparedDocument(image, original_size, transform, tuple(warnings), tuple(operations))


def line_regions(document: PreparedDocument) -> list[tuple[int, int, int, int]]:
    ink = np.asarray(document.image) < 128
    occupied = ink.any(axis=1)
    regions = []
    start = None
    for row, present in enumerate(list(occupied) + [False]):
        if present and start is None:
            start = row
        if not present and start is not None:
            columns = np.flatnonzero(ink[start:row].any(axis=0))
            regions.append((int(columns[0]), start, int(columns[-1]) + 1, row))
            start = None
    return regions


class TrOCRAdapter:
    def __init__(self, recognize: Callable[[Image.Image], str], version: str):
        self.recognize, self.version = recognize, version

    @classmethod
    def load(cls, path) -> "TrOCRAdapter":
        manifest = local_manifest(path, "trocr")
        import torch
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        processor = TrOCRProcessor.from_pretrained(path, local_files_only=True)
        model = VisionEncoderDecoderModel.from_pretrained(path, local_files_only=True)
        if model.config.decoder.model_type != "trocr":
            raise ArtifactUnavailable("checkpoint decoder is not TrOCR")
        model.eval()
        def recognize(image: Image.Image) -> str:
            pixels = processor(images=image.convert("RGB"), return_tensors="pt").pixel_values
            with torch.no_grad():
                ids = model.generate(pixels, max_new_tokens=256)
            return processor.batch_decode(ids, skip_special_tokens=True)[0]
        return cls(recognize, manifest["version"])

    def extract(self, document: PreparedDocument, source: Source,
                regions: list[tuple[int, int, int, int]] | None = None) -> CandidateExtraction:
        fields = {}
        for i, box in enumerate(regions if regions is not None else line_regions(document)):
            location = document.provenance(source, box)
            text = self.recognize(document.image.crop(box))
            fields[f"line:{i}"] = CandidateField(raw_value=text, normalized_value=None, confidence=Decimal(0),
                location=location, parser_name="trocr", parser_version=self.version)
        # No calibrated confidence is available from plain generation: 0 requires human review.
        return CandidateExtraction(source_id=source.source_id, fields=fields)


class LayoutLMv3Adapter:
    def __init__(self, predict: Callable[..., list[list[float]]], version: str):
        self.predict, self.version = predict, version

    @classmethod
    def load(cls, path) -> "LayoutLMv3Adapter":
        manifest = local_manifest(path, "layoutlmv3")
        import torch
        from transformers import AutoProcessor, AutoModelForTokenClassification
        processor = AutoProcessor.from_pretrained(path, local_files_only=True, apply_ocr=False, trust_remote_code=False)
        model = AutoModelForTokenClassification.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        if model.config.model_type != "layoutlmv3":
            raise ArtifactUnavailable("checkpoint is not LayoutLMv3")
        if tuple(model.config.id2label[i] for i in range(len(LABELS))) != LABELS:
            raise ArtifactUnavailable("checkpoint financial labels mismatch")
        model.eval()
        def predict(image: Image.Image, words: list[str], boxes: list[list[int]]) -> list[list[float]]:
            encoded = processor(images=image.convert("RGB"), text=words, boxes=boxes, return_tensors="pt", truncation=False)
            word_ids = encoded.word_ids(0)
            with torch.no_grad():
                logits = model(**encoded).logits[0].tolist()
            rows = []
            for i in range(len(words)):
                indices = [j for j, word_id in enumerate(word_ids) if word_id == i]
                if not indices:
                    raise ValueError("layout words were truncated")
                rows.append(logits[indices[0]])
            return rows
        return cls(predict, manifest["version"])

    def extract(self, document: PreparedDocument, source: Source, words: list[str],
                boxes: list[tuple[int, int, int, int]]) -> CandidateExtraction:
        if len(words) != len(boxes):
            raise ValueError("unaligned words/boxes")
        locations = [document.provenance(source, box) for box in boxes]
        normalized = [[round(1000 * x / document.image.width), round(1000 * y / document.image.height),
                       round(1000 * r / document.image.width), round(1000 * b / document.image.height)]
                      for x, y, r, b in boxes]
        rows = self.predict(document.image, words, normalized)
        if len(rows) != len(words):
            raise ValueError("unaligned layout model output")
        labels = decode_bio(rows)
        fields = {f"{label}:{i}": CandidateField(raw_value=word, normalized_value=None, confidence=Decimal(0),
                  location=location, parser_name="layoutlmv3", parser_version=self.version)
                  for i, (word, label, location) in enumerate(zip(words, labels, locations)) if label != "O"}
        return CandidateExtraction(source_id=source.source_id, fields=fields)
