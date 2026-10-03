# Local research demonstration

## Project overview, problem and target users

Agrogami AI explores traceable alternative-credit evidence for researchers and human evidence reviewers working with mobile-money messages, bills and paper ledgers. Unstructured records can be incomplete and contradictory. Sparse activity or variable income does not establish inability to repay. This is not an autonomous lender.

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
2. Enter the reviewer credential in the sidebar, keep the generated applicant UUID and choose Intake / Samples, SYNTHETIC, External inflow. Submit the marked SMS.
3. Evidence Review shows original/normalized fields, parser/confidence and hash-linked spans. Corroborate synthetic ownership as external and append a reviewed version.
4. Event Ledger shows preserved versions; Feature Summary shows actual 30/60/90 outputs and null coverage-dependent ratios.
5. Assessment creates an honest unknown-coverage snapshot with null score; Explanation shows actual insufficient-evidence reasons.
6. Correct an accepted amount with a Decimal string and reason. Audit / Versions shows supersession and a fresh unscored assessment; old snapshots are unchanged.
7. Evaluation / Fairness requires an actual stored evaluation UUID. No fabricated charts exist. Optional Prism reads these same services.

## API, project docs, Agrogami Prism and CloudCamp usage

API localhost:8000; Swagger /api/docs; OpenAPI /api/openapi.json; project /docs. Streamlit localhost:8501. Prism localhost:8001/mcp has exactly four read-only authorized tools. CloudCamp is external guidance only and receives no product data. See backend-api.md and mcp.md.

## Development environment, tech stack and reproducibility

Tested Python 3.14.8 on Windows. VS Code is the supplied IDE; coding assistants are development tools only. No generative underwriting, RAG scoring, workflow orchestration platform, local LLM runtime or live lender integration is implemented. Pydantic v2, SQLAlchemy, FastAPI, NumPy/sklearn, Streamlit and official MCP SDK support the local prototype. README provides exact commands. Default tests are offline; live runtime verification launches isolated processes and cleans them up.

## Limitations and changelog

Foundation pass implemented deterministic contracts/ledger/features. Second pass added backend/research interfaces. Completion pass added UI/docs/Prism, end-to-end/protocol/UI tests, smoke/run helpers and Docker artifacts. Docker is unavailable on the verified host; container build/run is unverified. Production identity/isolation/migrations/crash recovery/retention and real financial datasets/checkpoints remain future work. No public URLs, videos, model metrics, fairness guarantees or external MCP proof are invented.
