# Claims register

Allowed statuses: PLANNED, IMPLEMENTED, TESTED, DEMONSTRATED_WITH_SAMPLE_DATA, DEMONSTRATED_WITH_SYNTHETIC_DATA, BLOCKED_EXTERNAL_DEPENDENCY, UNSUPPORTED. Status reflects the evidence in the final column; no real-data claim is implied by synthetic results.

| Claim | Status | Evidence / boundary |
|---|---|---|
| Central configuration and privacy-safe intake logging | TESTED | tests/unit/test_config_intake.py |
| Canonical Decimal/aware-time/provenance contracts | TESTED | tests/unit/test_schemas.py |
| Candidate originals and critical-field review | TESTED | tests/unit/test_candidates.py; no parser inference |
| Deterministic duplicate, receipt/SMS, reversal and receivable reconciliation | TESTED | tests/unit/test_reconciliation.py; test_features.py; test_safety_edges.py |
| SQLite persistence, separate audit attributes and atomic correction lineage | TESTED | tests/integration/test_storage.py |
| PostgreSQL schema compatibility | TESTED | DDL compilation only in test_storage.py; live execution unverified |
| Live PostgreSQL operation | PLANNED | Requires configured server and optional driver; not run |
| Deterministic 30/60/90-day as-of features and null/coverage behavior | TESTED | tests/unit/test_features.py; test_safety_edges.py |
| Daily balance observations without invented cash transactions | TESTED | test_safety_edges.py::test_daily_balances_need_no_invented_cash_movements |
| Synthetic end-to-end storage/reconciliation/features | DEMONSTRATED_WITH_SYNTHETIC_DATA | 20 parameterized cases in tests/integration/test_pipeline.py; reopened SQLite round trips |
| Deterministic safe synthetic scenarios | TESTED | tests/unit/test_fixtures.py; sample_data/synthetic_events.json |
| Real provider-template parsing or model extraction accuracy | BLOCKED_EXTERNAL_DEPENDENCY | Requires consented examples, verified templates and annotations |
| Real-world feature validity and underwriting effectiveness | BLOCKED_EXTERNAL_DEPENDENCY | Requires consented longitudinal evidence and outcomes |
| Real financial TrOCR/LayoutLMv3/DeBERTa checkpoints and linked-outcome risk models | BLOCKED_EXTERNAL_DEPENDENCY | Adapters/scaffolds exist; actual annotated data/checkpoints absent |
| Real calibration, explanation and fairness validation | BLOCKED_EXTERNAL_DEPENDENCY | Utilities exist; representative trained model/evaluation data absent |
| Streamlit UI, project docs and Prism protocol | TESTED | tests/integration/test_local_product.py; synthetic workflow and internal protocol only |
| Public deployment | PLANNED | No target, credentials, deployed URL or production validation |
| Predictive performance, fairness, latency or production-readiness claims | UNSUPPORTED | No supporting empirical evaluation |
| Public demo/video proof or external MCP reuse | PLANNED | No public deployment, video or manually connected external client evidence |

Verified complete default test run and per-subsystem counts are recorded in docs/codex-handoff.md. Synthetic pipeline tests are software evidence, not dataset/model metrics.

## Second-pass component evidence

