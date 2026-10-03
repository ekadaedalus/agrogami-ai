"""Versioned local research API. No production authentication or deployment claim."""
import base64
import binascii
import hmac
import json
from enum import StrEnum
from typing import Annotated, Literal, TypeVar
from uuid import UUID
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, Field
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from agrogami.schemas import Contract, Source, CanonicalEvent, CandidateExtraction, Coverage, FeatureSnapshot
from agrogami.config import Settings
from agrogami.storage import Store
from agrogami.application import ApplicationService, Job, EvaluationRun
from agrogami.assessment import AssessmentSnapshot
from agrogami.explainability.core import EvidenceReason, TreeExplanation
from agrogami.fairness.metrics import FairnessReport

Record = TypeVar("Record")


class HealthResponse(Contract):
    status: Literal["ok"] = "ok"
    mode: Literal["research"] = "research"
    version: str = "0.2.0"


class ExplanationResponse(Contract):
    reasons: tuple[EvidenceReason, ...]
    tree_shap: TreeExplanation | None
    limitations: tuple[str, ...]


class Role(StrEnum):
    viewer = "viewer"
    reviewer = "reviewer"
    admin = "admin"


class SMSRequest(Contract):
    applicant_id: UUID
    account_id: UUID | None = None
    text: str = Field(min_length=1, max_length=16000)
    provider: str = Field(min_length=1, max_length=80)


class DocumentRequest(Contract):
    applicant_id: UUID
    content_base64: str = Field(min_length=1, max_length=14_000_000)
    orientation: int = 0
    deskew_degrees: float | None = None
    synthetic: bool = False


class ReviewRequest(Contract):
    changes: dict[str, object]
    reason: str = Field(min_length=1, max_length=1000)
    reviewer_alias: str = Field(pattern=r"^reviewer-[A-Za-z0-9_-]+$")


class AssessmentRequest(Contract):
    applicant_id: UUID
    assessment_time: AwareDatetime
    coverage: Coverage
    window_days: int = 30
    supersedes_assessment_id: UUID | None = None


class CandidateReviewRequest(Contract):
    event: CanonicalEvent
    reason: str = Field(min_length=1, max_length=1000)
    reviewer_alias: str = Field(pattern=r"^reviewer-[A-Za-z0-9_-]+$")


