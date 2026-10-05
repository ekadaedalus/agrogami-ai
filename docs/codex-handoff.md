# Codex Handoff

The sections through "Claims That Must NOT Yet Be Made" record the first-pass baseline. First/second-pass sections below are historical records. The "Codex Final Implementation Record" records local completion; the appended presentation and targeted UI polish records describe subsequent changes. Previous exclusions/handoff tasks are superseded. The original deterministic core remains unchanged; newer interfaces do not imply real-model validation.

## Repository State

At the start, AGENTS.md, README.md, .gitignore, .env.example, pyproject.toml, requirements.txt, all docs and src package initializers were empty. tests/, sample_data/, notebooks/ and scripts/ had no implementation. A .venv (Python 3.14.8) and .vscode configuration existed and were retained. No .git directory existed; Git status could not run. Directory names were preserved. This is the authoritative greenfield foundation, not a modification of an earlier system.

## Implemented

- Agent architecture/privacy constraints, installable src package and central environment configuration.
- Pydantic v2 enums, canonical events, original candidate fields, source/provenance, review decision, correction, coverage, feature snapshot, assessment skeleton and separate protected audit contracts.
- SHA-256 byte integrity intake, UUIDs, ingestion timestamps and allowlisted JSON logging.
- Seven SQLAlchemy relational tables with validated JSON payloads, source foreign keys, atomic append-only corrections, unique version predecessor, correction lookup and ancestor history.
- Deterministic required/critical-field validation, plausibility/currency/semantics checks, duplicate and cross-source reference reconciliation, ambiguity review, linked full reversals and capped receivable settlement.
- Balance equation with explicit completeness and fee convention; unknown returns None.
- Twenty reproducible synthetic event scenarios and clearly labeled invented SMS examples; candidate fixtures contain no model output.
- Deterministic 30/60/90-day feature windows, availability/version filtering, cash flow, CV, punctuality, liquidity, circulation proxy and coverage metadata with contributors.

## Tested

Complete default suite: **107 passed**, Python 3.14.8, Windows, 2026-10-03. No model downloads. The final command is listed below. Counts include parameterized cases.

| Subsystem | Test file | Cases / type | Result |
|---|---|---:|---|
| Package, ignored private paths, authoritative docs | tests/unit/test_foundation.py | 3 unit | Passed |
| Canonical money/time/provenance/candidate freezing | tests/unit/test_schemas.py | 13 unit | Passed |
| Candidate required fields/ambiguity/confidence | tests/unit/test_candidates.py | 6 unit | Passed |
| Configuration, environment precedence, intake and logging | tests/unit/test_config_intake.py | 4 unit | Passed |
| Duplicate/receipt/reference review, semantics, links and balances | tests/unit/test_reconciliation.py | 18 unit | Passed |
| Windows, leakage, exclusions, coverage, ratios and version availability | tests/unit/test_features.py | 23 unit | Passed |
| Historical obligations, missing payment, rejection, determinism, balance snapshots and duplicate settlements | tests/unit/test_safety_edges.py | 13 unit | Passed |
| Synthetic determinism and source labels | tests/unit/test_fixtures.py | 1 unit | Passed |
| SQLite round trips, separate audit, immutable/atomic lineage and PostgreSQL DDL | tests/integration/test_storage.py | 6 integration | Passed |
| All synthetic scenarios through persistence/reopening/three-window features | tests/integration/test_pipeline.py | 20 integration | Passed |

Dependency installation and scripts/export_fixtures.py were also executed successfully. PostgreSQL DDL compilation is not live PostgreSQL verification. No real-data, predictive, fairness or latency test was performed. Python 3.11–3.13 were not separately exercised.

## Important Architecture Decisions

Preserve typed Python 3.11+, Pydantic v2, Decimal monetary arithmetic and aware UTC timestamps. Float financial inputs are rejected. Monetary storage uses decimal strings inside JSON payloads to preserve SQLite precision. SQLAlchemy identity/source/version keys are relational. Application writes insert only; production migrations and DB access control remain separate work.

Original candidates/events are never overwritten by correction. Identity and provenance cannot change inside correction. Human reviewer aliases and reasons are required, and version/audit inserts commit atomically. Only current versions can be corrected; uniqueness prevents branches. Pydantic freezing is shallow; repository persistence preserves original copies.

Coverage is explicit caller attestation and is not derived from event presence. Features must preserve nulls and reasons. Financial facts, ownership, fee conventions, complete schedules or complete statements must never be silently imputed. Source hashes prove byte equality/integrity, not authenticity. Protected audit attributes have a separate table and no baseline-feature input path. Logs accept only safe record UUIDs and schema version through a fixed operation vocabulary.

