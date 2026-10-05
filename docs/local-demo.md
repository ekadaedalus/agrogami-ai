# Agrogami AI

Traceable underwriting from financial records traditional credit systems ignore

An explainable underwriting evidence and risk-audit workbench for thin-file credit.

**Demo environment**

This demonstration uses synthetic, sample, or de-identified financial records. Assessment outputs shown here are illustrative and are not lending decisions or validated individual creditworthiness.

## Project overview, problem and target users

Turn mobile-money messages, informal ledger records, receipts, and bills into traceable financial evidence for thin-file credit assessment. Agrogami AI supports human evidence reviewers and risk auditors examining these records. Unstructured records can be incomplete and contradictory. Sparse activity or variable income does not establish inability to repay. This is not an autonomous lender.

## Current scope and implemented vs planned

Implemented locally: deterministic foundation, extraction/model/governance interfaces, FastAPI, Streamlit, synchronized docs and read-only Prism. Actual trained financial extraction checkpoints and linked-outcome validation remain blocked. Public deployment, proof links and external MCP-client reuse are PLANNED.

## Architecture and evidence boundary

Evidence → Candidates → Validation & Reconciliation → Canonical Event Ledger → Features → Risk → Calibration → Explanation → Fairness/Policy → Immutable Snapshot. Only accepted available-as-of canonical events contribute. No raw OCR/model output, UI, API or MCP independently calculates financial facts or risk. Decimal money, aware timestamps and original source spans/regions remain authoritative. Hashes establish byte integrity, not authenticity.

## Document and SMS processing

Exact marked synthetic bKash-like/Nagad-like templates preserve amount/fee/balance distinctions and source spans. They are not production provider integrations. Raster preprocessing and local TrOCR/LayoutLMv3/DeBERTa adapters exist; absent checkpoints mean no model inference. Candidate originals and confidence/provenance remain visible to authorized review. PDF/multipage/word segmentation remain limitations.

## Validation, features and review/abstention

Receipt/SMS represent one payment; linked reversals cancel; own transfers and unsettled khata credit sales are excluded. Unknown ownership/amount/template routes to review. Features use half-open 30/60/90 windows with explicit coverage and contributor IDs. Missing observations stay unknown. Missing receipt is not lateness. NEEDS_REVIEW/INSUFFICIENT_EVIDENCE and null scores are appropriate demo outcomes.

## Risk, calibration, display mapping and TreeSHAP

LightGBM primary, regularized logistic baseline and XGBoost challenger retain dataset target and validation scope. Public benchmarks do not validate Agrogami borrower underwriting. Calibration uses disjoint holdouts. The project-specific 300–850 score is not FICO, bureau-equivalent or approval; scaling does not create calibration. TreeSHAP explains raw model margin, not causality or calibrated-probability contribution. Controlled reasons require observed evidence.

## Fairness, responsible AI and privacy

Protected attributes remain separate offline audit inputs; never inferred or baseline features. Only actual aggregate reports are displayed. No representative linked borrower outcomes have been evaluated. Fairlearn optimization is offline research, not future parity. Private source bytes use UUID filenames and ignored storage; intentional reviewer displays are distinct from logs. Demo roles are local dataset-wide access, not production isolation.

## Data sources and provenance

Included records/templates are SYNTHETIC. Public benchmark identity, original target and limitations remain separate. No automatic downloads or unrelated-data fusion create end-to-end validation. Original candidates/events/snapshots remain recoverable after corrections. Complete coverage requires actual verified evidence, not event presence.

## Demo walkthrough

1. Install local/test extras and configure a reviewer secret in ignored .env; start API and UI.
2. Expand Developer settings in the sidebar to enter the reviewer credential. API URL and Applicant UUID are in the same collapsed section; keep the generated applicant UUID. Choose Applicant Evidence, SYNTHETIC, External inflow and submit the marked SMS.
3. Evidence Review leads with Needs review, Ownership not confirmed, the actual amount and the marked synthetic source. Technical evidence retains original/normalized JSON, UUIDs, parser/template versions, confidence, SHA-256, span_start/span_end and audit codes such as AMBIGUOUS_OWNERSHIP. Corroborate synthetic ownership as external and append a reviewed version.
4. Event Ledger shows preserved versions. Financial Profile summarizes verified inflow, evidence coverage, payment history and balance history from the existing backend values. Detailed underwriting evidence retains the full 30/60/90-day tables and null coverage-dependent ratios, with readable measure labels and shortened event identifiers. Exact keys and full identifiers remain in Technical evidence. A sample inflow never establishes complete cash flow or payment/balance histories.
5. In Assessment, select **Assess available evidence** to create an unknown-coverage snapshot, or expand **Load assessment** to inspect an existing one. For INSUFFICIENT_EVIDENCE, the primary result is **Assessment withheld — Insufficient evidence**, with a null score. Explain the actual missing histories and artifact limitations; retain system state, reason codes, scope and full snapshot in Technical evidence. Explanation shows the stored evidence reasons, or prompts the user to run or load an assessment when none is selected.
6. Correct an accepted amount with a Decimal string and reason. Audit Trail preserves supersession and a fresh unscored assessment; old snapshots are unchanged and remain inspectable in Technical evidence.
7. Fairness & Evaluation retains the representative-outcomes limitation; **Advanced lookup** holds the optional stored evaluation UUID. No fabricated charts exist. Optional Prism reads these same services.

The full navigation is Overview, Applicant Evidence, Evidence Review, Event Ledger, Financial Profile, Assessment, Explanation, Fairness & Evaluation, Audit Trail and Documentation. Present the workflow before opening developer settings or technical drill-down; those details remain available throughout review.

The full Agrogami AI hero appears only on Overview. Other pages use a title and one helper line. A compact light-amber demo notice remains visible, while only the Deploy button and heading link anchors are hidden. The Streamlit header, toolbar and sidebar collapse/expand controls remain visible. Evidence Review uses **Review candidate evidence** for its lookup. Empty Event Ledger and Audit Trail views prompt the user to add and review evidence; full UUIDs, hashes and JSON remain available in collapsed Technical evidence.

## API, project docs, Agrogami Prism and CloudCamp usage

API localhost:8000; Swagger /api/docs; OpenAPI /api/openapi.json; project /docs. Streamlit localhost:8501. Prism localhost:8001/mcp has exactly four read-only authorized tools. CloudCamp is external guidance only and receives no product data. See backend-api.md and mcp.md.

## Development environment, tech stack and reproducibility

Tested Python 3.14.8 on Windows. VS Code is the supplied IDE; coding assistants are development tools only. No generative underwriting, RAG scoring, workflow orchestration platform, local LLM runtime or live lender integration is implemented. Pydantic v2, SQLAlchemy, FastAPI, NumPy/sklearn, Streamlit and official MCP SDK support the local workbench. README provides exact commands. Default tests are offline; live runtime verification launches isolated processes and cleans them up.

## Limitations and changelog

Foundation pass implemented deterministic contracts/ledger/features. Second pass added backend/research interfaces. Completion pass added UI/docs/Prism, end-to-end/protocol/UI tests, smoke/run helpers and Docker artifacts. Docker is unavailable on the verified host; container build/run is unverified. Production identity/isolation/migrations/crash recovery/retention and real financial datasets/checkpoints remain future work. No public URLs, videos, model metrics, fairness guarantees or external MCP proof are invented.
