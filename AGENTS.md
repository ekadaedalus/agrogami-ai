# Agent contract

This repository implements a deterministic evidence foundation for Agrogami. Read docs/codex-handoff.md, architecture.md, data-contract.md, feature-dictionary.md, claims-register.md and build-status.md before changes.

Preserve existing directory names. Python 3.11+, typed Python, Pydantic v2, Decimal money, aware timestamps, SQLAlchemy 2.x. Canonical events and candidates are immutable; corrections append versions with reviewer aliases and reasons. Never erase evidence or silently impute financial facts. Candidate originals are permanent.

Only accepted, available-as-of events enter features. Windows are [t0-window,t0). Missing observations are unknown, never zero. Own transfers and unsettled credit sales are not income. Cash-in/out do not establish external cash flow. Reversals cancel linked economic effects; receipt/SMS matches count once. Ambiguous matches require review. Incomplete balances and obligation denominators produce nulls. Protected audit attributes remain separate from underwriting features.

No raw SMS, documents, phone numbers, private identifiers, secrets or database URLs in logs. Use allowlisted UUIDs and versions. Private data stays ignored. Hashes establish byte integrity, not authenticity. All fixtures must be explicitly synthetic and reproducible.

Run python -m pytest before handoff. Update claims only with recorded evidence. Do not claim model inference/training, predictive performance, fairness, calibration, UI, MCP, deployment or demo proof. Downstream work requires explicit scope and real-data consent/annotations. Do not download models in default tests.
