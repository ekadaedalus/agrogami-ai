"""Agrogami Prism: four read-only tools over the existing application service."""
import hmac
import json
import logging
from contextlib import asynccontextmanager
from uuid import UUID
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from agrogami.application import ApplicationService, EvaluationRun
from agrogami.assessment import AssessmentSnapshot
from agrogami.config import Settings
from agrogami.schemas import ValidationStatus
from agrogami.storage import Store

class SafeSDKLog(logging.Filter):
    """SDK diagnostics may contain untrusted request text; retain severity only."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = json.dumps({"operation": "mcp_protocol", "status": record.levelname.lower()})
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True

class Gateway:
    def __init__(self, service: ApplicationService):
        self.service = service

    def ledger(self, applicant_id: UUID) -> dict:
        events = self.service.store.events(applicant_id)
        fields = {"event_id", "event_timestamp", "source_id", "source_type", "transaction_type", "direction",
                  "amount", "fee", "currency", "balance", "validation_status", "review_reason", "schema_version",
                  "created_at", "supersedes_event_id", "duplicate_of_event_id", "reversal_of_event_id", "source_provenance"}
        return {"events": [e.model_dump(mode="json", include=fields) for e in events
                           if e.validation_status == ValidationStatus.ACCEPTED], "scope": "research/demo"}

    def snapshot(self, assessment_id: UUID) -> dict:
        record = self.service.records.get(AssessmentSnapshot, assessment_id)
        if record is None:
            raise ValueError("Record not found")
        fields = {"assessment_id", "assessment_time", "status", "evidence_version_ids", "feature_schema_version",
                  "model_artifact", "model_validation_scope", "raw_probability", "calibrated_probability",
                  "unclipped_display_score", "display_score", "calibrator_version", "limitations", "created_at",
                  "supersedes_assessment_id"}
        result = record.model_dump(mode="json", include=fields)
        if record.model_artifact:
            result["model_artifact"] = record.model_artifact.model_dump(mode="json", include={
                "artifact_id", "version", "algorithm", "scope", "dataset_id", "target_definition", "feature_names", "feature_schema_version"})
        result["evidence_coverage"] = {name: value.model_dump(mode="json") for name, value in
            record.feature_snapshot.features.items() if name in {"coverage_days", "observed_day_share", "balance_coverage", "obligation_coverage"}}
        return result

    def explanation(self, assessment_id: UUID) -> dict:
        record = self.service.records.get(AssessmentSnapshot, assessment_id)
        if record is None:
            raise ValueError("Record not found")
        return {"reasons": [r.model_dump(mode="json") for r in record.reasons],
                "tree_shap": record.explanation_metadata.model_dump(mode="json") if record.explanation_metadata else None,
                "limitations": record.limitations}

    def fairness(self, run_id: UUID) -> dict:
        record = self.service.records.get(EvaluationRun, run_id)
        if record is None or record.fairness is None:
            raise ValueError("Aggregate fairness artifact unavailable")
        return {"run_id": str(record.run_id), "scope": record.scope.value, "dataset_id": record.dataset_id,
                "fairness": record.fairness.model_dump(mode="json"), "limitations": record.limitations}

def credential_role(headers, settings: Settings) -> str | None:
    authorization = headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    supplied = authorization[7:]
    for token, role in settings.demo_tokens.items():
        if hmac.compare_digest(supplied.encode(), token.encode()):
            return role
    if settings.mcp_auth_token and hmac.compare_digest(supplied.encode(), settings.mcp_auth_token.encode()):
        return "viewer"
    return None

class AuthorizedApp:
    """Pure ASGI boundary; authentication precedes MCP protocol parsing."""
    def __init__(self, app, settings: Settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from starlette.datastructures import Headers
            if credential_role(Headers(scope=scope), self.settings) is None:
                await JSONResponse({"detail": "Prism credential required"}, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)

def create_prism(service: ApplicationService | None = None, settings: Settings | None = None):
    settings = settings or Settings()
    if not settings.mcp_enabled:
        raise ValueError("Prism disabled; explicitly enable local MCP")
    if not settings.mcp_auth_token and not settings.demo_tokens:
        raise ValueError("Prism requires configured credentials")
    owned = service is None
    @asynccontextmanager
    async def lifespan(server):
        nonlocal service
        if owned:
            service = ApplicationService(Store(settings.database_url), settings.private_data_dir)
        try:
            yield {}
        finally:
            if owned:
                service.store.engine.dispose()

    server = FastMCP("Agrogami Prism", instructions="Read-only research inspection. No lending decisions.",
        host=settings.mcp_host, port=settings.mcp_port, stateless_http=True, json_response=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*"], allowed_origins=["http://127.0.0.1:*", "http://localhost:*"]),
        log_level="ERROR", lifespan=lifespan)

    def read(operation, identifier):
        try:
            return getattr(Gateway(service), operation)(identifier)
        except ValueError:
            raise ValueError("Requested research record unavailable") from None
        except Exception:
            raise ValueError("Research storage unavailable") from None

    @server.tool()
    def get_evidence_ledger(applicant_id: UUID) -> dict:
        """Read accepted canonical event versions and minimized provenance."""
        return read("ledger", applicant_id)

    @server.tool()
    def get_assessment_snapshot(assessment_id: UUID) -> dict:
        """Read an immutable research snapshot, preserving null scores and scope."""
        return read("snapshot", assessment_id)

    @server.tool()
    def get_explanation_factors(assessment_id: UUID) -> dict:
        """Read stored reasons/TreeSHAP; never recompute model explanations."""
        return read("explanation", assessment_id)

    @server.tool()
    def get_fairness_audit(run_id: UUID, ctx: Context) -> dict:
        """Read aggregate fairness only for reviewer/admin credentials."""
        request = ctx.request_context.request
        if request is None or credential_role(request.headers, settings) not in {"reviewer", "admin"}:
            raise ValueError("Reviewer/admin role required")
        return read("fairness", run_id)

    application = server.streamable_http_app()
    for name, logger in logging.Logger.manager.loggerDict.copy().items():
        if name.startswith("mcp.") and isinstance(logger, logging.Logger):
            if not any(isinstance(f, SafeSDKLog) for f in logger.filters):
                logger.addFilter(SafeSDKLog())
    return server, AuthorizedApp(application, settings)

def main() -> None:
    import uvicorn
    settings = Settings()
    _, application = create_prism(settings=settings)
    uvicorn.run(application, host=settings.mcp_host, port=settings.mcp_port, access_log=False, log_level="warning")

if __name__ == "__main__":
    main()
