from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def test_project_metadata_declares_supported_core_and_test_suite():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["requires-python"] == ">=3.11"
    requirements = project["project"]["dependencies"]
    assert any(r.startswith("pydantic>=2") for r in requirements)
    assert any(r.startswith("SQLAlchemy>=2") for r in requirements)
    assert project["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]


def test_private_defaults_and_secrets_are_excluded():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for path in (".env", ".venv/", "private_data/", "model_cache/", "*.db", "*.sqlite*"):
        assert path in ignored
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for variable in ("ENV", "DATABASE_URL", "PRIVATE_DATA_DIR", "MODEL_CACHE_DIR", "LOG_LEVEL",
                     "DEMO_MODE", "ENABLE_REAL_MODELS"):
        assert f"AGROGAMI_{variable}=" in example


def test_authoritative_agent_docs_and_handoff_exist():
    for name in ("AGENTS.md", "docs/PRD.md", "docs/architecture.md", "docs/data-contract.md",
                 "docs/feature-dictionary.md", "docs/responsible-ai.md", "docs/limitations.md",
                 "docs/claims-register.md", "docs/build-status.md", "docs/codex-handoff.md"):
        assert len((ROOT / name).read_text(encoding="utf-8").strip()) > 100
    assert "ANTIGRAVITY HANDOFF" in (ROOT / "docs/build-status.md").read_text(encoding="utf-8")
