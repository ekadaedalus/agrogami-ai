"""Run after installing package: python scripts/export_fixtures.py."""
import json
from pathlib import Path
from agrogami.fixtures import scenarios

if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "sample_data" / "synthetic_events.json"
    target.write_text(json.dumps({"synthetic": True, "scenarios": {
        name: [e.model_dump(mode="json") for e in events] for name, events in scenarios().items()
    }}, indent=2), encoding="utf-8")
