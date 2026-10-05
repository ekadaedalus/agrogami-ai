# Build status — local workbench completion

Starting checkpoint independently verified: Python 3.14.8 / Windows, **223 passed, 3 optional heavy tests deselected**. Previous local-completion suite: **251 passed, 3 deselected**. Historical pre-remediation suite, 2026-10-05: **253 passed, 3 deselected**. **Current (final freeze pass): 460 passed, 3 deselected** — see the final freeze section below. Original financial schemas/storage/reconciliation/features/fixtures were preserved. The original 107 foundation cases remain in the full green suite. No large models/datasets were downloaded.

## Implemented and tested

- Existing deterministic foundation and second-pass extraction/model/governance/backend services.
- Ten-page Streamlit UI using one HTTP client: overview, marked samples/image intake, candidate/provenance review, event ledger, three-window features, status/scope/null assessment, stored explanation/evaluation, immutable audit and docs.
- Reviewer-only candidate retrieval, explicit synthetic document marker, database readiness and synchronized allowlisted project /docs. Swagger remains /api/docs; OpenAPI /api/openapi.json.
- Separate official MCP SDK 1.30.0 Prism Streamable HTTP /mcp server: exactly four read-only tools, Bearer authentication, demo role reuse, restricted aggregate fairness, minimized payloads, explicit local host protection and sanitized SDK logging.
- tests/integration/test_local_product.py: **30 passing cases**, including all-page AppTest, full UI flow, presentation/drill-down and balance-history regressions, client/service correction history, docs/scope/path privacy and actual four-tool HTTP protocol. The earlier local-completion run had 28 cases. Existing backend docs assertion changed from reserved 404 to implemented 200 in that pass; no financial-core test was altered.
- Live API, Streamlit and Prism launched using isolated temporary SQLite storage; readiness/docs, synthetic review/correction/features/snapshots, official SDK initialize/list/read calls verified. Owned Windows process trees stopped and temporary storage cleanup passed.
- Editable install .[test,local,trees,fairness], exact dependency imports and pip check passed on Python 3.14.8. Streamlit 1.65.0, MCP 1.30.0, Markdown 3.11 installed from wheels.

## Containers and operations

Dockerfile, docker-compose.yml, .dockerignore, localhost-only publishing, nonroot runtime/shared private SQLite volume and API/UI healthchecks are implemented. Docker executable is unavailable: config/build/run NOT verified. Commands are in README; this is prepared local container support, not production deployment. Public deployment = PLANNED.

Smoke: python scripts/smoke_test.py uses a configured AGROGAMI_SMOKE_TOKEN and intentionally appends marked synthetic evidence. Full isolated verification: python -m scripts.verify_local_runtime. Windows helpers use relative paths and disable access logs/Streamlit usage telemetry. Readiness reports missing optional models without failing the deterministic demo.

## Presentation pass — 2026-10-04

Agrogami AI now leads the Streamlit UI, API metadata, README and project /docs, with the tagline “Traceable underwriting from financial records traditional credit systems ignore.” The Demo environment notice remains visible below the headline. API URL, Demo credential and Applicant UUID are in collapsed Developer settings. Human-readable evidence states lead the workflow; Technical evidence preserves full JSON, UUIDs, provenance, spans, SHA-256, parser/template metadata, machine codes and immutable version links.

Navigation uses Applicant Evidence, Financial Profile, Fairness & Evaluation and Audit Trail. Four Financial Profile summaries use existing values above the unchanged 30/60/90-day Detailed underwriting evidence tables. Assessment withheld emphasizes insufficient evidence and null scores; its reasons depend on the stored evidence and artifact scope. No core ledger schema, financial calculation, feature contract, authorization boundary or health-mode value changed.

The default runtime verifier found its configured ports 8000/8501/8001 occupied and stopped. The same verifier was then exercised through an in-memory harness that remapped those ports to operating-system-assigned unused loopback ports. API/Streamlit/Prism startup, synthetic workflow, official SDK reads, owned-process shutdown and temporary-storage cleanup succeeded. This is local synthetic software evidence; no manual visual browser review, public deployment, external MCP-client reuse or real underwriting validation was performed.

