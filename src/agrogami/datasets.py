"""Dataset identity, temporal-label and explicit local benchmark adapters."""
import csv
import hashlib
import json
from datetime import timedelta
from pathlib import Path
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
    feature_schema_version: str = Field(default="1.0", min_length=1)
    protected_columns: tuple[str, ...] = ()
    decision_times: tuple[AwareDatetime, ...] = ()
    feature_available_times: tuple[AwareDatetime, ...] = ()
    origination_times: tuple[AwareDatetime, ...] = ()
    outcome_observation_end_times: tuple[AwareDatetime, ...] = ()
    label_available_times: tuple[AwareDatetime, ...] = ()
    available_as_of: AwareDatetime | None = None

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
        for times in (self.origination_times, self.outcome_observation_end_times, self.label_available_times):
            if times and len(times) != n:
                raise ValueError("unaligned outcome temporal vectors")
        return self


class DatasetSplitLineage(Contract):
    """Private, content-bound split metadata; a fingerprint is not authenticity proof."""
    identity: DatasetIdentity
    feature_names: tuple[str, ...]
    feature_schema_version: str
    sample_ids: tuple[str, ...]
    observed_sample_ids: tuple[str, ...]
    sample_count: int = Field(gt=0)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision_times: tuple[AwareDatetime, ...] = ()
    feature_available_times: tuple[AwareDatetime, ...] = ()
    origination_times: tuple[AwareDatetime, ...] = ()
    outcome_observation_end_times: tuple[AwareDatetime, ...] = ()
    label_available_times: tuple[AwareDatetime, ...] = ()
    available_as_of: AwareDatetime | None = None

    @model_validator(mode="after")
    def membership(self) -> "DatasetSplitLineage":
        if self.sample_count != len(self.sample_ids) or len(set(self.sample_ids)) != self.sample_count:
            raise ValueError("split count/membership mismatch")
        if len(set(self.observed_sample_ids)) != len(self.observed_sample_ids) or not set(self.observed_sample_ids) <= set(self.sample_ids):
            raise ValueError("observed split membership mismatch")
        if not self.feature_names or len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("split feature schema mismatch")
        for times in (self.decision_times, self.feature_available_times, self.origination_times,
                      self.outcome_observation_end_times, self.label_available_times):
            if times and len(times) != self.sample_count:
                raise ValueError("split temporal membership mismatch")
        return self


def contract_fingerprint(value: Contract) -> str:
    payload = json.dumps(value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dataset_lineage(data: RiskDataset) -> DatasetSplitLineage:
    data = RiskDataset.model_validate(data.model_dump())
    return DatasetSplitLineage(identity=data.identity, feature_names=data.feature_names,
        feature_schema_version=data.feature_schema_version, sample_ids=data.sample_ids,
        observed_sample_ids=tuple(sid for sid, label in zip(data.sample_ids, data.labels) if label is not None),
        sample_count=len(data.sample_ids), fingerprint=contract_fingerprint(data),
        decision_times=data.decision_times, feature_available_times=data.feature_available_times,
        origination_times=data.origination_times, outcome_observation_end_times=data.outcome_observation_end_times,
        label_available_times=data.label_available_times, available_as_of=data.available_as_of)


def validate_dataset_scope(identity: DatasetIdentity, scope: str) -> None:
    expected = {"SYNTHETIC_DEMO": {"synthetic"},
                "PUBLIC_DATASET_BENCHMARK": {"public credit benchmark", "relational financial benchmark"},
                "REAL_LINKED_OUTCOME_EXPERIMENT": {"real linked outcomes"}}
    if scope not in expected or identity.scope not in expected[scope]:
        raise ValueError("artifact and dataset scope mismatch")
    if scope == "REAL_LINKED_OUTCOME_EXPERIMENT" and identity.target_definition != RESEARCH_TARGET:
        raise ValueError("linked outcome requires the research target")


def validate_temporal_scope(data: RiskDataset | DatasetSplitLineage, scope: str, *,
                            previous: tuple[DatasetSplitLineage, ...] = ()) -> None:
    """One stage boundary for declared scope, leakage and chronological holdouts.

    Real-linked experiments require a complete 180-day observation horizon for
    observed labels. Metadata assertions remain private research evidence,
    not independently verified borrower outcomes.
    """
    # Revalidate even an immutable contract: model_copy(update=...) bypasses validation.
    data = type(data).model_validate(data.model_dump())
    validate_dataset_scope(data.identity, scope)
    if scope != "REAL_LINKED_OUTCOME_EXPERIMENT":
        return
    vectors = (data.decision_times, data.feature_available_times, data.origination_times,
               data.outcome_observation_end_times, data.label_available_times)
    if data.available_as_of is None or any(len(times) != len(data.sample_ids) for times in vectors):
        raise ValueError("real-linked stages require complete decision/origination/outcome/availability metadata")
    observed = (set(data.observed_sample_ids) if isinstance(data, DatasetSplitLineage) else
                {sid for sid, label in zip(data.sample_ids, data.labels) if label is not None})
    for sid, decision, available, origin, end, label_available in zip(data.sample_ids, *vectors):
        if available >= decision or decision > origin:
            raise ValueError("post-decision or post-origination feature leakage")
        if end < origin or label_available < end or label_available > data.available_as_of:
            raise ValueError("invalid outcome or label availability chronology")
        if sid in observed and end < origin + timedelta(days=180):
            raise ValueError("observed research outcomes require a mature 180-day observation horizon")
    for prior in previous:
        validate_temporal_scope(prior, scope)
        if (max(prior.decision_times) >= min(data.decision_times)
                or max(prior.label_available_times) >= min(data.decision_times)
                or prior.available_as_of >= min(data.decision_times)):
            raise ValueError("splits must follow previously available mature outcomes chronologically")


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
