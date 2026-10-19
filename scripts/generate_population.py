"""Generate the SYNTHETIC labelled borrower population and its RiskDataset splits."""
import argparse
import json
from pathlib import Path
from agrogami.synthetic import population as P
from agrogami.synthetic.ledger import next_assessment_time
from agrogami.synthetic.pipeline import generate, write_population

ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=P.DEFAULT_SEED)
    parser.add_argument("--n", type=int, default=P.DEFAULT_N)
    parser.add_argument("--workers", type=int, default=None, help="Worker processes (default: CPU count - 1)")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "synthetic")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict:
    args = parse_args(argv)
    if args.n < 50:
        raise SystemExit("--n must be at least 50 so each split holds both classes")
    records = generate(args.seed, args.n, next_assessment_time(), workers=args.workers)
    manifest = write_population(records, args.out, seed=args.seed, n=args.n)
    print(json.dumps({k: manifest[k] for k in ("generator_version", "seed", "n", "default_rate", "bridge", "splits")}, indent=2))
    return manifest


if __name__ == "__main__":
    main()
