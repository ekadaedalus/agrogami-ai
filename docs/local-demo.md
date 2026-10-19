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

## Scored synthetic demo: Rahim and the abstention applicant

`.\.venv\Scripts\python.exe -m scripts.build_demo` rebuilds everything from scratch (about 10 minutes on 12 cores):

1. A seeded population of 2,000 SYNTHETIC microbusiness borrowers (`--seed`, `--n`). Every message runs through `ApplicationService.sms_intake` on a per-borrower in-memory ledger, and features come from the real feature engine. Labels come from a documented latent-trait rule with unobserved drivers and 5% label noise. See `data/synthetic/DATA_CARD.md`.
2. The model uses the 90-day window: 30 days proved too short to reveal the traits, as recorded in the data card. The model artifact records `window_days=90`, so a scored API assessment must request `window_days: 90`; other windows are rejected as a schema/window mismatch rather than silently rescored. The snapshot → RiskDataset bridge excludes, and never zero-fills, any null or reason-flagged feature. A seeded stratified 60/20/20 split follows; LR, LightGBM and XGBoost are trained, sigmoid-calibrated on the calibration split, and reported on the test split as the **synthetic recovery test** (`data/synthetic/metrics.json`). The pre-declared LightGBM checkpoint, its calibrator and a TreeSHAP background are written to `private_data/demo/models/lightgbm/`.
3. A fresh demo ledger, `private_data/demo/agrogami-demo.db`, holds:
   - Rahim (`600bbe3a-8b59-52ab-99d1-dc12d222b438`), scored through `ApplicationService.assessment`.
   - The abstention applicant (`fcba6da1-0b92-4a08-a776-664830b25a37`), recreated with its fixed UUID through the same Tk 100 flow as `prepare_demo` and still INSUFFICIENT_EVIDENCE.

   `private_data/agrogami.db` and earlier `synthetic_demo` scenarios are never touched.

To serve the demo, start the API with `.\scripts\run_demo_api.ps1` and the UI with `.\scripts\run_ui.ps1`. The launcher applies `private_data/demo/backend.env` (demo database, private directory, LightGBM checkpoint, calibrator, TreeSHAP background) to the API process only, and `/ready` then reports `risk: true`. `.env` is deliberately left alone: the default-startup test asserts that a plain `.env` loads no risk model. In the sidebar, **Demo applicant** switches between Rahim, the abstention applicant and a custom UUID. For a demo applicant, Financial Profile shows the stored 30/60/90-day snapshots with their attested coverage, and Assessment/Explanation open the latest stored assessment with TreeSHAP reason codes.

Rahim is a fictional Dhaka furniture-workshop owner with two registered SYNTHETIC wallets and 92 days of messages with running balances. His history contains exactly one duplicate SMS (same TrxID twice), one supplier payment with a reviewer-linked reversal, and one own bKash-like → Nagad-like transfer. Bill due dates are reviewer-corroborated, because the SMS template carries none. His assessment time is the next UTC midnight: complete-day coverage needs a midnight boundary after all evidence was recorded. Message dates shift with the build day; amounts, features, probability and score do not. Liquidity floor stays unavailable, because it requires one daily closing balance on a single account.

`.\.venv\Scripts\python.exe -m scripts.perturbation_check` changes Rahim's Tk 500 receipt to Tk 5,000 while keeping the reported balance. It then runs candidate → event → features → probability → score in temporary ledgers and prints the BALANCE_INCONSISTENCY flag and the score before and after; after the change, the score is withheld. Synthetic recovery metrics and Rahim's score are synthetic demonstrations, not validated underwriting, calibration or fairness evidence.

## API, project docs, Agrogami Prism and CloudCamp usage

API localhost:8000; Swagger /api/docs; OpenAPI /api/openapi.json; project /docs. Streamlit localhost:8501. Prism localhost:8001/mcp has exactly four read-only authorized tools. CloudCamp is external guidance only and receives no product data. See backend-api.md and mcp.md.

## Development environment, tech stack and reproducibility

Tested Python 3.14.8 on Windows. VS Code is the supplied IDE; coding assistants are development tools only. No generative underwriting, RAG scoring, workflow orchestration platform, local LLM runtime or live lender integration is implemented. Pydantic v2, SQLAlchemy, FastAPI, NumPy/sklearn, Streamlit and official MCP SDK support the local workbench. README provides exact commands. Default tests are offline; live runtime verification launches isolated processes and cleans them up.

## Limitations and changelog

Foundation pass implemented deterministic contracts/ledger/features. Second pass added backend/research interfaces. Completion pass added UI/docs/Prism, end-to-end/protocol/UI tests, smoke/run helpers and Docker artifacts. Docker is unavailable on the verified host; container build/run is unverified. Production identity/isolation/migrations/crash recovery/retention and real financial datasets/checkpoints remain future work. No public URLs, videos, model metrics, fairness guarantees or external MCP proof are invented.
