"""Versioned local research API. No production authentication or deployment claim."""
import base64
import binascii
import csv
import io
import json
from typing import Annotated, Literal, TypeVar
from uuid import UUID
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import AwareDatetime, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from agrogami.schemas import Contract, Source, CanonicalEvent, CandidateExtraction, Coverage, FeatureSnapshot
from agrogami.config import Settings
from agrogami.authorization import Principal, Role, authenticate, can_access_applicant
from agrogami.storage import Store
from agrogami.application import ApplicationService, Job, EvaluationRun
from agrogami.assessment import AssessmentSnapshot
from agrogami.explainability.core import EvidenceReason, TreeExplanation
from agrogami import __version__
from agrogami.fairness.metrics import FairnessReport

Record = TypeVar("Record")


class HealthResponse(Contract):
    status: Literal["ok"] = "ok"
    mode: Literal["research"] = "research"
    version: str = __version__


class ExplanationResponse(Contract):
    reasons: tuple[EvidenceReason, ...]
    tree_shap: TreeExplanation | None
    limitations: tuple[str, ...]


class SMSRequest(Contract):
    applicant_id: UUID
    account_id: UUID | None = None
    text: str = Field(min_length=1, max_length=16000)
    provider: str = Field(min_length=1, max_length=80)


BULK_SMS_MAX_ROWS = 500
BULK_SMS_MAX_BYTES = 1_000_000
BULK_SMS_COLUMNS = {"applicant_id", "provider", "text"}


class BulkSMSRow(Contract):
    row: int
    status: Literal["COMPLETED", "NEEDS_REVIEW", "BLOCKED_MODEL_ARTIFACT", "REJECTED"]
    job_id: UUID | None = None
    reasons: tuple[str, ...] = ()


