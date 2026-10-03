# Agrogami deterministic foundation

Typed financial evidence intake, canonical contracts, immutable SQLite storage, conservative reconciliation, human corrections and auditable 30/60/90-day features. All included data is synthetic. This package does not make lending decisions or execute models.

Python 3.11+; this pass was verified on Python 3.14.8 on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/export_fixtures.py
```

On other platforms use `.venv/bin/python` in place of the Windows executable. Copy `.env.example` to `.env` for local overrides. Settings reads it centrally; private data and model caches are ignored.

```python
from agrogami.config import Settings
from agrogami.storage import Store
from agrogami.fixtures import scenarios, fixture_sources, APPLICANT, T0, coverage
from agrogami.validation.rules import reconcile
from agrogami.features import build_all_windows

store = Store(Settings().database_url)
events = scenarios()["receipt_sms_same_payment"]
for source in fixture_sources(events):
    store.save(source)
for event in reconcile(events):
    store.save(event)
snapshots = build_all_windows(store.events(APPLICANT), applicant_id=APPLICANT,
                              t0=T0, coverage=coverage())
for snapshot in snapshots.values():
    store.save(snapshot)
store.engine.dispose()
```

This example uses a fresh database; inserts are immutable and repeated UUIDs are rejected. Coverage is explicit, never inferred from a transaction being present. Nulls and coverage reasons must remain visible to downstream consumers.

Start with [Codex Handoff](docs/codex-handoff.md), [Architecture](docs/architecture.md) and [Claims register](docs/claims-register.md). No Git repository was present when this implementation began; initialize/version it separately before collaboration.
