# Agrogami AI

Traceable underwriting from financial records traditional credit systems ignore

An explainable underwriting evidence and risk-audit workbench for thin-file credit.

## Product requirements

Turn mobile-money messages, informal ledger records, receipts, and bills into traceable financial evidence for thin-file credit assessment. Human reviewers inspect and corroborate financial records through an underwriting workflow backed by an immutable evidence ledger.

**Demo environment**

This demonstration uses synthetic, sample, or de-identified financial records. Assessment outputs shown here are illustrative and are not lending decisions or validated individual creditworthiness. Agrogami does not represent sample outputs as validated lending decisions. Real underwriting-performance and fairness claims require representative pre-application records linked to mature repayment outcomes.

Implemented: deterministic canonical ledger/features, candidate/model adapters, scoped research risk/calibration/explanation/fairness services, immutable snapshots, FastAPI, ten-page Streamlit application, synchronized project docs and authorized four-tool read-only Prism. Application/domain services are the sole source of financial logic.

Acceptance criteria: Decimal money and aware timestamps; original candidates and hash/span/region provenance preserved; receipt/SMS reconciliation and transfer/receivable/reversal semantics; unknown evidence and explicit coverage; accepted/as-of-only 30/60/90 features; protected audit separation; scoped/null assessment output; immutable review/history; offline default tests; no invented checkpoints/data/metrics/deployment proof.

Product presentation: lead with the product name and tagline, followed by supporting copy and a secondary demo notice. Keep API URL, Demo credential and Applicant UUID in collapsed Developer settings. Primary evidence views use readable states and reasons; Technical evidence retains UUIDs, full JSON, spans, hashes, parser/template metadata, machine codes and version links. Financial Profile adds four summaries from existing values above the unchanged 30/60/90-day Detailed underwriting evidence tables. Assessment withheld explains insufficient evidence and preserves null scores; missing evidence never becomes a low score. Navigation is Overview, Applicant Evidence, Evidence Review, Event Ledger, Financial Profile, Assessment, Explanation, Fairness & Evaluation, Audit Trail and Documentation.

The included synthetic intake/review/feature/assessment/correction flow is usable and tested through UI/API/MCP. Real trained financial extraction and linked-outcome validation remain blocked. Docker artifacts exist but their build/runtime is unverified on the current host.

Next human work: manual UI review/external MCP client invocation, Docker-capable validation, real datasets/annotations/checkpoints/outcomes, production security/operational readiness, explicitly authorized deployment and evidence-based proof recording. No handoff to another coding agent is required for the local implementation pass.
