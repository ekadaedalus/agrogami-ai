"""Evaluate explicitly supplied prediction JSONL; no invented model predictions."""
import argparse
import json
from pathlib import Path
from agrogami.extraction.bio import token_metrics, validate_bio
from agrogami.extraction.training import character_error_rate

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["deberta", "layoutlmv3", "trocr"], required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.predictions.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records or len({r["sample_id"] for r in records}) != len(records) or len({r["dataset_id"] for r in records}) != 1:
        raise ValueError("explicit unique evaluation sample/dataset IDs required")
    if args.task == "trocr":
        values = [character_error_rate(r["expected"], r["predicted"]) for r in records]
        observed = [v for v in values if v is not None]
        metrics = {"mean_sample_cer": sum(observed) / len(observed) if observed else None, "undefined_samples": values.count(None)}
    else:
        for record in records:
            validate_bio(record["expected"])
            validate_bio(record["predicted"])
        metrics = token_metrics([x for r in records for x in r["expected"]], [x for r in records for x in r["predicted"]])
    args.output.write_text(json.dumps({"dataset_id": records[0]["dataset_id"], "task": args.task, "metrics": metrics}, indent=2), encoding="utf-8")