As-of selection requires event, ingestion and version creation time before scoring. Later corrections cannot alter earlier snapshots. Reconciliation can inspect older available events for links while cash windows remain half-open. Output-derived UUID5 snapshot IDs are deterministic and do not prove truth. UTC calendar days are used; partial endpoints are conservatively incomplete.

## Canonical Data Contracts

CanonicalEvent has event/applicant/account/source IDs, source type, event/ingestion/creation times, transaction type/direction, nullable amount/fee/balance and due/payment dates, currency, reference/counterparty/provider, validation/review metadata, extractor/schema versions, supersession/duplicate/reversal/settlement links, ownership/medium-evidence flags, confidence, provenance and missingness. `payment_record_complete` is an explicit assertion needed to distinguish verified unpaid from unknown payment evidence.

BALANCE_SNAPSHOT extends transaction types to represent a verified daily closing balance without inventing a transaction: NEUTRAL direction, known account/balance, nullable amount/fee. It is excluded from cash flow and active transaction days. Complete daily balance history can therefore include genuine no-movement days.

CandidateExtraction preserves original raw values alongside normalized candidates, field confidence, location and parser/version. ReviewDecision checks critical candidate fields but does not promote them to canonical events. Provenance includes hash, document page/region and SMS span/provider/template. Source carries hash, ingestion time, synthetic marker and metadata. Correction records original/new IDs, reason, demo-safe alias and creation time. Store.history and Store.corrections recover lineage/audit information.

Coverage records complete UTC observed/balance/schedule days, known_at, optional evidence IDs and reasons. FeatureSnapshot includes applicant, scoring time, 30/60/90 window, schema version and FeatureValues with contributor IDs/reasons. Assessment is evidence-status metadata only. ProtectedAuditAttributes remains separate with a consent reference. Read data-contract.md and schemas/contracts.py for authoritative details.

## Financial Reconciliation Rules

- Duplicates: scoped exact transaction reference plus matching applicant/account/provider, amount/fee/currency/direction/ownership produces one economic event; originals remain stored. Contradictory groups are all reviewed, including additional copies.
- SMS + receipt: matching economic facts/reference count once regardless of their presentation. References are evidence inputs, not source authenticity proof. Missing-reference proximity within five minutes causes review, never auto-merging.
- Reversals: link one accepted same-applicant/account/currency original, opposite direction, equal amount and fee, prior timestamp; one full cancellation only. Unlinked, partial or repeated reversals require review. Full pairs have zero economic effect.
- Own-account transfers: no external income/outflow. Cash-in/out are medium changes unless explicitly evidenced as external.
- Khata: credit sales and receivables are noncash; no income until an accepted linked settlement. Cumulative settlement cannot exceed the original receivable and must be an inflow.
- Missing evidence: critical nulls, low confidence, unknown ownership, unsupported template and contradiction route to review. Missing receipt alone is not unpaid. No critical-fact imputation.
- Balances: use B_after=B_before+inflow-outflow-fee only with explicit complete movements, known amounts/directions/accounts and known separate-fee convention. Incomplete evidence returns None instead of a false inconsistency. A false result is available for caller review; automatic source-completeness certification is absent.

## Feature Engine Status

Implemented for all three windows: external inflow/outflow/net observed totals, observed-day population CV (epsilon 0.01 BDT), verified punctuality and median delay, balance Q0.10/mean liquidity floor, observed minimum, turnover/circulation proxy, coverage days/span/gaps/shares, active-day count/share, source count/mix, balance/schedule coverage, missingness and reviewed/accepted shares.

Unobserved days are excluded from CV, not filled with zero. Observed totals are partial when coverage is incomplete, and null if no qualifying evidence exists. Complete attested no-activity windows may yield known zero. Punctuality/delay require a complete due-obligation schedule and payment record; obligations created before the window can enter by due date. Payment dates on/after scoring date are excluded. Liquidity requires a verified single-account closing value per full day and valid positive mean; incomplete histories yield null while observed minimum remains. Turnover additionally requires complete cash coverage. Every feature has contributing IDs and reasons; protected attributes are absent.

Known v1 boundaries: no FX, partial reversal allocation, multi-account balance consolidation, provider inference or fuzzy matching. Full reversals cancel original pairs rather than treating refunds as standalone income. Own/medium transfer fees need separate explicit external fee evidence. See feature-dictionary.md for formulas and semantics.

## Configuration

Python 3.11+ (tested 3.14.8); installation: `python -m pip install -e ".[test]"` in the selected environment. Dependencies: Pydantic v2, pydantic-settings, SQLAlchemy 2.x and pytest test extra. PostgreSQL driver: `python -m pip install -e ".[test,postgres]"`.

| Variable | Default |
|---|---|
| AGROGAMI_ENV | development |
| AGROGAMI_DATABASE_URL | sqlite:///private_data/agrogami.db |
| AGROGAMI_PRIVATE_DATA_DIR | private_data |
| AGROGAMI_MODEL_CACHE_DIR | model_cache |
| AGROGAMI_LOG_LEVEL | INFO |
| AGROGAMI_DEMO_MODE | true |
| AGROGAMI_ENABLE_REAL_MODELS | false |

