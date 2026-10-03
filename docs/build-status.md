# Build status

Verified foundation pass: 2026-10-03 (Asia/Dhaka). Original project files were empty, with a pre-existing Python 3.14 virtual environment and editor settings. No .git directory existed. Existing directory names were preserved; downstream empty packages remain unimplemented.

Phases 0–7 are implemented: inspection; agent contract/configuration/documentation; canonical/candidate/provenance/review schemas; SQLAlchemy persistence; deterministic validation/reconciliation and correction lineage; 20 reproducible synthetic scenarios; 30/60/90-day features; unit/integration tests. No datasets, checkpoints, model outcomes, deployment URLs or proof were invented.

Complete default suite: `107 passed` on Python 3.14.8 / Windows. The final verification command is `.\.venv\Scripts\python.exe -m pytest -q`. Test files and subsystem evidence are listed in codex-handoff.md. Synthetic pipeline integration cases persist, reopen and compare all three window snapshots. No model downloads occur in the tests. Installation from pyproject.toml succeeded. Synthetic JSON export succeeded.

PostgreSQL DDL compilation is tested; live PostgreSQL execution is not. Coverage is caller-attested. This foundation has no production migrations, authenticated reviewer workflow, real-data validation or trained models. Claims register limits every claim to its evidence.

## ANTIGRAVITY HANDOFF

Implemented: immutable source/candidate/event storage, safe intake metadata/logging, review rules, scoped duplicates, receipt/SMS pairing, linked reversals, own-transfer and receivable semantics, settlement cap, cash-free daily balance snapshots, atomic corrections/history, separate protected audit attributes and deterministic as-of features with null/coverage/contributor metadata.

Tested: schema/configuration/privacy contracts; matching and ambiguity; balance known/unknown equations; cash exclusion and settlement; 30/60/90-day boundaries; future event/ingestion/correction exclusion; missing-day statistics; punctuality denominator/payment completeness; balance nulls and complete-history ratios; immutable/atomic persistence; all 20 synthetic pipeline cases.

Current commands (PowerShell, repository root):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/export_fixtures.py
```

Preserve Decimal money, aware UTC/as-of availability, append-only correction lineage, original candidates, explicit coverage and unknowns, and audit/underwriting separation. SQLAlchemy stores validated JSON envelopes with relational identity/lineage. Snapshot IDs are deterministic; random intake identifiers are not financial evidence. No downstream package name is evidence of implementation.

Known blockers: real evidence/consent, verified provider templates, annotations, model checkpoints and outcome data are absent. Live PostgreSQL needs a server/driver. Production auth/encryption/migrations and multi-version CI are not implemented. Git was not initialized.

Exact next phase: consented evidence acquisition and canonical annotation protocol, then verified deterministic provider/template ingestion adapters with candidate provenance and completeness validation. Evaluate those adapters before introducing OCR/transformer inference or any predictive training. ML, calibration/explanation/fairness, UI, MCP and deployment follow only with appropriate evidence and scope.

Read first: AGENTS.md; docs/codex-handoff.md; docs/architecture.md; docs/data-contract.md; docs/feature-dictionary.md; docs/claims-register.md; this file. docs/codex-handoff.md contains the detailed continuation contract.
