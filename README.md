# Agrogami AI ? Research Prototype

A Multimodal Framework for Fair and Explainable Alternative Credit Scoring from Unstructured Mobile and Paper Records.

This demonstration uses sample, synthetic, or de-identified records. Illustrative outputs are not lending decisions or validated individual creditworthiness. No real financial extraction checkpoint or linked-outcome borrower model is supplied.

## Local architecture and status

Evidence ? Candidates ? Validation & Reconciliation ? Canonical Ledger ? Deterministic 30/60/90-day Features ? Scoped Risk ? Holdout Calibration ? Explanation ? Offline Fairness ? Immutable Assessment.

Implemented: Decimal/aware-time contracts, immutable SQLite ledger/corrections, reconciliation, explicit null/coverage/provenance features, synthetic SMS parsing, raster preprocessing, local extraction adapters/scaffolds, logistic/LightGBM/XGBoost interfaces, calibration, project score, TreeSHAP and fairness utilities, FastAPI, Streamlit, project docs and authorized read-only Prism MCP. UI/API/MCP reuse application services; financial logic is not copied into presentation code.

Blocked: real provider templates, consented annotated financial records, trained DeBERTa/TrOCR/LayoutLMv3 checkpoints, mature linked repayment outcomes and validated borrower performance/fairness. No model/dataset download occurs automatically. Public deployment and proof links remain planned. Docker files are prepared; build/run is unverified because Docker is unavailable on the tested host.

## Setup

Tested interpreter: **Python 3.14.8, Windows**. Other declared Python versions are not separately tested. Keep the existing environment; on a clean machine select the intended Python before creating it.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -e ".[test,local,trees,fairness]"
Copy-Item .env.example .env
```

Copy the example only when creating a new local environment file; preserve existing overrides. `requirements.txt` delegates to pyproject.toml. Extras: ui, mcp, local, trees, fairness, models and postgres. Models dependencies never fetch checkpoints. Python 3.14 wheels installed successfully for Streamlit 1.65.0, MCP 1.30.0 and Markdown 3.11; see dependency-compatibility.json.

In ignored `.env`, configure `AGROGAMI_DEMO_TOKENS` as JSON mapping locally generated secret tokens to viewer/reviewer/admin. Do not commit tokens. UI uses the entered credential; API uses X-Agrogami-Token. No credential permits API viewer reads; invalid credentials fail. Candidate review, corrections, assessment creation and fairness retrieval require reviewer/admin. This is dataset-wide local research authorization, not production identity or applicant isolation.

## Run API, UI and Prism

Run each in its own PowerShell terminal from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn agrogami.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
.\.venv\Scripts\python.exe -m streamlit run src/agrogami/ui/app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
.\.venv\Scripts\python.exe -m agrogami.mcp.server
```

Before starting Prism set AGROGAMI_MCP_ENABLED=true and a secret AGROGAMI_MCP_AUTH_TOKEN or reuse configured demo tokens. Dedicated MCP token grants viewer only; demo reviewer/admin tokens authorize aggregate fairness. Send Authorization: Bearer on every Streamable HTTP request. Exactly four tools: get_evidence_ledger, get_assessment_snapshot, get_explanation_factors, get_fairness_audit. No write tools exist. Internal SDK protocol verification does not prove external Codex/Claude/Antigravity connection; manual external reuse remains planned.

Local UI: http://127.0.0.1:8501. Project docs: http://127.0.0.1:8000/docs. Swagger: http://127.0.0.1:8000/api/docs. OpenAPI: /api/openapi.json. Health: /health. Readiness: /ready (database plus optional artifact presence). Prism: http://127.0.0.1:8001/mcp. These are local run addresses, not public deployments.

Windows helpers: scripts/run_api.ps1, run_ui.ps1, run_mcp.ps1, run_tests.ps1. They use repository-relative paths. On Linux substitute .venv/bin/python.

## Demonstration

Enter a reviewer credential in the UI, keep the generated applicant UUID, select Intake / Samples ? SYNTHETIC ? External inflow and submit. Evidence Review displays original/normalized candidates, confidence, parser versions and spans. Explicitly corroborate synthetic ownership and append a reviewed version. Ledger/Features show actual accepted evidence and three windows; unknown coverage-dependent fields remain unavailable.

Create an assessment with unknown coverage: null score and insufficient/review status are expected, not a low score. Inspect real reasons, then correct the accepted amount with a Decimal string and reason. Audit / Versions shows old event/snapshot and newly appended unscored review snapshot. Candidate-only documents require complete manually corroborated canonical JSON; missing extraction checkpoints are visibly blocked. Evaluation/Fairness requires an actual stored run UUID; no fabricated charts are supplied.

See [demo walkthrough](docs/local-demo.md), [API](docs/backend-api.md), [Prism](docs/mcp.md), [datasets](docs/datasets.md), [evaluation protocol](docs/evaluation-protocol.md) and [limitations](docs/limitations.md).

## Tests and live verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m scripts.verify_local_runtime
```

Default tests run offline without model downloads, external MCP, PostgreSQL or CloudCamp. Three supplied-local-checkpoint tests are optional/heavy. Live verification requires free ports 8000/8501/8001; it starts isolated temporary API/UI/Prism processes, verifies the synthetic correction/snapshot flow and official SDK reads, then stops only its own processes.

Verified default suite: **251 passed, 3 deselected** on Python 3.14.8. All original 223 cases remain green, including the 107 deterministic foundation cases.

For an already running API, set AGROGAMI_SMOKE_TOKEN to a configured reviewer/admin credential and run:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_test.py --api-url http://127.0.0.1:8000
```

Smoke tooling intentionally appends synthetic records and returns nonzero on failure. No fake success is reported. Extraction heavy tests require explicitly supplied local artifacts; default startup loads no models/calibrator.

## Containers

Prepared commands; **not executed on this host**:

```powershell
docker compose config
docker compose up --build api ui
docker compose --profile mcp up --build
docker compose down
```

Configure ignored local tokens before enabling MCP. Default SQLite uses a named private volume shared by API/Prism. Ports publish only on localhost. Image uses Python 3.14, a nonroot user, no embedded secrets or model downloads; API/UI healthchecks are included. Docker config/build/runtime validation remains a human action on a Docker-capable machine. No public deployment occurred.

## Responsible use and remaining work

Project-specific 300?850 mapping is not FICO, bureau-equivalent or approval; scaling does not create calibration. TreeSHAP is association, not causality or legal adverse-action compliance. Protected attributes are separate offline inputs; Fairlearn optimization gives no future parity guarantee. Missing receipts are not nonpayment, unobserved days are not zero income, and public datasets retain their original target/scope.

Private data/cache/.env/database/logs are ignored; raw evidence is absent from ordinary logs. Production identity, applicant isolation, migrations, encryption, retention and interrupted correction/snapshot recovery remain work before public financial use. CloudCamp MCP is external competition guidance only and receives no product records. VS Code/coding assistants are development tools only; no RAG scoring, orchestration agents or automated lending/disbursement is implemented.

Repository: src/agrogami contains contracts, storage, application, extraction, features, risk/calibration, explainability/fairness, API, ui and mcp; tests contain unit/integration/optional heavy coverage; scripts contain local training/evaluation/run/smoke helpers; docs contain authoritative contracts/status/claims. Read [final implementation record](docs/codex-handoff.md), [build status](docs/build-status.md) and [claims register](docs/claims-register.md). Git was not initialized and no remote/release was created.
