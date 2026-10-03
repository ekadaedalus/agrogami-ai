"""Evidence-gated immutable assessments. No low-score substitute for unknown evidence."""
from enum import StrEnum
from datetime import datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4
from pydantic import AwareDatetime, Field, model_validator
from agrogami.schemas import Contract, FeatureSnapshot, Coverage, CanonicalEvent, ValidationStatus, utcnow
from agrogami.features import build_features
from agrogami.features.engine import current_as_of
from agrogami.risk.models import ModelArtifact, RiskModel, ValidationScope
from agrogami.calibration.core import Calibrator, project_score
from agrogami.explainability.core import evidence_reasons, EvidenceReason, TreeExplanation


class SnapshotStatus(StrEnum):
    READY = "READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    ILLUSTRATIVE = "ILLUSTRATIVE"


class AssessmentSnapshot(Contract):
    assessment_id: UUID = Field(default_factory=uuid4)
    applicant_id: UUID
    assessment_time: AwareDatetime
    status: SnapshotStatus
    evidence_version_ids: tuple[UUID, ...]
    feature_schema_version: str
    feature_snapshot: FeatureSnapshot
    model_artifact: ModelArtifact | None = None
    model_validation_scope: ValidationScope = ValidationScope.UNTRAINED
    raw_probability: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    calibrated_probability: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    unclipped_display_score: float | None = None
    display_score: int | None = Field(default=None, ge=300, le=850)
    calibrator_version: str | None = None
    calibration_dataset_id: str | None = None
    explanation_metadata: TreeExplanation | None = None
    reasons: tuple[EvidenceReason, ...] = ()
    fairness_policy_metadata: dict[str, str] = Field(default_factory=lambda: {
        "policy_version": "research-gate-v1", "fairness": "not_evaluated_for_this_applicant",
        "decision": "none; research display only"})
    limitations: tuple[str, ...]
    created_at: AwareDatetime = Field(default_factory=utcnow)
    supersedes_assessment_id: UUID | None = None

    @model_validator(mode="after")
    def consistency(self) -> "AssessmentSnapshot":
        if self.feature_snapshot.applicant_id != self.applicant_id or self.feature_snapshot.scoring_time != self.assessment_time:
            raise ValueError("assessment/feature identity mismatch")
        if self.feature_schema_version != self.feature_snapshot.feature_schema_version:
            raise ValueError("assessment feature version mismatch")
        probabilities_present = self.raw_probability is not None or self.calibrated_probability is not None
        score_present = self.display_score is not None or self.unclipped_display_score is not None
        if self.status in {SnapshotStatus.NEEDS_REVIEW, SnapshotStatus.INSUFFICIENT_EVIDENCE} and (probabilities_present or score_present):
            raise ValueError("review/insufficient snapshots must withhold probabilities and scores")
        if probabilities_present or score_present:
            if (self.raw_probability is None or self.calibrated_probability is None or self.display_score is None
                    or self.unclipped_display_score is None or self.model_artifact is None or self.calibrator_version is None):
                raise ValueError("complete scoring lineage required")
            if self.model_validation_scope in {ValidationScope.UNTRAINED, ValidationScope.PUBLIC_DATASET_BENCHMARK}:
                raise ValueError("untrained/public artifacts cannot score borrower assessments")
        if self.status == SnapshotStatus.READY and self.model_validation_scope != ValidationScope.REAL_LINKED_OUTCOME_EXPERIMENT:
            raise ValueError("READY requires explicitly real-linked research artifact")
        if self.model_artifact and self.model_artifact.scope != self.model_validation_scope:
            raise ValueError("artifact/snapshot scope mismatch")
        return self