Settings reads .env. DATABASE_URL is a fallback alias; AGROGAMI_DATABASE_URL takes precedence. Demo+real-model flags are rejected together, but neither flag implements model execution. Private/cache defaults are ignored. Custom paths must be outside source control. `.env` and database files remain ignored; no secrets were included. SQLite parents are created on initialization. `postgresql://...` becomes `postgresql+psycopg://...`; a live server/driver is required. DDL portability only has been tested.

## Run Commands

PowerShell from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/export_fixtures.py
```

The environment already exists; recreate only if needed. Copy the environment example only when creating local overrides. On Linux/macOS substitute `.venv/bin/python`. There is no UI, server or MCP run command. README.md includes a library example using a fresh database.

## Files the Next Agent Must Read First

1. AGENTS.md
2. docs/codex-handoff.md
3. docs/architecture.md
4. docs/data-contract.md
5. docs/feature-dictionary.md
6. docs/claims-register.md
7. docs/build-status.md

Then read schemas/contracts.py, storage.py, validation/rules.py, features/engine.py and the test suite before extending contracts.

## Remaining Work

1. Consented evidence acquisition, canonical annotations and verified coverage/source/provider semantics; implement deterministic provider/template adapters with candidate provenance and reviewed ambiguity.
2. Evaluate extraction adapters with annotated evidence, then add scoped OCR/TrOCR/LayoutLMv3 inference and extraction-model evaluation. No checkpoint selection or model download was done here.
3. Develop predictive models only with suitable longitudinal outcomes and temporal splits (DeBERTa/LightGBM/XGBoost as separately justified).
4. Validate calibration, explanations/TreeSHAP and subgroup/fairness/Fairlearn behavior using real evaluation evidence.
5. Build authorized human-review UI and assessment workflow, then Prism MCP against stable contracts.
6. Add migrations, auth, privacy operations, multi-version CI and live PostgreSQL validation before private deployment; public deployment/demo proof only with verified evidence and authorization.

The exact next handoff point is phase 1 above. Do not start by training models or building a public UI. Empty downstream directories remain intentionally unimplemented.

## External Dependencies / Blockers

No blockers remain for running the deterministic suite. Real datasets, consent, provider template verification, annotations, model checkpoints and repayment outcomes are absent; these block empirical downstream claims. External credentials are needed only for subsequently scoped integrations/deployment. Live PostgreSQL needs a provisioned server and driver. Reviewer authentication, production encryption, migration strategy and real statement completeness verification require further implementation/product decisions. Git initialization/version control is user/team work; no commit or remote was created.

## Claims That Must NOT Yet Be Made

Do not claim real-provider extraction accuracy, transformer inference/training, credit-risk prediction, repayment performance/AUC, calibration, fairness, bias removal, SHAP explanations, latency targets, production security/readiness, successful deployment, public URLs, Streamlit UI, working Prism MCP, external MCP reuse or video/demo proof. Synthetic fixtures/test counts demonstrate deterministic software behavior only. Update claims-register.md only with actual new evidence.

# Codex Second-Pass Handoff

## Preserved baseline

Read AGENTS.md and the first-pass docs before changes. The exact requested baseline command passed all 107 tests on Python 3.14.8 before changes. The original ten test files were rerun during extension and again passed 107 tests. Original canonical schemas, storage.py, reconciliation rules, feature engine and fixtures were not rewritten or regenerated. config.py gained new settings only. Backend persistence uses independent metadata and a new insert-only journal instead of modifying the seven core tables.

## New components implemented

- Strict invented bKash-like/Nagad-like parser covering receipt/send-money/cash-in/cash-out/payment/reversal and nontransaction messages; anchored amount/fee/balance fields, explicit date/time offsets and source spans. Unsupported/ambiguous/missing-time messages remain candidates for review.
- Financial BIO token dataset contracts, transition validation and constrained Viterbi decoding. DeBERTa-family local adapter and explicit DeBERTa-v3-small training/inference architecture scaffold, requiring a real local financial checkpoint/label manifest.
- Raster loading, legibility warnings, explicit orientation, small-angle deskew, resizing, grayscale/autocontrast, line regions and output-to-original coordinate mapping. Local TrOCR recognition and LayoutLMv3 layout adapters return candidates only. Generic layout weights are not a financial extractor.
- Dataset identities, local risk CSV/FUNSD/BanglaWriting manifest adapters and configurable Berka normalization boundary. Original benchmark tasks/limitations remain separate. Research loan labels implement initial-current eligibility, >=90 DPD in 180 days and censoring. Temporal matrices reject post-decision availability; protected columns are excluded.
- Common scoped risk interface, standardized regularized logistic baseline, LightGBM primary and XGBoost challenger fitting/native-or-JSON persistence. Scopes distinguish real-linked experiments, public benchmarks, synthetic demos and untrained artifacts.
- Separate sigmoid/Platt-style and isotonic calibration, disjoint identity checks, model UUID/version binding, Brier/log loss/reliability curve/slope/intercept utilities and deterministic project display score.
- Raw-margin TreeSHAP with declared feature definitions/background, native-target additivity checks, and controlled evidence reasons with source/event lineage. LATE_VERIFIED_BILLS requires actual late dates, never missing receipts. LOWER_TAIL_LIQUIDITY requires complete balance evidence. INSUFFICIENT_EVIDENCE remains descriptive.
- Offline group counts, TPR/FPR/selection/review rates, Wilson intervals, small/undefined-group flags and equalized-odds difference. Fairlearn ThresholdOptimizer wrapper is offline only and keeps protected inputs separate.
- Immutable full assessment snapshots with evidence, features, scoped model, raw/calibrated probabilities, score, calibrator/dataset identity, explanations/policy/limitations and optional predecessor. Corrections through the application/API automatically append unscored NEEDS_REVIEW snapshots with explicitly unknown fresh coverage. Unknown/review evidence or absent artifacts withholds scores. Public benchmark scoring is withheld; synthetic computations are ILLUSTRATIVE. READY is a complete research computation, not VALIDATED underwriting.
- Application services, private UUID source objects, atomic source/candidate/event/job insertion, explicit candidate-review audits, event corrections, immutable evaluation records and versioned FastAPI routes. Job outcomes are synchronous intake records, not an implemented worker queue.
- Local viewer/reviewer/admin token boundary; no role-header trust. Review/assessment creation and protected fairness retrieval require reviewer/admin. Error responses/source metadata omit raw input and private object paths.

## New tests and verification

New files: test_sms_parser.py, test_extraction_adapters.py, test_local_loading_fakes.py, test_dataset_adapters.py, test_risk_governance.py, test_explanations_fairness.py, test_backend_api.py and test_research_scripts.py. They cover parser semantics/spans/review, BIO constraints/local loaders with fakes, preprocessing/provenance, scopes/censoring/leakage, numerical baseline/calibration/score, native tree/TreeSHAP and offline fairness, assessment immutability/unknowns, API permissions/routes/privacy and local script end-to-end execution. Optional tests/heavy/test_local_checkpoints.py requires explicitly supplied local artifacts; default selection excludes it and never downloads models.

The review-to-assessment automatic append was demonstrated missing by a failing regression (one stored assessment instead of two), then fixed in the new application service. The original core correction/storage logic was not changed. Core event/correction audit and subsequent review assessment use separate transactions; process failure between commits requires explicit recovery. Direct Store.correct remains ledger-only. Use ApplicationService.review for backend corrections and the applicant assessment-history endpoint to discover new snapshots.

Final complete suite: **223 passed, 3 optional heavy checkpoint tests deselected**, Python 3.14.8 / Windows. Original **107 tests separately passed after extension**. All 116 new default cases passed. No model/dataset download occurs in tests. `pip check` reports no broken requirements; numerical/native imports succeeded. Exact installed versions are in dependency-compatibility.json. Do not confuse the initial network-restricted PyPI attempt or unfinished-install collection with a Python compatibility failure.

| New subsystem | Test file | Passing cases |
|---|---|---:|
| Strict synthetic SMS semantics/spans/review | tests/unit/test_sms_parser.py | 21 |
| BIO constraints, preprocessing/provenance and fake extraction | tests/unit/test_extraction_adapters.py | 18 |
| Fake local loader flags/architecture and training preflight | tests/unit/test_local_loading_fakes.py | 4 |
| Local public-identity/document manifest adapters | tests/unit/test_dataset_adapters.py | 3 |
| Scopes, outcomes, leakage, native risk/calibration/display score | tests/unit/test_risk_governance.py | 24 |
| Native/fake TreeSHAP, controlled reasons and offline Fairlearn/metrics | tests/unit/test_explanations_fairness.py | 9 |
| API/service startup, routes/roles/privacy and immutable correction assessments | tests/integration/test_backend_api.py | 34 |
| Local risk/calibration/evaluation/report persistence and extractor evaluation/help | tests/integration/test_research_scripts.py | 3 |

Native LightGBM 4.7.0, XGBoost 3.4.1, SHAP 0.52.0 and Fairlearn 0.14.0 toy smoke tests passed. XGBoost's categorical default initially caused a SHAP interventional error; explicit `enable_categorical=False` resolved it without changing the target/background. Starlette's deprecated httpx test transport was replaced by httpx2. Optional heavy tests are available but unexecuted because actual trained checkpoints are absent.

## Model adapters and missing artifacts

Present: DebertaAdapter, TrOCRAdapter, LayoutLMv3Adapter, LogisticRiskModel, TreeRiskModel and Calibrator. No trained financial DeBERTa, TrOCR or LayoutLMv3 checkpoint was supplied, trained or invented. No real linked-outcome risk/calibration artifact exists. Generic base checkpoints require explicit local provisioning and verified architecture; token heads require the financial BIO label manifest. Default startup loads no checkpoint or risk model.

Extraction config paths are optional: AGROGAMI_DEBERTA_CHECKPOINT, AGROGAMI_TROCR_CHECKPOINT, AGROGAMI_LAYOUTLMV3_CHECKPOINT. Set enable_real_models=true and demo_mode=false only for explicitly supplied local extraction artifacts. Transformers/torch are optional; prebuilt-wheel resolution was verified without installing or executing trained models. Real inference/training remains blocked by checkpoints/annotations, not simulated as implemented results.

## Risk, calibration, explainability and fairness status

Risk code can fit explicitly supplied scoped datasets; only tiny synthetic tests exercise fitting here. Censored rows are excluded. Public benchmark artifacts cannot produce borrower assessment scores. Logistic parameters use safe JSON; trees use native formats. Artifact scope is declared research metadata, not authenticity or external validation proof.

Calibration uses a separate holdout with disjoint stable sample IDs. Isotonic has minimum support gates (100 samples, 10 per class, 10 distinct predictions). Neither gates nor score scaling prove real calibration. The project display score is not FICO/bureau-equivalent or an approval decision; preserve both raw and calibrated probabilities and score values.

TreeSHAP operates only on supported binary tree raw margin/log-odds, validates additivity, and preserves background identity/definitions. It is not causality or an attribution to calibrated score. Configure a local background explicitly; otherwise snapshots have descriptive reasons and null TreeSHAP with a limitation. No fabricated explanation is returned.

Fairness metrics are offline descriptive aggregate calculations with explicit membership, uncertainty and undefined denominators. Fairlearn optimization is offline research only. No protected attributes enter baseline feature/risk vectors; no future parity, production fairness or real subgroup finding is claimed. Exact native import/smoke-test compatibility appears in the final dependency report.

## API status and exact commands

Swagger /api/docs; OpenAPI /api/openapi.json; reserved /docs is 404. All requested v1 routes are implemented, plus explicit candidate acceptance. Read docs/backend-api.md for contracts. Default artifacts are absent: documents report BLOCKED_MODEL_ARTIFACT; unsupported SMS retains candidates; incomplete assessments withhold probabilities/scores. No UI, MCP, Docker, live documentation module, deployment or proof link exists.

PowerShell from repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -e ".[test,trees,fairness]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn agrogami.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
.\.venv\Scripts\python.exe scripts/dependency_report.py --output docs/dependency-compatibility.json
```

