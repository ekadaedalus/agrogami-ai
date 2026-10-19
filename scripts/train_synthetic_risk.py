"""Train, calibrate and test LR/LightGBM/XGBoost on the SYNTHETIC population ("synthetic recovery test")."""
import argparse
import json
from pathlib import Path
from agrogami.risk.models import TreeHyperparameters
from agrogami.synthetic import population as P
from agrogami.synthetic.pipeline import metrics_table, train_all

ROOT = Path(__file__).resolve().parents[1]


def add_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--lr-c", type=float, default=0.5, help="Logistic inverse L2 regularization (default 0.5)")
    parser.add_argument("--primary", choices=["lightgbm", "xgboost"], default="lightgbm",
                        help="Pre-declared checkpoint the backend loads (TreeSHAP requires a tree model)")
    parser.add_argument("--method", choices=["sigmoid", "isotonic"], default="sigmoid")
    defaults = TreeHyperparameters()
    for name, field in TreeHyperparameters.model_fields.items():
        parser.add_argument("--" + name.replace("_", "-"), type=type(field.default), default=getattr(defaults, name),
                            help=f"Tree hyperparameter (default {getattr(defaults, name)}, sized for ~2,000 rows)")


def hyperparameters(args: argparse.Namespace) -> TreeHyperparameters:
    return TreeHyperparameters(**{name: getattr(args, name) for name in TreeHyperparameters.model_fields})


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "synthetic")
    parser.add_argument("--models", type=Path, required=True, help="New output directory for model artefacts")
    parser.add_argument("--seed", type=int, default=P.DEFAULT_SEED)
    add_model_arguments(parser)
    args = parser.parse_args(argv)
    if args.models.exists():
        raise SystemExit("--models must be a new directory; existing artefacts are never replaced")
    population = [json.loads(line) for line in (args.data / "population.jsonl").read_text(encoding="utf-8").splitlines()]
    report = train_all(args.data, args.models, seed=args.seed, hyperparameters=hyperparameters(args), lr_c=args.lr_c,
                       primary=args.primary, method=args.method, population=population)
    (args.data / "metrics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(metrics_table(report))
    return report


if __name__ == "__main__":
    main()
