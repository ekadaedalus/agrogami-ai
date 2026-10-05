"""Submission safeguards; no fixture here contains a usable credential."""
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_local_mcp_configuration_is_git_ignored():
    result = subprocess.run(["git", "check-ignore", "--no-index", ".vscode/mcp.json"],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", ".vscode/mcp.json"],
                             cwd=ROOT, capture_output=True, text=True, check=False)
    assert tracked.returncode != 0


@pytest.mark.parametrize("private_path", ["uploads", ".streamlit/secrets.toml", ".env",
                                         "private_data", "model_cache", ".vscode/mcp.json"])
def test_docker_context_excludes_private_runtime_paths(private_path):
    # Each required root has an explicit exclusion: audit it without Docker installed.
    patterns = {line.strip().rstrip("/") for line in (ROOT / ".dockerignore").read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#")}
    assert private_path in patterns


def test_mcp_example_exists_and_contains_no_literal_credentials():
    path = ROOT / ".vscode/mcp.json.example"
    assert path.is_file()
    example = json.loads(path.read_text(encoding="utf-8"))
    for server in example.get("servers", {}).values():
        for name, value in server.get("env", {}).items():
            if any(marker in name.upper() for marker in ("TOKEN", "SECRET", "PASSWORD", "API_KEY")):
                assert value.startswith("${") and value.endswith("}")
        for name, value in server.get("headers", {}).items():
            if name.lower() == "authorization":
                assert value.startswith("Bearer ${") and value.endswith("}")


def test_vscode_prism_example_uses_http_and_prompted_secret():
    example = json.loads((ROOT / ".vscode/mcp.json.example").read_text(encoding="utf-8"))
    prism = example["servers"]["agrogamiPrism"]
    assert prism["type"] == "http"
    assert prism["url"] == "http://127.0.0.1:8001/mcp"
    assert not {"command", "args", "env", "envFile"} & prism.keys()
    assert prism["headers"]["Authorization"] == "Bearer ${input:agrogami-prism-token}"
    prompt = next(item for item in example["inputs"] if item["id"] == "agrogami-prism-token")
    assert prompt["type"] == "promptString" and prompt["password"] is True
    assert "default" not in prompt