Optional actual extraction dependencies: `pip install --only-binary=:all: -e ".[models]"` using this environment. Optional local-load tests: `python -m pytest -m heavy`, with AGROGAMI_TEST_*_CHECKPOINT explicitly configured. No large model download occurs automatically.

Use ignored .env for AGROGAMI_DEMO_TOKENS JSON token→viewer/reviewer/admin mapping; tokens never belong in Git. Header: X-Agrogami-Token. Missing token is viewer, invalid credential 401, unauthorized review 403. This is local demo auth, not production identity or applicant isolation. Keep source objects in ignored private_data or a private path outside Git.

Risk settings: AGROGAMI_RISK_MODEL_PATH and AGROGAMI_CALIBRATOR_PATH together; non-synthetic artifacts need explicitly enabled research mode. Optional AGROGAMI_SHAP_BACKGROUND_PATH JSON includes identity, rows and feature_definitions. No paths are API response fields.

Scripts: train_extractor.py/evaluate_extractor.py for explicit local annotations/checkpoints or prediction pairs; train_risk.py/evaluate_risk.py for disjoint scoped splits and optional separate audit groups. `evaluate_risk.py --persist` appends actual local report metadata for evaluation routes. Use --help for exact required flags. These scripts are not evidence of real financial training or evaluation.

