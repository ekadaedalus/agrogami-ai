"""Perturbation check: Rahim's Tk 500 receipt becomes Tk 5,000 with the reported balance unchanged.

Both versions run through candidate → event → features → probability → score in isolated
temporary ledgers using the built SYNTHETIC_DEMO checkpoint; the demo database is not modified.
"""
import argparse
from pathlib import Path
import tempfile
from agrogami.risk.loading import load_risk_components
from agrogami.synthetic.ledger import next_assessment_time
from agrogami.synthetic.rahim import perturbation_check
from agrogami.ui.formatting import humanize

ROOT = Path(__file__).resolve().parents[1]
SELECTED = ROOT / "private_data" / "demo" / "models" / "lightgbm"


def describe(label: str, result: dict) -> str:
    score = result["display_score"] if result["display_score"] is not None else "withheld"
    probability = (f"{result['calibrated_probability']:.4f}" if result["calibrated_probability"] is not None
                   else "withheld")
    flags = ", ".join(f"{code} ({humanize(code)})" for code in result["target_event_flags"]) or "none"
    return (f"{label:<7} receipt Tk {result['target_amount']} / reported balance Tk {result['target_reported_balance']}\n"
            f"        event status: {result['target_event_status']}; flags: {flags}\n"
            f"        assessment: {result['assessment_status']}; calibrated probability: {probability}; score: {score}")


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=SELECTED / "tree")
    parser.add_argument("--calibrator", type=Path, default=SELECTED / "calibrator.json")
    parser.add_argument("--background", type=Path, default=SELECTED / "shap_background.json")
    args = parser.parse_args(argv)
    if not args.model.exists():
        raise SystemExit("Model checkpoint missing; run `python -m scripts.build_demo` first")
    model, calibrator, explainer = load_risk_components(args.model, args.calibrator, args.background)
    with tempfile.TemporaryDirectory(prefix="agrogami-perturbation-") as scratch:
        result = perturbation_check(Path(scratch), next_assessment_time(), model=model, calibrator=calibrator,
                                    explanation_provider=explainer)
    print("Original SMS : " + result["original_sms"])
    print("Perturbed SMS: " + result["perturbed_sms"])
    print(describe("Before", result["before"]))
    print(describe("After", result["after"]))
    for reason in result["after"]["withheld_because"]:
        print("        " + reason)
    return result


if __name__ == "__main__":
    main()
