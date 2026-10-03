"""Record runtime/package verification without exposing filesystem paths or secrets."""
import importlib
from importlib.metadata import version, PackageNotFoundError
import json
import platform
import argparse
from pathlib import Path


def report() -> dict:
    modules = {"fastapi": "fastapi", "uvicorn": "uvicorn", "Pillow": "PIL", "numpy": "numpy",
               "starlette": "starlette", "httpx2": "httpx2", "numba": "numba", "llvmlite": "llvmlite",
               "scikit-learn": "sklearn", "scipy": "scipy", "lightgbm": "lightgbm", "xgboost": "xgboost",
               "shap": "shap", "fairlearn": "fairlearn", "transformers": "transformers", "torch": "torch",
               "streamlit": "streamlit", "mcp": "mcp", "Markdown": "markdown"}
    packages = {}
    for package, module in modules.items():
        try:
            installed = version(package)
        except PackageNotFoundError:
            packages[package] = {"status": "not_installed"}
            continue
        try:
            importlib.import_module(module)
            packages[package] = {"version": installed, "status": "imported"}
        except Exception as exc:
            packages[package] = {"version": installed, "status": "import_failed", "error_type": type(exc).__name__,
                                 "error": str(exc)}
    return {"python": platform.python_version(), "platform": platform.system(), "packages": packages}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = report()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