def assess(events: list[CanonicalEvent], *, applicant_id: UUID, t0: datetime, coverage: Coverage,
           window_days: int = 30, model: RiskModel | None = None, calibrator: Calibrator | None = None,
           explanation_provider: Callable[[dict[str, float]], TreeExplanation] | None = None,
           previous_id: UUID | None = None) -> AssessmentSnapshot:
    snapshot = build_features(events, applicant_id=applicant_id, t0=t0, window_days=window_days, coverage=coverage)
    available = current_as_of([e for e in events if e.applicant_id == applicant_id], t0)
    start = t0 - timedelta(days=window_days)
    pending = any(e.validation_status != ValidationStatus.ACCEPTED and e.event_timestamp >= start for e in available)
    sufficient = snapshot.features["observed_day_share"].value == 1
    if snapshot.features["accepted_event_share"].value is not None and snapshot.features["accepted_event_share"].value < 1:
        pending = True
    limitations = ["Research snapshot, not a lending decision", "Project score is not FICO or bureau-equivalent",
                   "Scaling does not create calibration", "Coverage is caller-attested"]
    values = dict(applicant_id=applicant_id, assessment_time=t0,
        evidence_version_ids=tuple(sorted((e.event_id for e in available), key=str)),
        feature_schema_version=snapshot.feature_schema_version, feature_snapshot=snapshot,
        model_artifact=model.artifact if model else None,
        model_validation_scope=model.artifact.scope if model else ValidationScope.UNTRAINED,
        reasons=evidence_reasons(snapshot, available), supersedes_assessment_id=previous_id)
    status = SnapshotStatus.NEEDS_REVIEW if pending else SnapshotStatus.INSUFFICIENT_EVIDENCE
    if not sufficient:
        limitations.append("Incomplete observation coverage; probabilities and score withheld")
    elif pending:
        limitations.append("Unresolved evidence review; probabilities and score withheld")
    elif model is None or model.artifact.scope == ValidationScope.UNTRAINED or calibrator is None:
        status = SnapshotStatus.NEEDS_REVIEW
        limitations.append("Trained model and matched holdout calibrator unavailable")
    elif model.artifact.scope == ValidationScope.PUBLIC_DATASET_BENCHMARK:
        status = SnapshotStatus.ILLUSTRATIVE
        limitations.append("Public benchmark is not an Agrogami borrower model; scoring withheld")
    else:
        artifact = model.artifact
        if artifact.window_days != window_days or artifact.feature_schema_version != snapshot.feature_schema_version:
            raise ValueError("model feature schema/window mismatch")
        if calibrator.artifact.model_artifact_id != str(artifact.artifact_id) or calibrator.artifact.model_version != artifact.version:
            raise ValueError("calibrator does not belong to model artifact")
        features = {}
        for name in artifact.feature_names:
            feature = snapshot.features.get(name)
            if feature is None or feature.value is None or isinstance(feature.value, (dict, tuple)) or feature.reasons:
                limitations.append("Required model feature unavailable or incomplete; scoring withheld")
                break
            features[name] = float(feature.value)
        else:
            raw = model.predict(features)
            calibrated = calibrator.predict(raw)
            score = project_score(calibrated)
            status = SnapshotStatus.ILLUSTRATIVE if artifact.scope == ValidationScope.SYNTHETIC_DEMO else SnapshotStatus.READY
            limitations.extend(artifact.limitations)
            limitations.append("No externally validated underwriting claim")
            explanation = explanation_provider(features) if explanation_provider else None
            if explanation is None:
                limitations.append("TreeSHAP explanation/background not configured; descriptive evidence reasons only")
            if explanation is not None and explanation.model_artifact_id != artifact.artifact_id:
                raise ValueError("explanation artifact mismatch")
            values.update(raw_probability=raw, calibrated_probability=calibrated,
                unclipped_display_score=score.unclipped_score, display_score=score.display_score,
                calibrator_version=calibrator.artifact.version,
                calibration_dataset_id=calibrator.artifact.calibration_dataset_id, explanation_metadata=explanation)
    return AssessmentSnapshot(status=status, limitations=tuple(limitations), **values)
