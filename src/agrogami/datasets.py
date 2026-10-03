"""Dataset identity, temporal-label and explicit local benchmark adapters."""
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from pydantic import AwareDatetime, Field, model_validator
from agrogami.schemas import Contract

RESEARCH_TARGET = "Initially current loan reaches >=90 DPD within 180 days of origination"


class DatasetIdentity(Contract):
    dataset_id: str = Field(min_length=1)
    target_definition: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    limitations: tuple[str, ...]


DATASETS = {
    "default_credit_card": DatasetIdentity(dataset_id="UCI Default of Credit Card Clients",
        target_definition="Default payment next month", scope="public credit benchmark",
        limitations=("Taiwan credit-card borrowers; not Agrogami 90-DPD/180-day outcome",)),
    "south_german": DatasetIdentity(dataset_id="UCI South German Credit",
        target_definition="Good/bad credit risk classification in original dataset", scope="public credit benchmark",
        limitations=("Historical German credit; preserve original label coding",)),
    "funsd": DatasetIdentity(dataset_id="FUNSD", target_definition="Form entity labels and relations",
        scope="document benchmark", limitations=("English scanned forms; not Bangla financial records",)),
    "banglawriting": DatasetIdentity(dataset_id="BanglaWriting", target_definition="Annotated Bengali handwriting",
        scope="handwriting benchmark", limitations=("Verify supplied release, licensing and annotation units; not loan outcomes",)),
    "berka": DatasetIdentity(dataset_id="Berka financial dataset", target_definition="Original loan status in supplied release",
        scope="relational financial benchmark", limitations=("Historical Czech bank data; 90-DPD/180-day target not assumed",)),
}


class PerformanceObservation(Contract):
    timestamp: AwareDatetime
    days_past_due: int = Field(ge=0)


class LoanOutcome(Contract):
    loan_id: str
    origination_time: AwareDatetime
    initially_current: bool
    followup_end: AwareDatetime
    complete_followup: bool
    observations: tuple[PerformanceObservation, ...]

    @model_validator(mode="after")
    def chronology(self) -> "LoanOutcome":
        if self.followup_end < self.origination_time:
            raise ValueError("invalid follow-up chronology")
        if any(not self.origination_time <= o.timestamp <= self.followup_end for o in self.observations):
            raise ValueError("observation outside follow-up")
        return self

    def label(self) -> int | None:
        if not self.initially_current:
            return None
        endpoint = self.origination_time + timedelta(days=180)
        if any(o.days_past_due >= 90 and o.timestamp <= endpoint for o in self.observations):
            return 1
        if not self.complete_followup or self.followup_end < endpoint:
            return None
        return 0


class RiskDataset(Contract):
    identity: DatasetIdentity
    sample_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    labels: tuple[int | None, ...]
    protected_columns: tuple[str, ...] = ()
    decision_times: tuple[AwareDatetime, ...] = ()
    feature_available_times: tuple[AwareDatetime, ...] = ()

    @model_validator(mode="after")
    def aligned(self) -> "RiskDataset":
        from math import isfinite
        n = len(self.sample_ids)
        if not n or len(set(self.sample_ids)) != n or len(self.values) != n or len(self.labels) != n:
            raise ValueError("unaligned or duplicated sample identities")
        if not self.feature_names or len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("unique feature names required")
        if set(self.feature_names) & set(self.protected_columns):
            raise ValueError("protected attributes cannot be baseline inputs")
        if any(len(row) != len(self.feature_names) or not all(isfinite(v) for v in row) for row in self.values):
            raise ValueError("invalid risk feature matrix")
        if any(y not in {0, 1, None} for y in self.labels):
            raise ValueError("binary/censored labels required")
        if bool(self.decision_times) != bool(self.feature_available_times):
            raise ValueError("both temporal vectors required")
        if self.decision_times:
            if len(self.decision_times) != n or len(self.feature_available_times) != n:
                raise ValueError("unaligned temporal vectors")
            if any(a >= d for a, d in zip(self.feature_available_times, self.decision_times)):
                raise ValueError("post-decision leakage")
        return self


def load_risk_csv(path: Path, *, dataset_key: str, target_column: str, id_column: str,
                  feature_columns: tuple[str, ...], target_mapping: dict[str, int],
                  protected_columns: tuple[str, ...]) -> RiskDataset:
    identity = DATASETS[dataset_key]
    if identity.scope != "public credit benchmark" and dataset_key != "berka":
        raise ValueError("dataset is not a risk benchmark")
    if target_column in feature_columns or id_column in feature_columns:
        raise ValueError("target/identity leakage")
    with path.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    return RiskDataset(identity=identity, sample_ids=tuple(r[id_column] for r in records),
        feature_names=feature_columns, values=tuple(tuple(float(r[f]) for f in feature_columns) for r in records),
        labels=tuple(target_mapping[r[target_column]] for r in records), protected_columns=protected_columns)


def local_dataset_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("dataset file missing or outside declared root")
    return path


class DocumentBenchmarkSample(Contract):
    dataset_identity: DatasetIdentity
    sample_id: str
    image_reference: str
    words: tuple[str, ...]
    boxes: tuple[tuple[int, int, int, int], ...]
    original_labels: tuple[str, ...]
    original_relations: tuple[tuple[int, int], ...] = ()
    transcript: str | None = None


def load_funsd_annotation(path: Path, *, sample_id: str, image_reference: str) -> DocumentBenchmarkSample:
    """Retain FUNSD form labels/links; do not reinterpret them as financial labels."""
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    words, boxes, labels, links = [], [], [], set()
    for entity in data["form"]:
        for word in entity["words"]:
            if word["text"]:
                words.append(word["text"])
                boxes.append(tuple(word["box"]))
                labels.append(entity["label"])
        links.update(tuple(link) for link in entity.get("linking", []))
    return DocumentBenchmarkSample(dataset_identity=DATASETS["funsd"], sample_id=sample_id,
        image_reference=image_reference, words=tuple(words), boxes=tuple(boxes),
        original_labels=tuple(labels), original_relations=tuple(sorted(links)))


def load_handwriting_manifest(path: Path, *, root: Path) -> list[DocumentBenchmarkSample]:
    """Explicit normalized BanglaWriting release manifest, not an invented release layout."""
    import json
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    output = []
    for row in rows:
        local_dataset_path(root, row["image_reference"])
        output.append(DocumentBenchmarkSample(dataset_identity=DATASETS["banglawriting"],
            sample_id=row["sample_id"], image_reference=row["image_reference"], transcript=row["transcript"],
            words=(), boxes=(), original_labels=()))
    if not output or len({r.sample_id for r in output}) != len(output):
        raise ValueError("nonempty unique handwriting sample identities required")
    return output