## Exact next Antigravity tasks

1. Read AGENTS.md, this second-pass section, architecture.md, data-contract.md, feature-dictionary.md, datasets.md, backend-api.md, claims-register.md and build-status.md.
2. Build Streamlit review/assessment flows against the backend. Make scope, nulls, evidence coverage, review state and project-score limitations visible; never substitute invented scores/checkpoints. Preserve immutable review/assessment history and demo authorization.
3. Implement the live project documentation web module at /docs without moving Swagger/OpenAPI from /api/docs and /api/openapi.json.
4. Implement Agrogami Prism MCP over application/domain services, preserving authorization, protected-audit separation and point-in-time evidence; do not expose raw source bytes through generic tools.
5. Prepare Docker/private deployment only after appropriate runtime configuration, migrations, authorization, storage/retention and operational tests. Public deployment/demo proof requires explicit authorization and actual evidence. No URL/video/result should be fabricated.

Real-data/checkpoint acquisition and validation remain parallel external work: consent, verified provider templates, financial BIO/transcript/layout annotations, actual local checkpoints, longitudinal current-loan follow-up and repayment outcomes. Do not merge unrelated public datasets and present them as Agrogami end-to-end validation. Production auth/encryption, applicant isolation, migrations, crash recovery, PDF handling and accurate word segmentation remain explicit limitations.