class BulkSMSResult(Contract):
    rows: tuple[BulkSMSRow, ...]
    submitted: int
    accepted: int
    needs_review: int
    rejected: int


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
    settings = Settings()
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if owned:
            model, calibrator, explanation_provider = None, None, None
            from agrogami.extraction.local_models import DebertaAdapter
            from agrogami.extraction.documents import TrOCRAdapter, LayoutLMv3Adapter
            deberta = DebertaAdapter.load(settings.deberta_checkpoint) if settings.deberta_checkpoint else None
            trocr = TrOCRAdapter.load(settings.trocr_checkpoint) if settings.trocr_checkpoint else None
            layout = LayoutLMv3Adapter.load(settings.layoutlmv3_checkpoint) if settings.layoutlmv3_checkpoint else None
            if settings.risk_model_path:
                from agrogami.risk.loading import load_risk_components
                model, calibrator, explanation_provider = load_risk_components(
                    settings.risk_model_path, settings.calibrator_path, settings.shap_background_path,
                    enable_real_models=settings.enable_real_models)
            app.state.service = ApplicationService(Store(settings.database_url), settings.private_data_dir,
                model=model, calibrator=calibrator, explanation_provider=explanation_provider,
                deberta=deberta, trocr=trocr, layout=layout)
        yield
        if owned:
            app.state.service.store.engine.dispose()
    app = FastAPI(title="Agrogami AI", version=__version__, docs_url="/api/docs",
                  summary="Traceable underwriting from financial records traditional credit systems ignore",
                  description=("An explainable underwriting evidence and risk-audit workbench for thin-file credit. "
                               "Assessment outputs are illustrative and are not lending decisions or validated "
                               "individual creditworthiness."),
                  openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan)
    app.state.service = service
    # Credentials and scope are server-owned; request role headers are never trusted.
    if tokens is None:
        configured = settings.demo_tokens
        tokens = {token: Role(role) for token, role in configured.items()}

    def role(x_agrogami_token: Annotated[str | None, Header()] = None) -> Principal:
        if x_agrogami_token is None and settings.local_demo_mode:
            return Principal(Role.viewer, authenticated=False, local_demo=True)
        principal = authenticate(x_agrogami_token, settings, tokens=tokens)
        if principal is None:
            raise HTTPException(401, "Valid credential required")
        return principal

    def reviewer(current: Annotated[Principal, Depends(role)]) -> Principal:
        if not current.can("review"):
            raise HTTPException(403, "Reviewer or admin role required")
        return current

    def reader(current: Annotated[Principal, Depends(role)]) -> Principal:
        return current

    def writer(current: Annotated[Principal, Depends(role)]) -> Principal:
        if not current.local_demo and not current.can("intake"):
            raise HTTPException(403, "Authorized write role required")
        return current

    def applicant_access(current: Principal, applicant_id: UUID, service: ApplicationService) -> None:
        if not can_access_applicant(current, applicant_id, service.store):
            raise HTTPException(403, "Applicant access denied")

    def source_access(current: Principal, source_id: UUID, service: ApplicationService) -> Source:
        record = found(service.store.get(Source, source_id))
        applicant_access(current, record.applicant_id, service)
        if not current.authenticated and not record.synthetic:
            raise HTTPException(403, "Credential required for private evidence")
        return record

    def intake_access(current: Principal, applicant_id: UUID, service: ApplicationService, *, synthetic: bool) -> None:
        applicant_access(current, applicant_id, service)
        if not synthetic and not current.can("intake"):
            raise HTTPException(403, "Authorized write role required for private evidence")

    def domain(request: Request) -> ApplicationService:
        return request.app.state.service

    def found(value: Record | None) -> Record:
        if value is None:
            raise HTTPException(404, "Record not found")
        return value

    def public_snapshot(record: AssessmentSnapshot) -> AssessmentSnapshot:
        """Keep private experiment membership in the immutable journal only."""
        if record.model_artifact is None:
            return record
        artifact = record.model_artifact.model_copy(update={"training_sample_ids": (), "training_lineage": None})
        return record.model_copy(update={"model_artifact": artifact})

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
    app.include_router(docs_router(settings.docs_dir))

    @app.get("/ready")
    def ready(service: Annotated[ApplicationService, Depends(domain)]) -> dict:
        from sqlalchemy import text
        with service.store.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "available", "optional_models": {
            "deberta": service.deberta is not None, "trocr": service.trocr is not None,
            "layoutlmv3": service.layout is not None, "risk": service.model is not None},
            "mcp_enabled": settings.mcp_enabled}

    @app.get("/api/v1/candidates/{candidate_id}", response_model=CandidateExtraction, dependencies=[Depends(reviewer)])
    def candidate(candidate_id: UUID, service: Annotated[ApplicationService, Depends(domain)],
                  current: Annotated[Principal, Depends(reviewer)]) -> CandidateExtraction:
        record = found(service.store.get(CandidateExtraction, candidate_id))
        source_access(current, record.source_id, service)
        return record

    @app.post("/api/v1/intake/sms", response_model=Job, dependencies=[Depends(writer)], status_code=201)
    def sms(payload: SMSRequest, service: Annotated[ApplicationService, Depends(domain)],
            current: Annotated[Principal, Depends(writer)]) -> Job:
        intake_access(current, payload.applicant_id, service, synthetic=payload.text.startswith("SYNTHETIC:"))
        return service.sms_intake(**payload.model_dump())

    @app.post("/api/v1/intake/sms/bulk", response_model=BulkSMSResult, dependencies=[Depends(reviewer)], status_code=201,
              openapi_extra={"requestBody": {"required": True, "content": {"text/csv": {"schema": {"type": "string"}}}}})
    async def sms_bulk(request: Request, service: Annotated[ApplicationService, Depends(domain)],
                       current: Annotated[Principal, Depends(reviewer)]) -> BulkSMSResult:
        # One CSV row per SMS; each row runs the same intake/parse/validation as single intake.
        # Synthetic rows only: real bulk import needs a consent workflow that does not exist yet.
        if request.headers.get("content-type", "").split(";")[0].strip() != "text/csv":
            raise HTTPException(415, "Content-Type must be text/csv")
        if int(request.headers.get("content-length") or 0) > BULK_SMS_MAX_BYTES:
            raise HTTPException(413, "CSV exceeds 1 MB")
        body = await request.body()
        if len(body) > BULK_SMS_MAX_BYTES:
            raise HTTPException(413, "CSV exceeds 1 MB")
        try:
            reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
            columns = set(reader.fieldnames or ())
            if not BULK_SMS_COLUMNS <= columns or not columns <= BULK_SMS_COLUMNS | {"account_id"}:
                raise HTTPException(422, "CSV header must be applicant_id,provider,text (optional account_id)")
            records = list(reader)
        except (UnicodeDecodeError, csv.Error):
            raise HTTPException(422, "CSV must be valid UTF-8")
        if not records:
            raise HTTPException(422, "CSV has no rows")
        if len(records) > BULK_SMS_MAX_ROWS:
            raise HTTPException(413, f"CSV exceeds {BULK_SMS_MAX_ROWS} rows")

        def process() -> BulkSMSResult:
            results = []
            for number, record in enumerate(records, start=2):  # row 1 is the header
                try:
                    item = SMSRequest(applicant_id=record.get("applicant_id"), provider=record.get("provider"),
                                      text=record.get("text"), account_id=record.get("account_id") or None)
                except ValidationError:
                    results.append(BulkSMSRow(row=number, status="REJECTED", reasons=("INVALID_ROW",)))
                    continue
                if not item.text.startswith("SYNTHETIC:"):
                    results.append(BulkSMSRow(row=number, status="REJECTED", reasons=("NON_SYNTHETIC_ROW",)))
                    continue
                if not can_access_applicant(current, item.applicant_id, service.store):
                    results.append(BulkSMSRow(row=number, status="REJECTED", reasons=("APPLICANT_ACCESS_DENIED",)))
                    continue
                job = service.sms_intake(**item.model_dump())
                results.append(BulkSMSRow(row=number, status=job.status, job_id=job.job_id, reasons=job.reasons))
            return BulkSMSResult(rows=tuple(results), submitted=len(results),
                                 accepted=sum(r.status == "COMPLETED" for r in results),
                                 needs_review=sum(r.status == "NEEDS_REVIEW" for r in results),
                                 rejected=sum(r.status == "REJECTED" for r in results))
        return await run_in_threadpool(process)

    @app.post("/api/v1/intake/document", response_model=Job, dependencies=[Depends(writer)], status_code=201)
    def document(payload: DocumentRequest, service: Annotated[ApplicationService, Depends(domain)],
                 current: Annotated[Principal, Depends(writer)]) -> Job:
        intake_access(current, payload.applicant_id, service, synthetic=payload.synthetic)
        try:
            content = base64.b64decode(payload.content_base64, validate=True)
        except binascii.Error:
            raise HTTPException(422, "Invalid base64 image")
        return service.document_intake(applicant_id=payload.applicant_id, content=content,
                                      orientation=payload.orientation, deskew_degrees=payload.deskew_degrees, synthetic=payload.synthetic)

    @app.get("/api/v1/jobs/{job_id}", response_model=Job, dependencies=[Depends(reader)])
    def job(job_id: UUID, service: Annotated[ApplicationService, Depends(domain)],
            current: Annotated[Principal, Depends(reader)]) -> Job:
        record = found(service.records.get(Job, job_id))
        source_access(current, record.source_id, service)
        return record

    @app.get("/api/v1/sources/{source_id}", response_model=Source, dependencies=[Depends(reader)])
    def source(source_id: UUID, service: Annotated[ApplicationService, Depends(domain)],
               current: Annotated[Principal, Depends(reader)]) -> Source:
        record = source_access(current, source_id, service)
        safe_metadata = {k: v for k, v in record.metadata.items() if k in {"width", "height", "preprocess_version", "label"}}
        return Source.model_validate(record.model_dump() | {"metadata": safe_metadata})

    @app.get("/api/v1/applicants/{applicant_id}/events", response_model=list[CanonicalEvent], dependencies=[Depends(reader)])
    def events(applicant_id: UUID, service: Annotated[ApplicationService, Depends(domain)],
               current: Annotated[Principal, Depends(reader)]) -> list[CanonicalEvent]:
        applicant_access(current, applicant_id, service)
        return service.store.events(applicant_id)

    @app.post("/api/v1/events/{event_id}/review", response_model=CanonicalEvent, dependencies=[Depends(reviewer)])
    def review(event_id: UUID, payload: ReviewRequest, service: Annotated[ApplicationService, Depends(domain)],
               current: Annotated[Principal, Depends(reviewer)]) -> CanonicalEvent:
        applicant_access(current, found(service.store.get(CanonicalEvent, event_id)).applicant_id, service)
        return service.review(event_id, payload.changes, payload.reason, payload.reviewer_alias)

    @app.get("/api/v1/applicants/{applicant_id}/features", response_model=dict[int, FeatureSnapshot], dependencies=[Depends(reader)])
    def features(applicant_id: UUID, scoring_time: AwareDatetime, service: Annotated[ApplicationService, Depends(domain)],
                 current: Annotated[Principal, Depends(reader)],
                 coverage_json: str | None = Query(default=None, max_length=50000)) -> dict[int, FeatureSnapshot]:
        applicant_access(current, applicant_id, service)
        if coverage_json:
            coverage = Coverage.model_validate_json(coverage_json)
        else:
            from datetime import timedelta
            coverage = Coverage(applicant_id=applicant_id, known_at=scoring_time - timedelta(microseconds=1),
                                reasons=("no_verified_coverage_supplied",))
        return service.features(applicant_id, scoring_time, coverage)

    @app.get("/api/v1/applicants/{applicant_id}/feature-snapshots", response_model=list[FeatureSnapshot], dependencies=[Depends(reader)])
    def stored_snapshots(applicant_id: UUID, service: Annotated[ApplicationService, Depends(domain)],
                         current: Annotated[Principal, Depends(reader)]) -> list[FeatureSnapshot]:
        """Stored snapshots keep the scoring time and attested coverage they were computed with."""
        applicant_access(current, applicant_id, service)
        return service.store.snapshots(applicant_id)

    @app.post("/api/v1/candidates/{candidate_id}/review", response_model=CanonicalEvent, dependencies=[Depends(reviewer)], status_code=201)
    def candidate_review(candidate_id: UUID, payload: CandidateReviewRequest,
                         service: Annotated[ApplicationService, Depends(domain)],
                         current: Annotated[Principal, Depends(reviewer)]) -> CanonicalEvent:
        candidate = found(service.store.get(CandidateExtraction, candidate_id))
        source_access(current, candidate.source_id, service)
        applicant_access(current, payload.event.applicant_id, service)
        return service.accept_candidate(candidate_id, payload.event, payload.reason, payload.reviewer_alias)

    @app.post("/api/v1/assessments", response_model=AssessmentSnapshot, dependencies=[Depends(reviewer)], status_code=201)
    def assessment(payload: AssessmentRequest, service: Annotated[ApplicationService, Depends(domain)],
                   current: Annotated[Principal, Depends(reviewer)]) -> AssessmentSnapshot:
        applicant_access(current, payload.applicant_id, service)
        return public_snapshot(service.assessment(applicant_id=payload.applicant_id, t0=payload.assessment_time, coverage=payload.coverage,
                                  window_days=payload.window_days, previous_id=payload.supersedes_assessment_id))

    @app.get("/api/v1/assessments/{assessment_id}", response_model=AssessmentSnapshot, dependencies=[Depends(reader)])
    def get_assessment(assessment_id: UUID, service: Annotated[ApplicationService, Depends(domain)],
                       current: Annotated[Principal, Depends(reader)]) -> AssessmentSnapshot:
        record = found(service.records.get(AssessmentSnapshot, assessment_id))
        applicant_access(current, record.applicant_id, service)
        return public_snapshot(record)

    @app.get("/api/v1/applicants/{applicant_id}/assessments", response_model=list[AssessmentSnapshot], dependencies=[Depends(reader)])
    def assessment_history(applicant_id: UUID, service: Annotated[ApplicationService, Depends(domain)],
                           current: Annotated[Principal, Depends(reader)]) -> list[AssessmentSnapshot]:
        applicant_access(current, applicant_id, service)
        return [public_snapshot(record) for record in service.records.assessments(applicant_id)]

    @app.get("/api/v1/assessments/{assessment_id}/explanation", response_model=ExplanationResponse, dependencies=[Depends(reader)])
    def explanation(assessment_id: UUID, service: Annotated[ApplicationService, Depends(domain)],
                    current: Annotated[Principal, Depends(reader)]) -> ExplanationResponse:
        record = found(service.records.get(AssessmentSnapshot, assessment_id))
        applicant_access(current, record.applicant_id, service)
        return ExplanationResponse(reasons=record.reasons, tree_shap=record.explanation_metadata, limitations=record.limitations)

    @app.get("/api/v1/evaluations/{run_id}", response_model=EvaluationRun, dependencies=[Depends(reader)])
    def evaluation(run_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> EvaluationRun:
        record = found(service.records.get(EvaluationRun, run_id))
        return EvaluationRun.model_validate(record.model_dump() | {"fairness": None, "private_lineage": None})

    @app.get("/api/v1/evaluations/{run_id}/fairness", response_model=FairnessReport, dependencies=[Depends(reviewer)])
    def fairness(run_id: UUID, service: Annotated[ApplicationService, Depends(domain)]) -> FairnessReport:
        return found(found(service.records.get(EvaluationRun, run_id)).fairness)
    return app


app = create_app()
