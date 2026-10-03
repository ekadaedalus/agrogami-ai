# Product requirements: local research prototype

Agrogami AI is a traceable evidence/research workflow for human reviewers of mobile-money messages and paper records. It is not a lender or validated creditworthiness service.

Implemented: deterministic canonical ledger/features, candidate/model adapters, scoped research risk/calibration/explanation/fairness services, immutable snapshots, FastAPI, ten-page Streamlit application, synchronized project docs and authorized four-tool read-only Prism. Application/domain services are the sole source of financial logic.

Acceptance criteria: Decimal money and aware timestamps; original candidates and hash/span/region provenance preserved; receipt/SMS reconciliation and transfer/receivable/reversal semantics; unknown evidence and explicit coverage; accepted/as-of-only 30/60/90 features; protected audit separation; scoped/null assessment output; immutable review/history; offline default tests; no invented checkpoints/data/metrics/deployment proof.

The included synthetic intake/review/feature/assessment/correction flow is usable and tested through UI/API/MCP. Real trained financial extraction and linked-outcome validation remain blocked. Docker artifacts exist but their build/runtime is unverified on the current host.

Next human work: manual UI review/external MCP client invocation, Docker-capable validation, real datasets/annotations/checkpoints/outcomes, production security/operational readiness, explicitly authorized deployment and evidence-based proof recording. No handoff to another coding agent is required for the local implementation pass.