def create_app(service: ApplicationService | None = None, *, tokens: dict[str, Role] | None = None) -> FastAPI:
    owned = service is None
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if owned:
            settings = Settings()
            model, calibrator, explanation_provider = None, None, None
            from agrogami.extraction.local_models import DebertaAdapter
            from agrogami.extraction.documents import TrOCRAdapter, LayoutLMv3Adapter
            deberta = DebertaAdapter.load(settings.deberta_checkpoint) if settings.deberta_checkpoint else None
            trocr = TrOCRAdapter.load(settings.trocr_checkpoint) if settings.trocr_checkpoint else None
            layout = LayoutLMv3Adapter.load(settings.layoutlmv3_checkpoint) if settings.layoutlmv3_checkpoint else None
            if settings.risk_model_path:
                from agrogami.risk.models import LogisticRiskModel, TreeRiskModel, ValidationScope
                from agrogami.calibration.core import Calibrator
                model = (TreeRiskModel.load(settings.risk_model_path) if settings.risk_model_path.is_dir()
                         else LogisticRiskModel.load(settings.risk_model_path))
                if model.artifact.scope != ValidationScope.SYNTHETIC_DEMO and not settings.enable_real_models:
                    raise RuntimeError("Non-synthetic local artifacts require explicit research mode")
                calibrator = Calibrator.load(settings.calibrator_path)
                if settings.shap_background_path:
                    from agrogami.explainability.core import explain_tree
                    if not isinstance(model, TreeRiskModel):
                        raise RuntimeError("TreeSHAP background requires a supported tree model")
                    background = json.loads(settings.shap_background_path.read_text(encoding="utf-8"))
                    explanation_provider = lambda features: explain_tree(model, features, background=background["rows"],
                        background_identity=background["identity"], feature_definitions=background["feature_definitions"])
            app.state.service = ApplicationService(Store(settings.database_url), settings.private_data_dir,
                model=model, calibrator=calibrator, explanation_provider=explanation_provider,
                deberta=deberta, trocr=trocr, layout=layout)
        yield
        if owned:
            app.state.service.store.engine.dispose()
    app = FastAPI(title="Agrogami research backend", version="0.2.0", docs_url="/api/docs",
                  openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan)
    app.state.service = service
    # Map secrets to roles. Empty map permits viewer reads only; it never trusts role headers.
    if tokens is None:
        configured = Settings().demo_tokens
        tokens = {token: Role(role) for token, role in configured.items()}

    def role(x_agrogami_token: Annotated[str | None, Header()] = None) -> Role:
        if x_agrogami_token is None:
            return Role.viewer
        for token, granted in tokens.items():
            if hmac.compare_digest(x_agrogami_token, token):
                return granted
        raise HTTPException(401, "Invalid demo credential")

    def reviewer(current: Annotated[Role, Depends(role)]) -> Role:
        if current not in {Role.reviewer, Role.admin}:
            raise HTTPException(403, "Reviewer or admin role required")
        return current

    def reader(current: Annotated[Role, Depends(role)]) -> Role:
        return current

    def domain(request: Request) -> ApplicationService:
        return request.app.state.service

    def found(value: Record | None) -> Record:
        if value is None:
            raise HTTPException(404, "Record not found")
        return value

    @app.exception_handler(RequestValidationError)
    async def request_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": "Invalid request contract"})

    @app.exception_handler(ValueError)
    async def domain_error(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": "Request rejected by domain validation"})

    @app.exception_handler(IntegrityError)
    async def persistence_conflict(request: Request, exc: IntegrityError):
        return JSONResponse(status_code=409, content={"detail": "Immutable record conflict"})

    @app.exception_handler(SQLAlchemyError)
    async def persistence_error(request: Request, exc: SQLAlchemyError):
        return JSONResponse(status_code=503, content={"detail": "Evidence storage unavailable"})

    @app.exception_handler(OSError)
    async def filesystem_error(request: Request, exc: OSError):
        return JSONResponse(status_code=503, content={"detail": "Private storage unavailable"})

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    from agrogami.api.project_docs import router as docs_router
    app.include_router(docs_router(Settings().docs_dir))

    @app.get("/ready")
    def ready(service: Annotated[ApplicationService, Depends(domain)]) -> dict:
        from sqlalchemy import text
        with service.store.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "available", "optional_models": {
            "deberta": service.deberta is not None, "trocr": service.trocr is not None,
            "layoutlmv3": service.layout is not None, "risk": service.model is not None},
            "mcp_enabled": Settings().mcp_enabled}

    @app.get("/api/v1/candidates/{candidate_id}", response_model=CandidateExtraction, dependencies=[Depends(reviewer)])
    def candidate(candidate_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> CandidateExtraction:
        return found(service.store.get(CandidateExtraction, candidate_id))

    @app.post("/api/v1/intake/sms", response_model=Job, dependencies=[Depends(reader)], status_code=201)
    def sms(payload: SMSRequest, service: Annotated[ApplicationService, Depends(domain)]) -> Job:
        return service.sms_intake(**payload.model_dump())

    @app.post("/api/v1/intake/document", response_model=Job, dependencies=[Depends(reader)], status_code=201)
    def document(payload: DocumentRequest, service: Annotated[ApplicationService, Depends(domain)]) -> Job:
        try:
            content = base64.b64decode(payload.content_base64, validate=True)
        except binascii.Error:
            raise HTTPException(422, "Invalid base64 image")
        return service.document_intake(applicant_id=payload.applicant_id, content=content,
                                      orientation=payload.orientation, deskew_degrees=payload.deskew_degrees, synthetic=payload.synthetic)

    @app.get("/api/v1/jobs/{job_id}", response_model=Job, dependencies=[Depends(reader)])
    def job(job_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> Job:
        return found(service.records.get(Job, job_id))

    @app.get("/api/v1/sources/{source_id}", response_model=Source, dependencies=[Depends(reader)])
    def source(source_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> Source:
        record = found(service.store.get(Source, source_id))
        safe_metadata = {k: v for k, v in record.metadata.items() if k in {"width", "height", "preprocess_version", "label"}}
        return Source.model_validate(record.model_dump() | {"metadata": safe_metadata})

    @app.get("/api/v1/applicants/{applicant_id}/events", response_model=list[CanonicalEvent], dependencies=[Depends(reader)])
    def events(applicant_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> list[CanonicalEvent]:
        return service.store.events(applicant_id)

    @app.post("/api/v1/events/{event_id}/review", response_model=CanonicalEvent, dependencies=[Depends(reviewer)])
    def review(event_id: UUID, payload: ReviewRequest, service: Annotated[ApplicationService, Depends(domain)]) -> CanonicalEvent:
        found(service.store.get(CanonicalEvent, event_id))
        return service.review(event_id, payload.changes, payload.reason, payload.reviewer_alias)

    @app.get("/api/v1/applicants/{applicant_id}/features", response_model=dict[int, FeatureSnapshot], dependencies=[Depends(reader)])
    def features(applicant_id: UUID, scoring_time: AwareDatetime, service: Annotated[ApplicationService, Depends(domain)],
                 coverage_json: str | None = Query(default=None, max_length=50000)) -> dict[int, FeatureSnapshot]:
        if coverage_json:
            coverage = Coverage.model_validate_json(coverage_json)
        else:
            from datetime import timedelta
            coverage = Coverage(applicant_id=applicant_id, known_at=scoring_time - timedelta(microseconds=1),
                                reasons=("no_verified_coverage_supplied",))
        return service.features(applicant_id, scoring_time, coverage)

    @app.post("/api/v1/candidates/{candidate_id}/review", response_model=CanonicalEvent, dependencies=[Depends(reviewer)], status_code=201)
    def candidate_review(candidate_id: UUID, payload: CandidateReviewRequest,
                         service: Annotated[ApplicationService, Depends(domain)]) -> CanonicalEvent:
        return service.accept_candidate(candidate_id, payload.event, payload.reason, payload.reviewer_alias)

    @app.post("/api/v1/assessments", response_model=AssessmentSnapshot, dependencies=[Depends(reviewer)], status_code=201)
    def assessment(payload: AssessmentRequest, service: Annotated[ApplicationService, Depends(domain)]) -> AssessmentSnapshot:
        return service.assessment(applicant_id=payload.applicant_id, t0=payload.assessment_time, coverage=payload.coverage,
                                  window_days=payload.window_days, previous_id=payload.supersedes_assessment_id)

    @app.get("/api/v1/assessments/{assessment_id}", response_model=AssessmentSnapshot, dependencies=[Depends(reader)])
    def get_assessment(assessment_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> AssessmentSnapshot:
        return found(service.records.get(AssessmentSnapshot, assessment_id))

    @app.get("/api/v1/applicants/{applicant_id}/assessments", response_model=list[AssessmentSnapshot], dependencies=[Depends(reader)])
    def assessment_history(applicant_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> list[AssessmentSnapshot]:
        return service.records.assessments(applicant_id)

    @app.get("/api/v1/assessments/{assessment_id}/explanation", response_model=ExplanationResponse, dependencies=[Depends(reader)])
    def explanation(assessment_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> ExplanationResponse:
        record = found(service.records.get(AssessmentSnapshot, assessment_id))
        return ExplanationResponse(reasons=record.reasons, tree_shap=record.explanation_metadata, limitations=record.limitations)

    @app.get("/api/v1/evaluations/{run_id}", response_model=EvaluationRun, dependencies=[Depends(reader)])
    def evaluation(run_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> EvaluationRun:
        record = found(service.records.get(EvaluationRun, run_id))
        return EvaluationRun.model_validate(record.model_dump() | {"fairness": None})

    @app.get("/api/v1/evaluations/{run_id}/fairness", response_model=FairnessReport, dependencies=[Depends(reviewer)])
    def fairness(run_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> FairnessReport:
        return found(found(service.records.get(EvaluationRun, run_id)).fairness)
    return app


app = create_app()
