"""The package and API expose one authoritative release version."""
from pathlib import Path
import tomllib


def test_package_and_api_version_are_synchronized():
    import agrogami
    from agrogami.api.app import HealthResponse, app
    metadata = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == HealthResponse().version == app.version
    assert agrogami.__version__ == app.version
