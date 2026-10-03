# Current limitations

Only the deterministic foundation exists. Included messages and events are invented synthetic fixtures. Provider names are illustrative; production SMS templates, authenticity, OCR accuracy, transaction ownership and complete statements are not verified.

Coverage is explicit caller attestation, not inferred truth. Numeric cash totals under partial evidence are observed totals with reasons; unobserved cash flow remains unknown. Balance ratios use a conservative single-account daily-closing contract. Multi-account aggregation, partial reversals, cross-currency conversion, separate fee refund conventions and provider-specific parsers are outside v1. Review rules use exact scoped references; reference-less proximity causes review, not fuzzy auto-acceptance.

Persistence uses relational identity/lineage plus JSON text payloads. Application writes are immutable; database administrators are not prevented from changing data. SQLite integration and PostgreSQL DDL compilation are tested; a live PostgreSQL server, schema migrations, concurrent production operation, encryption and backup recovery are not validated. Add migrations before modifying deployed schema. Default private paths are ignored; custom paths require equivalent source-control exclusion. Git was not initialized in the supplied directory.

Python 3.14.8 was used for this test run. Python 3.11+ is declared; a multi-version CI matrix remains future work. Dependency ranges are declared rather than a hash-locked production environment. No external credentials, real datasets, annotations or model checkpoints were provided or requested for this scope.

Not implemented: TrOCR, LayoutLMv3, DeBERTa, LightGBM, XGBoost, calibration, SHAP, Fairlearn, Streamlit, Agrogami Prism MCP, deployment or video proof. Empty downstream package directories preserve the supplied structure and do not indicate implementation.
