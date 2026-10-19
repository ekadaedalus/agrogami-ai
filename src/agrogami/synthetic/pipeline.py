"""Population → RiskDataset splits → calibrated SYNTHETIC_DEMO models → recovery-test report."""
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import json
import os
from pathlib import Path
from uuid import UUID, uuid5, NAMESPACE_URL
import numpy as np
from agrogami.calibration.core import (CalibrationArtifact, Calibrator, ExperimentManifest, calibration_metrics,
                                       validate_evaluation)
from agrogami.datasets import DatasetIdentity, RiskDataset, contract_fingerprint, dataset_lineage
from agrogami.risk.bridge import MODEL_FEATURES, MODEL_WINDOW, snapshots_to_dataset, stratified_split
from agrogami.risk.models import (LogisticRiskModel, ModelArtifact, TreeHyperparameters, TreeRiskModel,
                                  ValidationScope)
from agrogami.schemas import FeatureSnapshot
from agrogami.synthetic import population as P

REPORT_TITLE = "Synthetic recovery test"
REPORT_CAVEAT = ("Labels are generated from synthetic latent traits by a documented rule; these metrics show how "
                 "much of that rule the pipeline recovers. They are not real repayment performance, underwriting "
                 "validation, calibration validity or fairness evidence.")
ALGORITHMS = ("logistic", "lightgbm", "xgboost")
FEATURE_DEFINITIONS = {
    "external_inflow_total": "Sum of verified external inflows in the model window (BDT)",
    "external_outflow_total": "Sum of verified external outflows plus their fees in the window (BDT)",
    "net_external_cash_flow": "External inflows minus fee-inclusive external outflows (BDT)",
    "inflow_cv": "Population SD of daily external inflow / (mean + 0.01 BDT) over attested complete days",
    "payment_punctuality": "Verified obligations paid by due date / verified obligations due in window",
    "median_payment_delay_days": "Median days paid after due date among verified paid obligations",
    "active_day_share": "Days with a verified effective transaction / window days",
}
DATA_FILES = {"train": "risk_train.json", "calibration": "risk_calibration.json", "test": "risk_test.json"}


def identity(seed: int, n: int) -> DatasetIdentity:
    return DatasetIdentity(dataset_id=f"SYNTHETIC-agrogami-population-{P.GENERATOR_VERSION}-seed{seed}-n{n}",
        target_definition="SYNTHETIC default label from documented latent-trait rule with label noise (data/synthetic/DATA_CARD.md)",
        scope="synthetic", limitations=("SYNTHETIC borrowers and labels; not real repayment outcomes",
            "Label rule includes unobserved drivers and 5% label noise by design",
            "Features from synthetic SMS through the real intake/ledger/feature code"))


def _process(task: tuple[int, int, datetime, int]) -> dict:
    return P.process_borrower(*task)


def generate(seed: int, n: int, t0: datetime, *, workers: int | None = None) -> list[dict]:
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    tasks = [(seed, index, t0, MODEL_WINDOW) for index in range(n)]
    if workers == 1:
        return [_process(task) for task in tasks]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_process, tasks, chunksize=8))