## Unresolved dependency issues / claims boundary

No interpreter downgrade occurred. Optional transformer wheel resolution succeeds for Python 3.14, but actual checkpoint execution has not been tested. Exact installed numerical versions, import outcomes and any native errors are captured in dependency-compatibility.json. Network sandbox/download issues do not establish library incompatibility.

Never claim real extraction accuracy/F1/CER, real predictive AUC/PR-AUC/KS, calibration/Brier validity, group fairness guarantees, latency targets, lender/provider integration, production identity/security, external MCP reuse, deployment URLs or video proof. Tests on explicitly synthetic data establish software behavior only. Keep claims-register.md evidence-specific.

# Codex Final Implementation Record

## Verified Starting State

Python 3.14.8 / Windows; 223 default tests passed and 3 optional local-checkpoint tests deselected before changes. Read the required agent/contracts/docs/configuration and source/test trees. No repository/core regeneration occurred. Financial schemas, storage, reconciliation, features and existing fixtures remain unchanged.

## Product Surface

Streamlit is implemented at src/agrogami/ui/app.py with ten coherent pages, typed central APIClient, safe formatting and marked samples. It performs no financial arithmetic. Candidate/provenance review and correction call authorized backend services. Unknown values/coverage/scores remain unavailable; scope and project-score/SHAP limitations are visible. Full UI synthetic flow and all pages passed AppTest. Manual browser review is still human work.

## Project Docs

/docs renders an allowlisted escaped Markdown collection synchronized with repository docs; includes overview/problem/users/architecture/contracts/extraction/features/risk/calibration/score/explanation/fairness/privacy/evaluation/datasets/API/Prism/CloudCamp/environment/demo/limitations/changelog. Swagger remains /api/docs and schema /api/openapi.json. No CMS or user-selected filesystem path exists.

## MCP

Agrogami Prism uses official MCP SDK 1.30.0, stateless Streamable HTTP /mcp, separate local process/shared database. Exactly four tools: get_evidence_ledger, get_assessment_snapshot, get_explanation_factors, get_fairness_audit. Tools read existing application/ledger/journal records, never write or compute model values. Bearer credentials reuse demo viewer/reviewer/admin; dedicated MCP token grants viewer only; fairness requires reviewer/admin. Missing/invalid HTTP credentials are 401. Local DNS-rebinding protection remains enabled. Outputs omit raw source bytes/account IDs/counterparties/transaction references/training sample IDs/row-level protected records. SDK log diagnostics are redacted to structured severity.

Actual four-tool HTTP protocol, registration/authentication/restrictions/unknown records/minimization/read-only behavior passed offline tests. Live official SDK initialization/list/reads also passed. External Codex/Claude/Antigravity invocation is separately PLANNED, not inferred from these tests. CloudCamp was not contacted and receives no product data.

## Integration

Marked synthetic SMS → hash/source intake → candidate spans → pending canonical event → authorized corroborated correction ? accepted ledger ? core reconciliation/features ? null/insufficient assessment with real reasons ? immutable journal. Further correction preserves originals, references new versions in recomputed features and appends a fresh unscored review assessment. Original assessment retrieval remains identical. UI and smoke tests expose the same service path. Missing checkpoints/coverage remain honest blockers, not fake low scores.

## Docker

Dockerfile, compose API/UI/optional Prism profile, private shared SQLite volume, nonroot Python 3.14 runtime, localhost published ports, environment tokens and API/UI healthchecks are prepared. Docker is unavailable here; config/build/run remain unverified. No public deployment occurred. README gives docker compose config/up/down commands.

## Tests

Final full default suite: **251 passed, 3 deselected** on Python 3.14.8. All 223 prior cases remain green, including original 107. Existing API /docs assertion changed intentionally from reserved 404 to implemented 200. New test_local_product.py has **28 passing cases** covering client/UI end-to-end, all pages, candidate/scope/privacy/docs/readiness, immutable corrections and MCP protocol/security/logging. No financial-core test was changed. Default tests need no internet, large models, public datasets, CloudCamp/external clients or PostgreSQL. pip check and editable installation succeeded. Exact dependency imports are in dependency-compatibility.json.

