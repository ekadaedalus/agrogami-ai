"""Explicit opt-in local DeBERTa/TrOCR/LayoutLMv3 training. Run --help first."""
import argparse
import json
from pathlib import Path
from agrogami.extraction.training import train_local

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["deberta", "trocr", "layoutlmv3"], required=True)
    for name in ("base-checkpoint", "train-file", "evaluation-file", "data-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--epochs", type=int, default=1)
    args = vars(parser.parse_args())
    result = train_local(**args)
    print(json.dumps({"task": result["task"], "version": result["version"], "heldout_loss": result["heldout_loss"]}))
