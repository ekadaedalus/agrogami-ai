# Codex Handoff

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
