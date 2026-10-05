# Agrogami AI API

Traceable underwriting from financial records traditional credit systems ignore

An explainable underwriting evidence and risk-audit workbench for thin-file credit.

Run from repository root on Python 3.14.8:

```powershell
.\.venv\Scripts\python.exe -m uvicorn agrogami.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

The server provides the local evidence and risk-audit workflow. Assessment outputs are illustrative and are not lending decisions or validated individual creditworthiness. Swagger: `/api/docs`; OpenAPI: `/api/openapi.json`; `/docs` renders allowlisted synchronized repository documentation. Streamlit and read-only Prism are implemented; container artifacts exist but Docker execution is unverified. No public deployment exists. Product branding changes do not change route contracts, authorization headers or the existing health-mode value.

| Route | Contract / authorization |
|---|---|
| GET /health | Public safe version/mode |
| GET /ready | Database availability and optional artifact presence; no private paths |
| GET /docs | Allowlisted rendered project documentation; no user-selected file paths |
| GET /api/v1/candidates/{candidate_id} | Reviewer/admin; original candidate fields and provenance for intentional review |
| POST /api/v1/intake/sms | SMSRequest; viewer; synchronous immutable job/source/candidates and optional pending event |
| POST /api/v1/intake/document | DocumentRequest with base64 raster bytes and explicit synthetic marker; viewer; preprocessing and optional local extraction candidates; no upload filename/path accepted |
| GET /api/v1/jobs/{job_id} | Viewer; intake outcome/reasons/UUIDs, not an asynchronous queue |
| GET /api/v1/sources/{source_id} | Viewer; safe source metadata, no object path/raw bytes |
| GET /api/v1/applicants/{applicant_id}/events | Viewer; canonical ledger versions |
| POST /api/v1/events/{event_id}/review | Reviewer/admin; typed changes/reason/demo-safe alias; append correction |
| POST /api/v1/candidates/{candidate_id}/review | Reviewer/admin; explicit CanonicalEvent/reason/alias; deterministic validation and immutable acceptance audit |
| GET /api/v1/applicants/{applicant_id}/features | Viewer; aware scoring_time; optional coverage_json attestation; all three core windows |
| POST /api/v1/assessments | Reviewer/admin; applicant/time/coverage/window and optional predecessor |
| GET /api/v1/assessments/{assessment_id} | Viewer; complete immutable snapshot and limitations |
| GET /api/v1/applicants/{applicant_id}/assessments | Viewer; assessment history including automatic unscored correction snapshots |
| GET /api/v1/assessments/{assessment_id}/explanation | Viewer; controlled evidence reasons and configured TreeSHAP metadata or null |
| GET /api/v1/evaluations/{run_id} | Viewer; actual persisted local aggregate metrics, fairness redacted |
| GET /api/v1/evaluations/{run_id}/fairness | Reviewer/admin; actual offline aggregate group report |

Set `AGROGAMI_DEMO_TOKENS` in ignored `.env` to a JSON map of secret token to viewer/reviewer/admin. Supply `X-Agrogami-Token`. No token is viewer; invalid token is 401; privileged operation without reviewer/admin is 403. Role headers grant nothing. This is not production identity, per-applicant authorization or tenant isolation.

Default application has no risk model, calibrator or extraction checkpoints. Document jobs record BLOCKED_MODEL_ARTIFACT; SMS template matches require explicit ownership review. Unsupported/missing-time candidates require manual canonical facts via candidate review, never inferred ingestion dates. Job records preserve intake outcomes; later review is represented by accepted event/correction lineage rather than rewriting jobs.

Feature GET without a coverage attestation uses explicit unknown coverage, never assumes full statements. Assessment POST requires a supplied attestation, known before scoring. Unknown evidence returns INSUFFICIENT_EVIDENCE or NEEDS_REVIEW with null probabilities/scores. A matching local model/calibrator may support research computation; synthetic results are ILLUSTRATIVE and public benchmark borrower scoring is withheld. READY is not VALIDATED or a loan decision.

Each application/API event correction automatically appends a NEEDS_REVIEW assessment snapshot with explicit unknown fresh coverage and null probabilities/scores. Earlier snapshots remain immutable and the new snapshot links its predecessor when present. Fetch applicant assessment history to find it, then explicitly reassess with verified fresh coverage. Ledger correction and assessment-journal appends use separate transactions; recovery after an interrupted second append is operational work, not an implemented production retry system.

Local numerical artifact paths, SHAP background and extraction checkpoint settings are documented in .env.example and codex-handoff.md. Extraction requires explicit non-demo research mode and local manifests. Output candidates remain reviewed/normalized separately. No API payload can provide a model checkpoint, arbitrary filesystem path or protected attribute vector.

Validation errors are sanitized (422), unknown records 404, immutable conflicts 409 and storage outages 503. Source metadata is allowlisted. The local server command disables request access logs. A production service needs authenticated applicant authorization, transport security, limits, retention/consent policies and deployment verification before real financial use.
