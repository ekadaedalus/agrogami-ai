# Python 3.14 dependency verification

Actual runtime: Python 3.14.8, Windows. No interpreter downgrade occurred. Base and optional numerical packages were installed with `--only-binary=:all:`; no source build was used for runtime dependencies. Exact successful import evidence is recorded in dependency-compatibility.json. Second-pass historical suite: 223 passed, 3 heavy checkpoint tests deselected; current result is in build-status.md; pip check passed. Fairlearn 0.14.0 offline ThresholdOptimizer and native LightGBM/XGBoost TreeSHAP smoke tests passed. No active numerical/backend compatibility blocker remains.

The optional transformer stack was checked using:

```powershell
.\.venv\Scripts\python.exe -m pip install --dry-run --only-binary=:all: ".[models]"
```

Resolution succeeded for Transformers 5.18.0, torch 2.14.1 (cp314 Windows wheel), sentencepiece 0.2.2 (cp314 wheel) and accelerate 1.15.0. These packages/checkpoints were not installed or executed in this pass. This demonstrates wheel resolution only, not trained inference, training, Bangla recognition or end-to-end compatibility with a supplied financial artifact. Loader behavior is verified with fakes and local-manifest preflight tests. Optional heavy tests require explicit local checkpoints and cannot download them.

The initial sandbox could not connect to PyPI (`WinError 10013` socket permission). The same query/installation was rerun with approved network access and succeeded in resolving dependencies. Download interruptions/slow transfer are network conditions, not Python compatibility errors. Do not record them as Fairlearn incompatibility. Actual package import issues, if any, belong in the generated report with exact version and exception.

Fairlearn ThresholdOptimizer support is offline research only. Numerical rates have a compatible independent implementation; native Fairlearn and TreeSHAP smoke-test results must be read from the final verification record, not assumed from wheel availability.

Observed and resolved library interaction: XGBoost 3.4.1 defaults `enable_categorical=True`. With SHAP 0.52.0 and an interventional background this produced `NotImplementedError: Categorical split is not yet supported. You can still use TreeExplainer with feature_perturbation=tree_path_dependent.` The numeric-only risk interface now explicitly sets `enable_categorical=False` during fitting/loading. A separate reproduction confirmed the declared interventional/raw-margin explanation works with that setting; native regression tests verify additivity. No switch to a different explanation target/background was made.

Starlette 1.7.0 initially warned that `httpx` TestClient use is deprecated and recommends `httpx2`. The test dependency now follows that recommendation rather than suppressing the warning. This is not a Python downgrade or Fairlearn blocker.

## Local product dependencies

Streamlit 1.65.0, MCP SDK 1.30.0 and Markdown 3.11 were installed from wheels and actually imported/exercised on Python 3.14.8. Editable installation of .[test,local,trees,fairness] succeeded with isolated setuptools build metadata. The earlier no-build-isolation attempt failed because setuptools was not installed in the runtime environment; standard isolated installation resolved it. No interpreter downgrade or active UI/MCP compatibility blocker remains. Docker is absent, so container runtime compatibility is unverified.
