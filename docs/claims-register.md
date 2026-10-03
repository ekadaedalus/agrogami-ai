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
| TrOCR/LayoutLMv3/DeBERTa and LightGBM/XGBoost | PLANNED | No inference/training implemented |
| Calibration, TreeSHAP, Fairlearn evaluation | PLANNED | Requires trained model and appropriate evaluation data |
| Streamlit UI, Prism MCP and deployment | PLANNED | No implementation, endpoints or URLs |
| Predictive performance, fairness, latency or production-readiness claims | UNSUPPORTED | No supporting empirical evaluation |
| Public demo/video proof or external MCP reuse | UNSUPPORTED | No deployment, video or external client evidence |

Verified complete default test run and per-subsystem counts are recorded in docs/codex-handoff.md. Synthetic pipeline tests are software evidence, not dataset/model metrics.
