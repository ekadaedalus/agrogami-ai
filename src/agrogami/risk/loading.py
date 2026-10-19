"""Load explicitly supplied local risk artifacts exactly as the backend does at startup."""
import json
from pathlib import Path
from typing import Callable
from agrogami.calibration.core import Calibrator
from agrogami.explainability.core import TreeExplanation, explain_tree
from agrogami.risk.models import LogisticRiskModel, TreeRiskModel, RiskModel, ValidationScope


def load_risk_components(model_path: Path, calibrator_path: Path, background_path: Path | None = None, *,
                         enable_real_models: bool = False
                         ) -> tuple[RiskModel, Calibrator, Callable[[dict[str, float]], TreeExplanation] | None]:
    model = TreeRiskModel.load(model_path) if model_path.is_dir() else LogisticRiskModel.load(model_path)
    if model.artifact.scope != ValidationScope.SYNTHETIC_DEMO and not enable_real_models:
        raise RuntimeError("Non-synthetic local artifacts require explicit research mode")
    calibrator = Calibrator.load(calibrator_path)
    explanation_provider = None
    if background_path:
        if not isinstance(model, TreeRiskModel):
            raise RuntimeError("TreeSHAP background requires a supported tree model")
        background = json.loads(background_path.read_text(encoding="utf-8"))
        tree = model
        explanation_provider = lambda features: explain_tree(tree, features, background=background["rows"],
            background_identity=background["identity"], feature_definitions=background["feature_definitions"])
    return model, calibrator, explanation_provider