## Runtime Verification

API, Streamlit and Prism were actually started with isolated temporary SQLite/private storage. Verified API readiness/docs/intake/review/features/snapshots and UI health; official SDK initialized/listed/read Prism records. A Windows SQLite cleanup race was observed and fixed by stopping only owned process trees; final live verification exited zero after cleanup. No test process is intentionally left running. AppTest exercised actual UI sessions separately.

Exact commands, repository-root PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -e ".[test,local,trees,fairness]"
.\.venv\Scripts\python.exe -m uvicorn agrogami.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
.\.venv\Scripts\python.exe -m streamlit run src/agrogami/ui/app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
.\.venv\Scripts\python.exe -m agrogami.mcp.server
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.verify_local_runtime
```

Prism requires explicitly enabled MCP and configured ignored credentials. Existing running API smoke uses AGROGAMI_SMOKE_TOKEN with scripts/smoke_test.py. README documents Docker commands and all environment settings.

## External Blockers

Real provider templates, consented annotated financial datasets, trained DeBERTa/TrOCR/LayoutLMv3 checkpoints, initially-current mature loan follow-up and representative linked repayment outcomes are absent. Optional transformer stack is not installed/executed; real loading/training accuracy remains blocked. Docker executable is unavailable. No external credentials/public deployment target or external-client proof was provided.

## Claims Still Blocked

Real extraction F1/CER/Bangla accuracy, borrower AUC/PR-AUC/KS/calibration/fairness/latency, production security/legal compliance, universal parity, FICO equivalence, live providers/lenders, external MCP reuse and public/video proof cannot be claimed. Scoped research utilities and synthetic software tests do not establish those claims. Protected attributes remain offline-only separate inputs.

## Remaining Human Actions

Manual UI review and external-client MCP invocation; Docker-capable config/build/runtime checks; actual dataset/consent/annotation/checkpoint/outcome acquisition and validation; production authorization/applicant isolation/encryption/retention/migrations/crash recovery; explicitly authorized public deployment; video recording and real proof-link insertion. Codex completed the feasible local implementation; this record is not a transfer to another coding agent. The repository is ready for local research review and deployment preparation, not yet production financial/public deployment certification.

## Completion-Pass File Inventory

Created (18): src/agrogami/api/project_docs.py; src/agrogami/ui/__init__.py, app.py, api_client.py, formatting.py, samples.py; src/agrogami/mcp/server.py; scripts/smoke_test.py, verify_local_runtime.py, run_api.ps1, run_ui.ps1, run_mcp.ps1, run_tests.ps1; tests/integration/test_local_product.py; docs/local-demo.md; Dockerfile; docker-compose.yml; .dockerignore.

Modified (25): AGENTS.md; README.md; pyproject.toml; .env.example; .gitignore; src/agrogami/config.py, application.py, api/app.py; scripts/dependency_report.py; tests/integration/test_backend_api.py (only reserved docs assertion); docs/PRD.md, architecture.md, data-contract.md, feature-dictionary.md, evaluation-protocol.md, responsible-ai.md, limitations.md, claims-register.md, build-status.md, codex-handoff.md, mcp.md, datasets.md, backend-api.md, dependency-compatibility.md, dependency-compatibility.json.

requirements.txt was inspected and retained because it delegates to pyproject.toml. All four PowerShell helpers passed parser syntax checks. Docker executable is absent; PyYAML is also not installed, so no Docker CLI/config/build or independent YAML-parser validation is claimed. These are unavailable tools, not Python library incompatibilities.

# Product Presentation Pass — 2026-10-04

## Implemented presentation

The visible product identity is Agrogami AI, followed by “Traceable underwriting from financial records traditional credit systems ignore.” Supporting copy describes the evidence and risk-audit workbench for thin-file credit. The Demo environment notice remains visible and explains that demonstration outputs are illustrative, not lending decisions or validated individual creditworthiness.

Streamlit places API URL, Demo credential and Applicant UUID in collapsed Developer settings. Primary evidence views lead with readable status, amount, source and reasons. Technical evidence preserves UUIDs, complete JSON, source spans, SHA-256, parser/template metadata, exact machine reason codes and immutable version links. Renamed navigation is reflected in README and project documentation. Financial Profile adds summaries from existing values above unchanged 30/60/90-day tables. Assessment withheld preserves null scores and uses conditional reasons grounded in stored evidence and artifact scope.

FastAPI/OpenAPI metadata and /docs use the same product identity. The docs hero prioritizes the headline and tagline, with secondary limitation copy; allowlisted escaped Markdown rendering remains intact. Smoke tools assert the new brand and demo notice. No core schemas, ledger tables, financial calculations, feature contracts, review/correction semantics, authorization boundary or health-mode value were changed.

## Local runtime evidence

The default `python -m scripts.verify_local_runtime` attempt found configured ports 8000/8501/8001 already occupied and stopped without claiming success. The exact existing verifier was then executed through an in-memory harness remapping those ports to operating-system-assigned unused loopback ports. API, Streamlit and Prism started against isolated temporary synthetic storage. Readiness/docs, the synthetic intake/review/correction/feature/snapshot workflow and official MCP SDK reads succeeded. Owned-process shutdown and temporary-storage cleanup passed.

This confirms local software and internal protocol behavior only. No visual browser review, manually connected external MCP client, Docker build/run, public deployment, video proof, actual financial checkpoint inference or representative underwriting/calibration/fairness validation was performed in this pass. External data, artifact, operational and proof blockers remain unchanged.

## Final test evidence and existing services

Full default suite on Python 3.14.8 / Windows: **253 passed, 3 optional heavy tests deselected in 44.14s**. `tests/integration/test_local_product.py` now contributes **30 cases**, including readable evidence/retained audit details and a complete-zero-balance history regression. Complete balance history is not reported missing solely because a zero denominator makes the liquidity ratio unavailable. Historical counts in prior pass records above are unchanged.

Executed command: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp <fresh .pytest_temp directory>`, with the placeholder replaced by a new directory inside the ignored workspace `.pytest_temp` root. This avoided existing temporary/cache ACL failures. No default tests were excluded beyond the already configured optional heavy marker; no model or dataset was downloaded.

