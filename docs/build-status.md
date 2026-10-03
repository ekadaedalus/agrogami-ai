# Build status ? local prototype completion

Starting checkpoint independently verified: Python 3.14.8 / Windows, **223 passed, 3 optional heavy tests deselected**. Current default suite: **251 passed, 3 deselected**. Original financial schemas/storage/reconciliation/features/fixtures were preserved. The original 107 foundation cases remain in the full green suite. No large models/datasets were downloaded.

## Implemented and tested

- Existing deterministic foundation and second-pass extraction/model/governance/backend services.
- Ten-page Streamlit UI using one HTTP client: overview, marked samples/image intake, candidate/provenance review, event ledger, three-window features, status/scope/null assessment, stored explanation/evaluation, immutable audit and docs.
- Reviewer-only candidate retrieval, explicit synthetic document marker, database readiness and synchronized allowlisted project /docs. Swagger remains /api/docs; OpenAPI /api/openapi.json.
- Separate official MCP SDK 1.30.0 Prism Streamable HTTP /mcp server: exactly four read-only tools, Bearer authentication, demo role reuse, restricted aggregate fairness, minimized payloads, explicit local host protection and sanitized SDK logging.
- tests/integration/test_local_product.py: **28 passing cases**, including all-page AppTest, full UI flow, client/service correction history, docs/scope/path privacy and actual four-tool HTTP protocol. Existing backend docs assertion changed from reserved 404 to implemented 200; no financial-core test was altered.
- Live API, Streamlit and Prism launched using isolated temporary SQLite storage; readiness/docs, synthetic review/correction/features/snapshots, official SDK initialize/list/read calls verified. Owned Windows process trees stopped and temporary storage cleanup passed.
- Editable install .[test,local,trees,fairness], exact dependency imports and pip check passed on Python 3.14.8. Streamlit 1.65.0, MCP 1.30.0, Markdown 3.11 installed from wheels.

## Containers and operations

Dockerfile, docker-compose.yml, .dockerignore, localhost-only publishing, nonroot runtime/shared private SQLite volume and API/UI healthchecks are implemented. Docker executable is unavailable: config/build/run NOT verified. Commands are in README; this is prepared local container support, not production deployment. Public deployment = PLANNED.

Smoke: python scripts/smoke_test.py uses a configured AGROGAMI_SMOKE_TOKEN and intentionally appends marked synthetic evidence. Full isolated verification: python -m scripts.verify_local_runtime. Windows helpers use relative paths and disable access logs/Streamlit usage telemetry. Readiness reports missing optional models without failing the deterministic demo.

## Privacy/security review

No raw evidence/phone numbers/private paths/tokens in ordinary UI/client/MCP logs. SDK diagnostics retain structured severity only; a regression verifies untrusted log text is removed. Candidate raw fields are intentional reviewer/admin views, not logs. Source API metadata is allowlisted; upload filenames are not accepted; object names are UUIDs. /docs reads only a fixed document allowlist and escapes embedded HTML. Private data/cache/.env/database/log/temp paths are ignored for Git/container context.

Local demo authorization remains dataset-wide, with tokenless API viewer access. No production identity, applicant isolation, encryption, rate limits, consent/retention/migrations or durable interrupted-snapshot recovery is claimed. Ledger correction and subsequent assessment journal are separate transactions.

## External blockers and remaining human actions

Real provider templates, consented financial annotations, trained DeBERTa/TrOCR/LayoutLMv3 checkpoints and mature linked repayment outcomes remain absent. Real predictive/calibration/fairness/latency claims remain blocked. Manual external Codex/Claude/Antigravity MCP reuse, final UI review, Docker-capable validation, production operations/security, explicitly authorized public deployment, video recording and proof links remain human/external tasks. No fake result/URL/proof was created.

## ANTIGRAVITY HANDOFF

Historical heading retained for foundation contract compatibility. The user superseded the previous coding-agent handoff: Codex completed the feasible local product pass. There is no pending UI/docs/Prism implementation handoff. Read docs/codex-handoff.md ? Codex Final Implementation Record for current status. Next stage is human review and operational/data/proof work, not regenerating the core.

## Exact run commands

```powershell
.\.venv\Scripts\python.exe -m uvicorn agrogami.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
.\.venv\Scripts\python.exe -m streamlit run src/agrogami/ui/app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
.\.venv\Scripts\python.exe -m agrogami.mcp.server
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.verify_local_runtime
```

Prism requires AGROGAMI_MCP_ENABLED=true and configured secret credentials. README contains clean-install/environment/Docker commands.
