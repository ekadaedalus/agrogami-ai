"""Synthetic experiment membership stays in private immutable records."""
from fastapi.testclient import TestClient

from agrogami.api.app import create_app, Role
from agrogami.application import ApplicationService
from agrogami.assessment import AssessmentSnapshot
from agrogami.fixtures import APPLICANT, T0, coverage
from agrogami.risk.models import ModelArtifact, LogisticRiskModel, ValidationScope
from agrogami.storage import Store


def test_public_assessment_views_omit_private_training_membership(tmp_path):
    artifact = ModelArtifact(version="SYNTHETIC-private-lineage", algorithm="regularized_logistic",
        scope=ValidationScope.SYNTHETIC_DEMO, dataset_id="SYNTHETIC-private-lineage",
        target_definition="Invented label", feature_names=("external_inflow_total",),
        training_sample_ids=("SYNTHETIC-private-training-member",))
    store = Store("sqlite:///" + str(tmp_path / "synthetic.db"))
    service = ApplicationService(store, tmp_path / "sources",
        model=LogisticRiskModel(artifact, [0], 0, [0], [1]))
    try:
        with TestClient(create_app(service, tokens={"synthetic-review": Role.reviewer})) as client:
            response = client.post("/api/v1/assessments", headers={"X-Agrogami-Token": "synthetic-review"},
                json={"applicant_id": str(APPLICANT), "assessment_time": T0.isoformat(),
                      "coverage": coverage().model_dump(mode="json")})
            assert response.status_code == 201
            assert "SYNTHETIC-private-training-member" not in response.text
            identifier = response.json()["assessment_id"]
            for path in (f"assessments/{identifier}", f"applicants/{APPLICANT}/assessments"):
                assert "SYNTHETIC-private-training-member" not in client.get("/api/v1/" + path).text
            from uuid import UUID
            stored = service.records.get(AssessmentSnapshot, UUID(identifier))
            assert stored.model_artifact.training_sample_ids == artifact.training_sample_ids
    finally:
        store.engine.dispose()


def test_public_evaluation_omits_private_lineage_and_preserves_journal(tmp_path):
    from agrogami.application import EvaluationRun
    from agrogami.calibration.core import Calibrator, validate_evaluation
    from agrogami.datasets import DatasetIdentity, RiskDataset

    def data(split):
        return RiskDataset(identity=DatasetIdentity(dataset_id="SYNTHETIC-private-experiment",
            target_definition="Invented software label", scope="synthetic", limitations=("Synthetic only",)),
            sample_ids=tuple(f"SYNTHETIC-private-{split}-{i}" for i in range(4)),
            feature_names=("external_inflow_total",), values=((1.0,), (2.0,), (3.0,), (4.0,)), labels=(0, 0, 1, 1))
    model = LogisticRiskModel.fit(data("training"), scope=ValidationScope.SYNTHETIC_DEMO, version="SYNTHETIC-v1")
    calibration_data = data("calibration")
    calibrator = Calibrator.fit([.1, .2, .8, .9], list(calibration_data.labels), list(calibration_data.sample_ids),
        model=model.artifact, data=calibration_data, dataset_id=calibration_data.identity.dataset_id, version="SYNTHETIC-cal")
    lineage = validate_evaluation(data("evaluation"), model.artifact, calibrator.artifact)
    report = EvaluationRun(dataset_id=lineage.dataset_id, scope=lineage.scope, metrics={},
        private_lineage=lineage, limitations=("Synthetic software test",))
    store = Store("sqlite:///" + str(tmp_path / "synthetic-report.db"))
    service = ApplicationService(store, tmp_path / "sources")
    try:
        service.records.save(report)
        with TestClient(create_app(service)) as client:
            response = client.get(f"/api/v1/evaluations/{report.run_id}")
            assert response.status_code == 200
            assert response.json()["private_lineage"] is None
            for split in ("training", "calibration", "evaluation"):
                assert f"SYNTHETIC-private-{split}-" not in response.text
        assert service.records.get(EvaluationRun, report.run_id) == report
    finally:
        store.engine.dispose()