A read-only OpenAPI check of the existing API on port 8000 still returned its old title. Existing user-owned services were left running. Restart the local API to serve the edited metadata and /docs code; the isolated remapped-port runtime verification exercised the updated files without interrupting those services.

# Targeted UI Polish — 2026-10-05

The Streamlit hero is Overview-only; other pages use a title and helper line. The compact amber demo notice explicitly styles nested text; CSS hides only the Deploy button and heading link anchors, preserving the header, toolbar and sidebar collapse/expand controls. Actions use Assess available evidence, Load assessment and Review candidate evidence. Insufficient results display Assessment withheld — Insufficient evidence. Feature labels are readable and UUID references shortened, with complete originals in collapsed Technical evidence. Empty audit/explanation views guide the next action; the evaluation UUID is in Advanced lookup. Loaded assessment selection carries into Explanation. See local-demo.md for the walkthrough.

This pass changed UI presentation, existing UI assertions and synchronized docs only. Financial calculations, immutable ledger/snapshots, API/MCP contracts and role restrictions remain unchanged. Full default suite: **253 passed, 3 optional heavy tests deselected in 46.67s**, Python 3.14.8. An initial workspace temporary-directory access failure was bypassed with a fresh system temporary directory and disabled pytest cache. A separate ephemeral AppTest check passed for ten page headers, empty states, collapsed lookups and readable labels.

The existing live runtime verifier passed through an in-memory harness using unused loopback ports and isolated system temporary storage, including synthetic workflow, official SDK reads and owned-process/storage cleanup. Existing services were not stopped. Installed Streamlit selector names were checked, and the declared banner colors have 8.70:1 contrast; this is not browser visual inspection. Video recording, public deployment and real-data/model validation remain unperformed. Exact test commands and evidence are in build-status.md; external blockers remain unchanged.

# Final Remediation, Verification and Freeze — 2026-10-05

Starting state: remediation committed as `fix: audit auth`. With a repository-local basetemp the suite had 432 passed and 28 failed (pre-written nonfinite-SHAP and version-consistency regressions); the plain `pytest -q` command additionally errored on the ACL-locked system Temp `pytest-of-HP` directory.

Changes: src/agrogami/explainability/core.py (finite target/base/contribution/additivity validation in `explain_tree`; `FiniteFloat` fields and a nonnegative additivity error on `TreeExplanation`, covering creation, persisted reload and API/MCP response models); release version 0.2.0 in pyproject.toml, `agrogami.__version__` and API/OpenAPI metadata (the API reads the package value); pytest addopts use `.pytest_temp/default` and disable the cache plugin; constraints-tested.txt; README, build-status, claims-register, mcp and this record. No financial logic, feature definition, authorization boundary, MCP tool or UI design changed.

Verification: default suite **460 passed, 3 deselected**; `pip check` clean; live API/Streamlit/Prism verifier passed on OS-assigned ports with cleanup; prepare_demo created a fresh SYNTHETIC scenario without changing earlier ones; secret/privacy scan clean. Docker remains unexecuted (not installed). No external MCP client invocation is recorded here.

The historical Temp audit directory could not be removed because of Windows ACL restrictions. All permanent regression assets have been internalized into the repository and no source/test/runtime dependency remains on that Temp location.

Freeze commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m scripts.verify_local_runtime --api-port 0 --ui-port 0 --mcp-port 0
.\.venv\Scripts\python.exe -m scripts.prepare_demo
```