| Claim | Status | Boundary |
|---|---|---|
| Strict synthetic bKash-like/Nagad-like SMS candidate parser | TESTED | 21 tests in test_sms_parser.py; unverified production templates remain blocked |
| DeBERTa BIO contracts, constrained decoding and local loading adapter | TESTED | test_extraction_adapters.py / test_local_loading_fakes.py; fake loader/inference and preflight only; no real checkpoint/accuracy |
| Financial DeBERTa checkpoint | BLOCKED_EXTERNAL_DEPENDENCY | Requires annotations and actual training artifact |
| Image preprocessing, source-coordinate regions and local TrOCR/LayoutLMv3 adapters | TESTED | test_extraction_adapters.py; test_local_loading_fakes.py; fake application pipeline; trained extraction checkpoints absent |
| Bangla handwriting accuracy / financial layout extraction accuracy | BLOCKED_EXTERNAL_DEPENDENCY | No annotated evaluation or trained financial checkpoint |
| Dataset identity adapters, censored outcomes and temporal input contracts | TESTED | test_dataset_adapters.py / test_risk_governance.py; synthetic local samples only, no public benchmark/download |
| Scoped logistic baseline / LightGBM primary / XGBoost challenger interfaces | TESTED | test_risk_governance.py; native tiny synthetic fitting/round trips; no real/public experiment results |
| Separate sigmoid/isotonic calibration and evaluation utilities | TESTED | test_risk_governance.py / test_research_scripts.py; synthetic holdouts and support gates; no real calibration claim |
| Project-specific 300–850 score formula | TESTED | Formula/endpoint/clipping tests in test_risk_governance.py; not FICO/bureau-equivalent or approval |
| Raw-margin TreeSHAP with additivity and controlled evidence reasons | TESTED | test_explanations_fairness.py; native LightGBM/XGBoost toy tests and controlled evidence tests; no causality |
| Offline group metrics, Wilson intervals and Fairlearn experiment wrapper | TESTED | test_explanations_fairness.py; Fairlearn 0.14.0 native offline smoke passed; no actual fairness/parity finding |
| Evidence-gated immutable assessment snapshot service | TESTED | test_backend_api.py; automatic unscored correction append, preserved history, insufficient evidence/public scoring gates |
| Versioned FastAPI backend and demo role/token boundary | TESTED | 34 tests in test_backend_api.py; configured default startup, routes/roles/privacy; no production auth/deployment claim |
| Local risk training/calibration/evaluation script workflow | DEMONSTRATED_WITH_SYNTHETIC_DATA | test_research_scripts.py; actual local toy fitting and report persistence only |
| Extraction training scaffold execution on actual financial annotations/checkpoints | BLOCKED_EXTERNAL_DEPENDENCY | Scripts/preflight/loader fakes exist; no annotation corpus or checkpoint supplied |
| Python 3.14 numerical backend compatibility | TESTED | docs/dependency-compatibility.json; import/native smoke checks and pip check passed |
| Optional transformer dependency compatibility | IMPLEMENTED | Python 3.14 wheel-resolution dry run succeeds; stack/checkpoint execution not tested |

Historical second-pass default suite: **223 passed, 3 heavy checkpoint tests deselected** on Python 3.14.8. Original **107 tests separately reconfirmed**. No large model download or real-data evaluation occurred. See build-status.md and the second-pass handoff for counts and exact boundaries.

## Local completion evidence

| Claim | Status | Evidence / boundary |
|---|---|---|
| Ten-page Streamlit HTTP-service workflow | TESTED | test_local_product.py: all pages and full synthetic intake/review/feature/assessment/audit AppTest; no browser manual review claimed |
| Marked synthetic document intake and reviewer-only candidates | TESTED | test_local_product.py; no filename/path intake; raw fields intentional authorized review only |
| Synchronized project /docs and readiness | TESTED | docs/HTML escaping/path-selection tests; database/optional artifact state; Swagger unchanged |
| Prism four-tool read-only Streamable HTTP protocol | TESTED | actual initialize/list/call HTTP protocol in test_local_product.py; unknown/write tools denied |
| Prism Bearer/demo roles, minimized data and safe SDK diagnostics | TESTED | viewer fairness denial/reviewer retrieval/minimized payload/log redaction regressions |
| Local API/UI/Prism process runtime | DEMONSTRATED_WITH_SYNTHETIC_DATA | scripts.verify_local_runtime executed successfully; official SDK reads, owned process-tree stop and temporary-storage cleanup |
| Synthetic correction/recomputed features/immutable snapshots | DEMONSTRATED_WITH_SYNTHETIC_DATA | live smoke plus HTTP client/UI tests preserve old records and reference new event versions |
| Docker artifacts and local run helpers | IMPLEMENTED | Dockerfile/compose/ignore/healthchecks and relative PowerShell helpers; Docker unavailable, no build/runtime proof |
| External Codex/Claude/Antigravity MCP client reuse | PLANNED | No manually connected external client invocation; internal official SDK tests are separate evidence |
| Public deployment/video/proof links | PLANNED | No public target/credentials/URL or video provided/performed |
| Representative borrower risk/calibration/fairness/latency validation | BLOCKED_EXTERNAL_DEPENDENCY | No real financial checkpoints, representative linked mature outcomes or annotations |

Current verified full default suite: **251 passed, 3 heavy tests deselected**, Python 3.14.8. All original foundation and second-pass cases remain green. Tests are software evidence, not real-world underwriting/accuracy/fairness proof.