def write_population(records: list[dict], out: Path, *, seed: int, n: int) -> dict:
    """Bridge 30-day snapshots into seeded stratified splits and write deterministic artefacts."""
    out.mkdir(parents=True, exist_ok=True)
    window = records[0]["model_window"]
    rows = [(r["sample_id"], FeatureSnapshot.model_validate_json(r["model_snapshot"]), r["label"]) for r in records]
    bridged = snapshots_to_dataset(rows, identity=identity(seed, n), feature_names=MODEL_FEATURES, window_days=window)
    train, calibration, test = stratified_split(bridged.dataset, seed=seed)
    for name, data in zip(DATA_FILES, (train, calibration, test)):
        (out / DATA_FILES[name]).write_text(data.model_dump_json(), encoding="utf-8")
    with (out / "population.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        keep = set(MODEL_FEATURES) | {"coverage_days", "accepted_event_share", "liquidity_floor"}
        for r in records:
            windows = r["features"]
            row = {k: r[k] for k in ("sample_id", "applicant_id", "label", "latent_label", "label_flipped",
                                     "latent_default_probability", "traits", "sms_count", "current_event_status",
                                     "review_reasons")}
            row["features"] = {w: {k: v for k, v in values.items() if k in keep} for w, values in windows.items()}
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (out / "bridge_exclusions.json").write_text(json.dumps([e.model_dump() for e in bridged.exclusions], indent=2) + "\n",
                                                encoding="utf-8")
    labels = [r["label"] for r in records]
    manifest = {
        "generator_version": P.GENERATOR_VERSION, "seed": seed, "n": n, "history_days": P.HISTORY_DAYS,
        "label_rule": {"intercept": P.INTERCEPT, "weights": P.LABEL_WEIGHTS, "label_noise": P.LABEL_NOISE,
                       "unobserved_drivers": ["hidden_shock", "hidden_burden"]},
        "default_rate": round(sum(labels) / len(labels), 4),
        "latent_default_rate": round(sum(r["latent_label"] for r in records) / len(records), 4),
        "mean_latent_default_probability": round(float(np.mean([r["latent_default_probability"] for r in records])), 4),
        "labels_flipped_by_noise": sum(r["label_flipped"] for r in records),
        "sms_messages": sum(r["sms_count"] for r in records),
        "events_not_accepted": sum(r["current_event_status"]["NEEDS_REVIEW"] + r["current_event_status"]["REJECTED"] for r in records),
        "bridge": {"window_days": window, "features": list(MODEL_FEATURES), "rows": len(bridged.dataset.sample_ids),
                   "excluded": len(bridged.exclusions)},
        "splits": {name: {"rows": len(d.sample_ids), "defaults": sum(y == 1 for y in d.labels),
                          "fingerprint": contract_fingerprint(d)}
                   for name, d in zip(DATA_FILES, (train, calibration, test))},
    }
    (out / "generation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / "DATA_CARD.md").write_text(data_card(manifest, records), encoding="utf-8")
    return manifest


def load_splits(data_dir: Path) -> tuple[RiskDataset, RiskDataset, RiskDataset]:
    return tuple(RiskDataset.model_validate_json((data_dir / DATA_FILES[name]).read_text(encoding="utf-8"))
                 for name in DATA_FILES)  # type: ignore[return-value]


def _stable_id(kind: str, *parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "agrogami-synthetic-artifact:" + kind + ":" + ":".join(parts))


def fit_calibrated(algorithm: str, train: RiskDataset, calibration: RiskDataset, *, version: str,
                   hyperparameters: TreeHyperparameters, lr_c: float, method: str = "sigmoid",
                   window_days: int = MODEL_WINDOW):
    scope = ValidationScope.SYNTHETIC_DEMO
    model = (LogisticRiskModel.fit(train, scope=scope, version=version, c=lr_c) if algorithm == "logistic"
             else TreeRiskModel.fit(train, algorithm=algorithm, scope=scope, version=version, hyperparameters=hyperparameters))
    # Content-derived artifact identities keep reruns byte-comparable (uuid4 is the library default).
    # The artifact records the feature window it was trained on; assessments must use the same window.
    model.artifact = ModelArtifact.model_validate(model.artifact.model_dump() | {
        "artifact_id": _stable_id("model", version, contract_fingerprint(dataset_lineage(train))),
        "window_days": window_days})
    observed = [(sid, row, y) for sid, row, y in zip(calibration.sample_ids, calibration.values, calibration.labels) if y is not None]
    raw = [model.predict(dict(zip(calibration.feature_names, row))) for _, row, _ in observed]
    calibrator = Calibrator.fit(raw, [y for _, _, y in observed], [sid for sid, _, _ in observed], model=model.artifact,
                                dataset_id=calibration.identity.dataset_id, version=version + "-cal", method=method,
                                data=calibration)
    calibrator.artifact = CalibrationArtifact.model_validate(calibrator.artifact.model_dump() | {
        "artifact_id": _stable_id("calibrator", version, str(model.artifact.artifact_id))})
    return model, calibrator


def evaluate(model, calibrator: Calibrator, test: RiskDataset) -> dict:
    from sklearn.metrics import roc_auc_score
    manifest = ExperimentManifest.create(model.artifact, calibrator.artifact)
    validate_evaluation(test, model.artifact, calibrator.artifact, manifest)
    rows = [(row, y) for row, y in zip(test.values, test.labels) if y is not None]
    labels = [y for _, y in rows]
    raw = [model.predict(dict(zip(test.feature_names, row))) for row, _ in rows]
    calibrated = [calibrator.predict(p) for p in raw]
    result = {}
    for stage, p in (("raw", raw), ("calibrated", calibrated)):
        metrics = calibration_metrics(p, labels)
        result[stage] = {"auc": round(float(roc_auc_score(labels, p)), 4), "brier": round(metrics["brier"], 4),
                         "log_loss": round(metrics["log_loss"], 4)}
    result["test_rows"], result["test_defaults"] = len(labels), sum(labels)
    return result


def train_all(data_dir: Path, models_dir: Path, *, seed: int, hyperparameters: TreeHyperparameters, lr_c: float,
              primary: str = "lightgbm", method: str = "sigmoid", population: list[dict] | None = None) -> dict:
    train, calibration, test = load_splits(data_dir)
    window = json.loads((data_dir / "generation_manifest.json").read_text(encoding="utf-8"))["bridge"]["window_days"]
    models_dir.mkdir(parents=True, exist_ok=True)
    results, fitted = {}, {}
    for algorithm in ALGORITHMS:
        version = f"SYNTHETIC-demo-{algorithm}-{P.GENERATOR_VERSION}-seed{seed}"
        model, calibrator = fit_calibrated(algorithm, train, calibration, version=version,
                                           hyperparameters=hyperparameters, lr_c=lr_c, method=method,
                                           window_days=window)
        target = models_dir / algorithm
        target.mkdir(parents=True, exist_ok=False)
        model.save(target / ("model.json" if algorithm == "logistic" else "tree"))
        calibrator.save(target / "calibrator.json")
        (target / "experiment.json").write_text(ExperimentManifest.create(model.artifact, calibrator.artifact)
                                                .model_dump_json(indent=2), encoding="utf-8")
        results[algorithm] = evaluate(model, calibrator, test)
        fitted[algorithm] = (model, calibrator)
    if primary not in {"lightgbm", "xgboost"}:
        raise ValueError("the selected checkpoint must be a TreeSHAP-supported tree model")
    rng = np.random.default_rng(seed)
    picks = sorted(rng.choice(len(train.sample_ids), size=min(200, len(train.sample_ids)), replace=False).tolist())
    background = {"identity": f"{train.identity.dataset_id}:train-background-{len(picks)}-seed{seed}",
                  "rows": [list(train.values[i]) for i in picks], "feature_definitions": FEATURE_DEFINITIONS}
    (models_dir / primary / "shap_background.json").write_text(json.dumps(background), encoding="utf-8")
    report = {"title": REPORT_TITLE, "caveat": REPORT_CAVEAT, "dataset_id": test.identity.dataset_id,
              "split": "test", "window_days": window, "features": list(MODEL_FEATURES), "calibration_method": method,
              "selected_checkpoint": primary,
              "selection_rule": "Pre-declared primary (LightGBM, as in the project architecture); not chosen on test metrics",
              "hyperparameters": {"logistic_c": lr_c, "tree": hyperparameters.model_dump()}, "models": results}
    if population is not None:
        report["reference"] = oracle_reference(population, test)
    return report


def oracle_reference(population: list[dict], test: RiskDataset) -> dict:
    """How well the generating rule itself ranks the noisy test labels (an upper reference, not a model)."""
    from sklearn.metrics import roc_auc_score
    by_id = {r["sample_id"]: r for r in population}
    rows = [(by_id[sid], y) for sid, y in zip(test.sample_ids, test.labels) if y is not None]
    labels = [y for _, y in rows]
    full = [r["latent_default_probability"] for r, _ in rows]
    observable = [P.latent_logit(P.Traits(**(r["traits"] | {"hidden_shock": False, "hidden_burden": 0.0})))
                  for r, _ in rows]
    return {"latent_rule_auc": round(float(roc_auc_score(labels, full)), 4),
            "observable_part_of_rule_auc": round(float(roc_auc_score(labels, observable)), 4)}


def metrics_table(report: dict) -> str:
    lines = [f"{report['title']} — {report['dataset_id']} (test split, n={next(iter(report['models'].values()))['test_rows']})",
             f"{'model':<10} {'stage':<11} {'AUC':>7} {'Brier':>7} {'LogLoss':>8}"]
    for algorithm, result in report["models"].items():
        for stage in ("raw", "calibrated"):
            m = result[stage]
            mark = " *" if algorithm == report["selected_checkpoint"] and stage == "calibrated" else ""
            lines.append(f"{algorithm:<10} {stage:<11} {m['auc']:>7.4f} {m['brier']:>7.4f} {m['log_loss']:>8.4f}{mark}")
    if "reference" in report:
        ref = report["reference"]
        lines.append(f"reference: generating rule AUC {ref['latent_rule_auc']:.4f}; observable part only "
                     f"{ref['observable_part_of_rule_auc']:.4f}")
    lines.append("* selected checkpoint loaded by the backend. " + report["caveat"])
    return "\n".join(lines)


def data_card(manifest: dict, records: list[dict]) -> str:
    w, s = manifest["label_rule"]["weights"], manifest["splits"]
    return f"""# SYNTHETIC borrower population — data card

**Every record here is synthetic.** The borrowers, wallets, phone-like identifiers, TrxIDs and
default labels are invented. The labels are produced by the rule below and say **nothing about
any real person's repayment**. Models trained on this data are `SYNTHETIC_DEMO` artefacts for
demonstrating the pipeline; they are not validated underwriting models.

| Item | Value |
|---|---|
| Generator version | `{manifest['generator_version']}` (`src/agrogami/synthetic/population.py`) |
| Seed | `{manifest['seed']}` (default; `--seed` flag) |
| Borrowers | {manifest['n']} (`--n` flag) |
| History per borrower | {manifest['history_days']} days of SMS-style wallet messages |
| SMS messages generated | {manifest['sms_messages']} |
| Events not accepted after review | {manifest['events_not_accepted']} |
| Default rate (observed labels) | {manifest['default_rate']:.2%} |
| Latent default rate (before noise) | {manifest['latent_default_rate']:.2%} |
| Label noise | {manifest['label_rule']['label_noise']:.0%} symmetric flips ({manifest['labels_flipped_by_noise']} labels flipped) |
| Bridge rows / exclusions | {manifest['bridge']['rows']} / {manifest['bridge']['excluded']} |
| Train / calibration / test | {s['train']['rows']} ({s['train']['defaults']} defaults) / {s['calibration']['rows']} ({s['calibration']['defaults']}) / {s['test']['rows']} ({s['test']['defaults']}) |

## How records are produced

Each borrower draws latent traits: monthly digital receipts, receipt **stability**, business
**margin**, bill-payment **discipline**, activity level, an optional second wallet, and two
**unobserved** drivers (`hidden_shock`, a post-assessment adverse shock with probability 10%,
and `hidden_burden`, an off-ledger informal debt z-score). A wallet simulator turns the observable
traits into {manifest['history_days']} days of messages in the strict `SYNTHETIC:` bKash-like /
Nagad-like template: customer receipts, supplier payments, weekly wage transfers, cash-outs,
cash-in top-ups and three monthly bills, each with a running balance.

Every message goes through `ApplicationService.sms_intake` (intake hash, strict parser,
candidate, canonical event, validation, own-account registration, balance-continuity check) on a
per-borrower in-memory SQLite ledger. Bill due dates are appended as reviewer corrections
(`Store.correct`, alias `reviewer-synthetic-generator`), because the SMS template has no due date.
Coverage of SMS and obligations is attested for the full history; balance coverage is not, so
`liquidity_floor` stays null. Features come from the real feature engine at a UTC-midnight t0.

Generator caps (design choices, **not** provider facts; the templates and validators themselves
only reject amounts above Tk 1,000,000,000): at most Tk 25,000 per message and Tk 300,000 per
wallet per calendar month in each direction; balances never go negative.

## Labelling rule

```
z = {manifest['label_rule']['intercept']}
    + {w['instability']} * (0.66 - stability) / 0.15
    + {w['low_margin']} * (0.12 - margin) / 0.09
    + {w['indiscipline']} * (0.84 - discipline) / 0.10
    + {w['hidden_shock']} * hidden_shock          # unobserved
    + {w['hidden_burden']} * hidden_burden        # unobserved
latent_default ~ Bernoulli(sigmoid(z))
label = latent_default, flipped with probability {manifest['label_rule']['label_noise']}
```

Stability, margin and discipline are only seen through noisy features (inflow CV, net cash
flow, punctuality over three bills a month). The two hidden drivers and the label noise are never
observable, so no model can recover the rule perfectly; `metrics.json` reports how well the rule
itself ranks the noisy test labels as a reference.

## Model inputs and splits

`agrogami.risk.bridge` converts each borrower's {manifest['bridge']['window_days']}-day `FeatureSnapshot` into a
`RiskDataset` row over {', '.join(manifest['bridge']['features'])}. The full attested history is used
because 30 days is too short to reveal the traits: with three bills a month and daily receipt
noise, 30-day features track margin, stability and discipline far more weakly than 90-day ones. A snapshot with any null, non-scalar or
reason-flagged selected feature is excluded and listed in `bridge_exclusions.json`; nothing is
zero-filled. Splits are a seeded per-class shuffle (60/20/20). Latent traits are published in
`population.jsonl` for audit only and never enter the bridge.

## Files

`population.jsonl` (per-borrower label, traits, compact 30/60/90 features), `risk_train.json`,
`risk_calibration.json`, `risk_test.json`, `bridge_exclusions.json`, `generation_manifest.json`,
`metrics.json` ("synthetic recovery test"). Regenerate with
`python -m scripts.build_demo` or `python -m scripts.generate_population --seed {manifest['seed']} --n {manifest['n']}`.
"""