Final default verification: **253 passed, 3 optional heavy tests deselected in 44.14s**, Python 3.14.8. A fresh workspace `.pytest_temp` directory and disabled pytest cache bypassed local temporary/cache ACL failures; no tests were excluded beyond the configured optional heavy marker. The added balance-history regression distinguishes a complete history with zero balances from an unavailable liquidity ratio and does not report missing history merely because that ratio is null.

Command: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp <fresh .pytest_temp directory>`. Replace the placeholder with a new directory inside the ignored workspace `.pytest_temp` root. A read-only check of the already running API on port 8000 still returned its old OpenAPI title; existing user services were not restarted. Restart the local API to load the new metadata and /docs code.

## Targeted UI polish — 2026-10-05

Overview alone retains the full hero; the other nine pages have compact titles and helper lines. The secondary demo notice uses explicit dark text on light amber, including nested Markdown text. CSS hides only the Deploy button and heading link anchors, preserving the Streamlit header, toolbar and sidebar collapse/expand controls. Actions read Assess available evidence, Load assessment and Review candidate evidence. Insufficient assessments display Assessment withheld — Insufficient evidence without changing their null score or backend status.

Financial Profile retains its summary-first layout and all three original feature windows, with readable labels, evidence notes and shortened contributor UUIDs. Cards also use short references. Full identifiers, machine keys, hashes and payloads remain in collapsed Technical evidence. Audit Trail/Event Ledger and Explanation have intentional empty states; Fairness & Evaluation retains its limitation and puts its UUID input in collapsed Advanced lookup. A successfully loaded assessment remains selected for Explanation. Financial calculations, API/MCP contracts and authorization were not changed.

Verification: **253 passed, 3 optional heavy tests deselected in 46.67s**, Python 3.14.8. The first targeted run encountered access denial in the existing workspace `.pytest_temp` folder; the full suite passed with a fresh system temporary directory and pytest cache disabled. An additional ephemeral AppTest check verified all ten page headers, empty states, readable feature labels and collapsed lookups. The existing runtime verifier passed through an in-memory harness using unused loopback ports and isolated system temporary storage: API/Streamlit/Prism startup, synthetic workflow, official SDK reads and owned-process/storage cleanup succeeded. No verifier source edit was needed. Browser visual inspection and video recording remain unperformed.

Full-suite command: `$testTempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('agrogami-ui-polish-' + [guid]::NewGuid().ToString('N'))` followed by `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp $testTempRoot`.

Navigation follow-up, 2026-10-05: removed the toolbar-hiding selectors; only Deploy and heading link anchors are hidden. Full default suite rerun on Python 3.14.8: **253 passed, 3 optional heavy tests deselected in 56.47s**, using a fresh system temporary directory and disabled pytest cache. CSS review found no header/sidebar/navigation hiding rules; browser visual verification remains unperformed.

## Final remediation, verification and freeze pass — 2026-10-05

Current release version **0.2.0** (pyproject, `agrogami.__version__`, FastAPI `/health` and OpenAPI metadata; enforced by tests/test_version_consistency.py). The `.venv` editable-install dist-info still reports 0.1.0 because setuptools is absent from the environment and refreshing it would require a network build; rerun `pip install -e ".[test,local,trees,fairness]"` to update it. Runtime and API values do not read that metadata.

Remediation from the preceding pass (committed as `fix: audit auth`) was preserved. This pass changed only: finite TreeSHAP validation (`explain_tree` rejects a nonfinite native target, base value, contribution or additivity error; `TreeExplanation` uses finite floats, so creation, persisted JSON reload and API/MCP response models reject NaN/±Infinity; valid explanations are unchanged), version synchronization, pytest default options (repository-local `.pytest_temp/default` basetemp and disabled cache plugin, mirroring scripts/run_tests.ps1), `constraints-tested.txt` and documentation.

Final default suite: **460 passed, 3 optional heavy tests deselected** on Python 3.14.8 via `.\.venv\Scripts\python.exe -m pytest -q` (scripts/run_tests.ps1 gives the same result). Before the fixes the suite had 28 failures: 27 pre-written nonfinite-SHAP regressions and the version-consistency regression. Targeted: financial/governance/lineage/authorization/config-security/demo-tooling/version suites **207 passed**; SHAP/explanation selection **38 passed**. `pip check`: no broken requirements.

Live runtime: `python -m scripts.verify_local_runtime --api-port 0 --ui-port 0 --mcp-port 0` PASSED — FastAPI `/ready` and project `/docs`, Streamlit `/_stcore/health`, synthetic review/correction/features/snapshot flow, authenticated Bearer Streamable HTTP Prism `/mcp` via the official SDK (initialize, exactly four tools, three reads). Owned process trees stopped (host Python process count unchanged) and no runtime temporary directory remained.

`python -m scripts.prepare_demo` PASSED: a new SYNTHETIC_DEMO scenario directory with manifest identifiers (applicant, source, candidate, original event, accepted/current event, assessment, 30/60/90 feature snapshots). The assessment is INSUFFICIENT_EVIDENCE with a null score, so no evaluation run applies. SHA-256 comparison showed no change to earlier scenarios, `private_data/agrogami.db` or stored objects.

Secret/privacy scan: no committed credential (Git history included for the legacy demo token names); examples hold placeholders, `${input:...}` prompts or synthetic test values; the runtime verifier generates per-run UUID credentials. `.env`, `.vscode/mcp.json`, `.streamlit/secrets.toml`, private_data, uploads, model_cache, `*.db`/`*.sqlite*` and `.pytest_temp` are Git-ignored and excluded from the Docker context; the Dockerfile copies only pyproject, README, src and docs. No private absolute Windows path appears in tracked content.

Docker: executable not installed on this host — IMPLEMENTED, NOT runtime verified. External MCP clients: no external Codex/Claude/Antigravity invocation is recorded in this repository, so none is claimed.

The historical Temp audit directory could not be removed because of Windows ACL restrictions (the stale repository `.pytest_cache` has the same restriction and is ignored). All permanent regression assets have been internalized into the repository and no source/test/runtime dependency remains on that Temp location.

Counts in earlier sections (223 → 251 → 253) are historical records, not the current state.

## Privacy/security review

No raw evidence/phone numbers/private paths/tokens in ordinary UI/client/MCP logs. SDK diagnostics retain structured severity only; a regression verifies untrusted log text is removed. Candidate raw fields are intentional reviewer/admin views, not logs. Source API metadata is allowlisted; upload filenames are not accepted; object names are UUIDs. /docs reads only a fixed document allowlist and escapes embedded HTML. Private data/cache/.env/database/log/temp paths are ignored for Git/container context.

Local demo mode (`AGROGAMI_LOCAL_DEMO_MODE=true`) remains an explicit localhost synthetic convenience with dataset-wide access; deployment mode requires authentication and explicit applicant grants for nonadmin credentials. No production identity, applicant isolation, encryption, rate limits, consent/retention/migrations or durable interrupted-snapshot recovery is claimed. Ledger correction and subsequent assessment journal are separate transactions.

## External blockers and remaining human actions

Real provider templates, consented financial annotations, trained DeBERTa/TrOCR/LayoutLMv3 checkpoints and mature linked repayment outcomes remain absent. Real predictive/calibration/fairness/latency claims remain blocked. Manual external Codex/Claude/Antigravity MCP reuse, final UI review, Docker-capable validation, production operations/security, explicitly authorized public deployment, video recording and proof links remain human/external tasks. No fake result/URL/proof was created.

## ANTIGRAVITY HANDOFF

Historical heading retained for foundation contract compatibility. The user superseded the previous coding-agent handoff: Codex completed the feasible local product pass. There is no pending UI/docs/Prism implementation handoff. Read docs/codex-handoff.md → Codex Final Implementation Record for current status. Next stage is human review and operational/data/proof work, not regenerating the core.

## Exact run commands

```powershell
.\.venv\Scripts\python.exe -m uvicorn agrogami.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
.\.venv\Scripts\python.exe -m streamlit run src/agrogami/ui/app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
.\.venv\Scripts\python.exe -m agrogami.mcp.server
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.verify_local_runtime --api-port 0 --ui-port 0 --mcp-port 0
.\.venv\Scripts\python.exe -m scripts.prepare_demo
```

Prism requires AGROGAMI_MCP_ENABLED=true and configured secret credentials. README contains clean-install/environment/Docker commands.
