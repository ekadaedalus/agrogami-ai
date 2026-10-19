"""SYNTHETIC demo population, bridge, Rahim fixture, perturbation and demo UI regressions."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib
import json
from pathlib import Path
import runpy
import sys
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from agrogami.api.app import create_app
from agrogami.application import ApplicationService, OwnAccount
from agrogami.authorization import Role
from agrogami.datasets import DatasetIdentity, RiskDataset
from agrogami.explainability.core import explain_tree
from agrogami.risk.bridge import MODEL_FEATURES, snapshots_to_dataset, stratified_split
from agrogami.risk.models import TreeHyperparameters, TreeRiskModel, ValidationScope
from agrogami.schemas import (CanonicalEvent, FeatureSnapshot, FeatureValue, ReviewReason as R, Source,
                              TransactionDirection as D, TransactionType as T, ValidationStatus as V)
from agrogami.storage import Store
from agrogami.synthetic import population as P
from agrogami.synthetic.identities import ABSTENTION_APPLICANT_ID, RAHIM_APPLICANT_ID
from agrogami.synthetic.ledger import next_assessment_time
from agrogami.synthetic.pipeline import DATA_FILES, FEATURE_DEFINITIONS, fit_calibrated, load_splits
from agrogami.synthetic.rahim import BKASH_ALIAS, NAGAD_ALIAS, build_rahim, perturbed_messages, rahim_messages
from agrogami.synthetic.wallet import MONTHLY_WALLET_CAP, PER_TRANSACTION_CAP, PROVIDERS, period
from agrogami.ui.samples import synthetic_account
from agrogami.validation.continuity import continuity_break

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"
T0 = datetime(2026, 3, 1, tzinfo=timezone.utc)


def event(name: str, minute: int, *, amount="100", fee="0", balance="1000", direction=D.INFLOW,
          kind=T.RECEIPT, reference=None, **changes) -> CanonicalEvent:
    when = T0 - timedelta(days=2) + timedelta(minutes=minute)
    applicant = changes.pop("applicant_id", RAHIM_APPLICANT_ID)
    return CanonicalEvent.model_validate(dict(
        applicant_id=applicant, account_id=synthetic_account(applicant, PROVIDERS["bkash"]),
        source_id=uuid4(), source_type="MOBILE_MONEY_SMS", event_timestamp=when, ingestion_timestamp=when,
        transaction_type=kind, direction=direction, amount=Decimal(amount), fee=Decimal(fee), balance=Decimal(balance),
        provider=PROVIDERS["bkash"], transaction_reference=reference or "SYN-" + name,
        source_provenance={"source_hash": "0" * 64, "provider": PROVIDERS["bkash"], "template": "synthetic-provider-v1"})
        | changes)


# --- balance continuity -------------------------------------------------------------------

def test_continuity_verifies_chain_flags_break_and_never_guesses():
    first = event("a", 0, balance="1000")
    paid = event("b", 5, amount="250", fee="5", balance="745", direction=D.OUTFLOW, kind=T.PAYMENT)
    assert continuity_break(paid, [first]) is False
    wrong = event("c", 5, amount="2500", fee="5", balance="745", direction=D.OUTFLOW, kind=T.PAYMENT)
    assert continuity_break(wrong, [first]) is True
    # A later-arriving earlier message is checked against its stored successor as well.
    assert continuity_break(event("d", -5, amount="50", balance="1050"), [first]) is True
    # Unknown direction, no neighbour, or a same-reference copy are unverifiable, not breaks.
    assert continuity_break(event("e", 9, direction=D.UNKNOWN, kind=T.REVERSAL, balance="9"), [first]) is None
    assert continuity_break(event("f", 9, balance="1"), []) is None
    copy = event("a", 0, balance="1000", reference=first.transaction_reference)
    assert continuity_break(copy, [first]) is None
    unreported = CanonicalEvent.model_validate(event("g", 9).model_dump() | {"balance": None})
    assert continuity_break(unreported, [first]) is None


def test_registered_wallets_resolve_ownership_and_unregistered_accounts_stay_unknown(tmp_path):
    store = Store("sqlite:///" + (tmp_path / "own.db").as_posix())
    try:
        service = ApplicationService(store, tmp_path / "private")
        applicant = uuid4()
        bkash, nagad = PROVIDERS["bkash"], PROVIDERS["nagad"]
        text = ("SYNTHETIC: Send Money Tk 1,000.00. Fee Tk 5.00. TrxID SYN-OWN-1. Balance Tk 9,000.00. "
                "Counterparty {party}. Date 2026-01-02. Time 10:00:00+06:00.")
        unregistered = service.sms_intake(applicant_id=applicant, account_id=synthetic_account(applicant, bkash),
                                          text=text.format(party="SYN-W-NG"), provider=bkash)
        assert "AMBIGUOUS_OWNERSHIP" in unregistered.reasons
        service.register_accounts(applicant, (
            OwnAccount(account_id=synthetic_account(applicant, bkash), provider=bkash, wallet_alias="SYN-W-BK"),
            OwnAccount(account_id=synthetic_account(applicant, nagad), provider=nagad, wallet_alias="SYN-W-NG")),
            "SYNTHETIC attestation", "reviewer-test")
        own = service.sms_intake(applicant_id=applicant, account_id=synthetic_account(applicant, bkash),
                                 text=text.format(party="SYN-W-NG").replace("SYN-OWN-1", "SYN-OWN-2")
                                 .replace("9,000.00", "7,995.00"), provider=bkash)
        external = service.sms_intake(applicant_id=applicant, account_id=synthetic_account(applicant, bkash),
                                      text=text.format(party="SYN-SUPPLIER").replace("SYN-OWN-1", "SYN-OWN-3")
                                      .replace("10:00:00", "11:00:00").replace("9,000.00", "6,990.00"), provider=bkash)
        assert store.get(CanonicalEvent, own.event_id).ownership == "own"
        assert store.get(CanonicalEvent, external.event_id).ownership == "external"
        assert store.get(CanonicalEvent, external.event_id).validation_status == V.ACCEPTED
        elsewhere = service.sms_intake(applicant_id=applicant, account_id=uuid4(),
                                       text=text.format(party="SYN-X").replace("SYN-OWN-1", "SYN-OWN-4"), provider=bkash)
        assert store.get(CanonicalEvent, elsewhere.event_id).ownership == "unknown"
    finally:
        store.engine.dispose()


# --- bridge and split ---------------------------------------------------------------------

def snapshot(**overrides) -> FeatureSnapshot:
    features = {name: FeatureValue(value=Decimal("1")) for name in MODEL_FEATURES} | overrides
    return FeatureSnapshot(applicant_id=uuid4(), scoring_time=T0, window_days=90, features=features)


IDENTITY = DatasetIdentity(dataset_id="SYNTHETIC-bridge-test", target_definition="SYNTHETIC label",
                           scope="synthetic", limitations=("SYNTHETIC",))


def test_bridge_excludes_missing_or_flagged_features_and_never_zero_fills():
    rows = [("ok", snapshot(), 0),
            ("null", snapshot(payment_punctuality=FeatureValue(value=None, reasons=("complete_obligation_denominator_unknown",))), 1),
            ("flagged", snapshot(inflow_cv=FeatureValue(value=Decimal("0.4"), reasons=("CV uses attested complete days only",))), 0),
            ("absent", FeatureSnapshot(applicant_id=uuid4(), scoring_time=T0, window_days=90,
                                       features={"inflow_cv": FeatureValue(value=Decimal(1))}), 1),
            ("window", snapshot().model_copy(update={"window_days": 30}), 1)]
    result = snapshots_to_dataset(rows, identity=IDENTITY)
    assert result.dataset.sample_ids == ("ok",)
    assert result.dataset.values == ((1.0,) * len(MODEL_FEATURES),)
    reasons = {e.sample_id: e.reason for e in result.exclusions}
    assert reasons["null"].startswith("null:") and reasons["flagged"].startswith("reasons:")
    assert reasons["absent"] == "feature_absent" and reasons["window"] == "window_mismatch"
    assert 0.0 not in {v for row in result.dataset.values for v in row}


def test_stratified_split_is_seeded_disjoint_and_keeps_both_classes():
    labels = tuple([0] * 80 + [1] * 20)
    data = RiskDataset(identity=IDENTITY, sample_ids=tuple(f"S{i:03d}" for i in range(100)),
                       feature_names=("x",), values=tuple((float(i),) for i in range(100)), labels=labels)
    first, second = stratified_split(data, seed=3), stratified_split(data, seed=3)
    assert first == second and stratified_split(data, seed=4) != first
    ids = [set(part.sample_ids) for part in first]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2]) and sum(map(len, ids)) == 100
    assert [sum(part.labels) for part in first] == [12, 4, 4]


def test_tree_hyperparameters_reach_the_estimator_and_cli(tmp_path, monkeypatch):
    rng = np.random.default_rng(0)
    x = rng.normal(size=(120, 2))
    data = RiskDataset(identity=IDENTITY, sample_ids=tuple(f"S{i}" for i in range(120)), feature_names=("a", "b"),
                       values=tuple(map(tuple, x.tolist())), labels=tuple(int(v > 0) for v in x[:, 0]))
    model = TreeRiskModel.fit(data, algorithm="lightgbm", scope=ValidationScope.SYNTHETIC_DEMO, version="t",
                              hyperparameters=TreeHyperparameters(n_estimators=7, min_child_samples=5))
    assert model.estimator.booster_.num_trees() == 7
    train, calibration, _ = stratified_split(data, seed=1)
    paths = {}
    for name, part in (("train", train), ("cal", calibration)):
        paths[name] = tmp_path / f"{name}.json"
        paths[name].write_text(part.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["train_risk.py", "--training", str(paths["train"]), "--calibration", str(paths["cal"]),
        "--algorithm", "lightgbm", "--scope", "SYNTHETIC_DEMO", "--version", "SYNTHETIC-cli", "--output", str(tmp_path / "out"),
        "--n-estimators", "9", "--min-child-samples", "5", "--lr-c", "0.3"])
    runpy.run_path(str(ROOT / "scripts" / "train_risk.py"), run_name="__main__")
    assert TreeRiskModel.load(tmp_path / "out" / "tree").shap_estimator.num_trees() == 9


# --- population ---------------------------------------------------------------------------

def committed_rows() -> dict[str, tuple[tuple[float, ...], int]]:
    rows = {}
    for part in load_splits(DATA):
        rows.update({sid: (values, label) for sid, values, label in zip(part.sample_ids, part.values, part.labels)})
    return rows


def test_population_regenerates_committed_rows_through_real_intake():
    rows = committed_rows()
    t0 = next_assessment_time()
    for index in range(3):
        record = P.process_borrower(P.DEFAULT_SEED, index, t0)
        assert record["current_event_status"]["NEEDS_REVIEW"] == record["current_event_status"]["REJECTED"] == 0
        bridged = snapshots_to_dataset([(record["sample_id"], FeatureSnapshot.model_validate_json(record["model_snapshot"]),
                                         record["label"])], identity=IDENTITY)
        assert rows[record["sample_id"]] == (bridged.dataset.values[0], record["label"])
    messages = P.borrower_messages(P.rng_for(P.DEFAULT_SEED, 0, 2), P.draw_traits(P.rng_for(P.DEFAULT_SEED, 0, 0)), t0, 0)
    assert messages and all(m.text.startswith("SYNTHETIC: ") and m.trx.startswith("SYN") for m in messages)
    assert all(m.counterparty.startswith("SYN-") for m in messages)


def test_committed_population_card_rate_and_hidden_drivers():
    manifest = json.loads((DATA / "generation_manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == P.DEFAULT_SEED and manifest["n"] == P.DEFAULT_N
    assert manifest["generator_version"] == P.GENERATOR_VERSION
    assert 0.10 <= manifest["default_rate"] <= 0.20
    assert manifest["events_not_accepted"] == 0
    assert set(manifest["label_rule"]["unobserved_drivers"]).isdisjoint(MODEL_FEATURES)
    for name in DATA_FILES.values():
        data = RiskDataset.model_validate_json((DATA / name).read_text(encoding="utf-8"))
        assert data.identity.scope == "synthetic" and data.feature_names == MODEL_FEATURES
    card = " ".join((DATA / "DATA_CARD.md").read_text(encoding="utf-8").replace("**", "").split()).lower()
    for required in (P.GENERATOR_VERSION, str(P.DEFAULT_SEED), "label noise", "hidden_shock",
                     "say nothing about any real person's repayment", f"{manifest['default_rate']:.2%}"):
        assert required.lower() in card
    metrics = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["title"] == "Synthetic recovery test" and set(metrics["models"]) == {"logistic", "lightgbm", "xgboost"}
    assert all({"auc", "brier", "log_loss"} <= set(m["calibrated"]) for m in metrics["models"].values())


# --- Rahim --------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def trained():
    train, calibration, _ = load_splits(DATA)
    model, calibrator = fit_calibrated("lightgbm", train, calibration, version="SYNTHETIC-test-lightgbm",
                                       hyperparameters=TreeHyperparameters(), lr_c=0.5)
    background = [list(row) for row in train.values[:100]]
    provider = lambda features: explain_tree(model, features, background=background,
        background_identity="SYNTHETIC-test-background", feature_definitions=FEATURE_DEFINITIONS)
    return model, calibrator, provider


@pytest.fixture(scope="module")
def rahim(trained, tmp_path_factory):
    model, calibrator, provider = trained
    directory = tmp_path_factory.mktemp("rahim")
    store = Store("sqlite:///" + (directory / "rahim.db").as_posix())
    service = ApplicationService(store, directory / "private", model=model, calibrator=calibrator,
                                 explanation_provider=provider)
    t0 = next_assessment_time()
    built = build_rahim(service, t0)
    yield service, built, t0
    store.engine.dispose()


def test_rahim_is_outside_the_training_population():
    population = [json.loads(line) for line in (DATA / "population.jsonl").read_text(encoding="utf-8").splitlines()]
    assert str(RAHIM_APPLICANT_ID) not in {row["applicant_id"] for row in population}
    assert all(row["sample_id"].startswith("SYNTHETIC-POP-") for row in population)


def test_rahim_fixture_is_synthetic_within_caps_and_has_each_edge_case_once():
    t0 = next_assessment_time()
    messages = rahim_messages(t0)
    assert all(m.text.startswith("SYNTHETIC: ") and m.trx.startswith("SYN") and m.counterparty.startswith("SYN-")
               for m in messages)
    unique = [m for m in messages if m.tag != "duplicate_delivery"]
    assert max(m.amount for m in unique) <= PER_TRANSACTION_CAP and min(m.balance for m in unique) > 0
    totals = {}
    for m in unique:
        key = (m.wallet, period(t0, m.when), m.kind in {"Receipt", "Cash In", "Reversal"})
        totals[key] = totals.get(key, 0) + m.amount
    assert max(totals.values()) <= MONTHLY_WALLET_CAP
    tags = [m.tag for m in messages if m.tag and not m.tag.startswith("bill:")]
    assert sorted(tags) == sorted(["duplicate_original", "duplicate_delivery", "reversed_payment", "reversal",
                                   "own_transfer_out", "own_transfer_in", "perturbation_target"])
    receipts = [m.amount for m in unique if m.kind == "Receipt" and not m.tag.startswith("own")]
    assert sum(a <= 5000 for a in receipts) / len(receipts) > 0.9 and 2 <= sum(a > 10000 for a in receipts) <= 6
    original, duplicate = (m for m in messages if m.tag.startswith("duplicate"))
    assert original.text == duplicate.text
    assert perturbed_messages(messages)[2].balance == perturbed_messages(messages)[1].balance


def test_rahim_ledger_handles_duplicate_reversal_and_own_transfer(rahim):
    service, built, _ = rahim
    events = service.store.events(RAHIM_APPLICANT_ID)
    superseded = {e.supersedes_event_id for e in events if e.supersedes_event_id}
    current = [e for e in events if e.event_id not in superseded]
    assert all(e.validation_status == V.ACCEPTED for e in current)
    assert not any(R.AMBIGUOUS_OWNERSHIP in e.review_reason for e in events)
    ids = built["edge_case_event_ids"]
    by_id = {str(e.event_id): e for e in current}
    assert by_id[ids["own_transfer_out"]].ownership == by_id[ids["own_transfer_in"]].ownership == "own"
    reversal = next(e for e in current if e.transaction_type == T.REVERSAL)
    assert reversal.direction == D.INFLOW and str(reversal.reversal_of_event_id) == ids["reversed_payment"]
    assert all(service.store.get(Source, e.source_id).synthetic for e in current)
    f90 = built["snapshots"][90].features
    contributors = {str(i) for i in f90["external_inflow_total"].contributing_event_ids}
    # The duplicate SMS contributes exactly once; own transfers never enter external cash flow.
    assert len({ids["duplicate_original"], ids["duplicate_delivery"]} & contributors) == 1
    assert not ({ids["own_transfer_in"], ids["own_transfer_out"]} & contributors)
    messages = rahim_messages(built["assessment"].assessment_time)
    expected_inflow = sum(m.amount for m in messages if m.kind == "Receipt" and m.tag not in
                          {"duplicate_delivery", "own_transfer_in"} and m.when >= built["assessment"].assessment_time - timedelta(days=90))
    assert f90["external_inflow_total"].value == expected_inflow
    expected_outflow = sum(m.amount + m.fee for m in messages if m.kind in {"Payment", "Send Money"} and m.tag not in
                           {"reversed_payment", "own_transfer_out"} and m.when >= built["assessment"].assessment_time - timedelta(days=90))
    assert f90["external_outflow_total"].value == expected_outflow


@pytest.mark.parametrize("window", [30, 60, 90])
def test_rahim_core_features_available_in_every_window(rahim, window):
    _, built, _ = rahim
    features = built["snapshots"][window].features
    for name in ("net_external_cash_flow", "inflow_cv", "payment_punctuality"):
        assert features[name].value is not None and features[name].reasons == ()
    assert features["coverage_days"].value == window and features["accepted_event_share"].value == 1
    assert features["net_external_cash_flow"].value > 0


def test_rahim_scored_through_assessment_path_with_treeshap(rahim, trained):
    service, built, t0 = rahim
    assessment = built["assessment"]
    assert assessment.status == "ILLUSTRATIVE" and assessment.model_validation_scope == "SYNTHETIC_DEMO"
    assert assessment.feature_snapshot.window_days == assessment.model_artifact.window_days == 90
    assert 0 < assessment.calibrated_probability < 1 and 300 <= assessment.display_score <= 850
    features = {name: float(assessment.feature_snapshot.features[name].value) for name in MODEL_FEATURES}
    assert assessment.calibrated_probability == pytest.approx(trained[1].predict(trained[0].predict(features)))
    assert set(assessment.explanation_metadata.contributions) == set(MODEL_FEATURES)
    assert service.records.get(type(assessment), assessment.assessment_id) == assessment
    assert {str(s.snapshot_id) for s in service.store.snapshots(RAHIM_APPLICANT_ID)} == {
        str(s.snapshot_id) for s in built["snapshots"].values()}


def test_perturbation_cli_flags_balance_and_withholds_score(trained, tmp_path, capsys):
    model, calibrator, _ = trained
    (tmp_path / "m").mkdir()
    model.save(tmp_path / "m" / "tree")
    calibrator.save(tmp_path / "m" / "calibrator.json")
    background = {"identity": "SYNTHETIC-test", "rows": [list(r) for r in load_splits(DATA)[0].values[:50]],
                  "feature_definitions": FEATURE_DEFINITIONS}
    (tmp_path / "m" / "bg.json").write_text(json.dumps(background), encoding="utf-8")
    cli = importlib.import_module("scripts.perturbation_check")
    result = cli.main(["--model", str(tmp_path / "m" / "tree"), "--calibrator", str(tmp_path / "m" / "calibrator.json"),
                       "--background", str(tmp_path / "m" / "bg.json")])
    before, after = result["before"], result["after"]
    assert before["target_amount"] == "500.00" and after["target_amount"] == "5000.00"
    assert before["target_reported_balance"] == after["target_reported_balance"]
    assert before["assessment_status"] == "ILLUSTRATIVE" and 300 <= before["display_score"] <= 850
    assert before["target_event_status"] == "ACCEPTED" and before["target_event_flags"] == []
    assert after["target_event_status"] == "NEEDS_REVIEW" and "BALANCE_INCONSISTENCY" in after["target_event_flags"]
    assert after["assessment_status"] == "NEEDS_REVIEW"
    assert after["display_score"] is after["calibrated_probability"] is None
    printed = capsys.readouterr().out
    assert "BALANCE_INCONSISTENCY (Balance does not reconcile)" in printed and "score: withheld" in printed
    assert f"score: {before['display_score']}" in printed


# --- API and UI ---------------------------------------------------------------------------

def test_stored_snapshot_endpoint_returns_attested_windows(rahim):
    service, built, _ = rahim
    with TestClient(create_app(service, tokens={"view": Role.viewer})) as client:
        response = client.get(f"/api/v1/applicants/{RAHIM_APPLICANT_ID}/feature-snapshots",
                              headers={"X-Agrogami-Token": "view"})
        assert response.status_code == 200
        assert sorted(item["window_days"] for item in response.json()) == [30, 60, 90]
        assert client.get(f"/api/v1/applicants/{uuid4()}/feature-snapshots", headers={"X-Agrogami-Token": "view"}).json() == []


def test_ui_demo_selector_shows_rahims_stored_profile_and_score(rahim, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from agrogami.ui.api_client import APIClient
    service, built, _ = rahim
    original = APIClient.__init__
    with TestClient(create_app(service)) as transport:
        def initialize(self, base_url, token="", **kwargs):
            original(self, base_url, token, transport)
        monkeypatch.setattr(APIClient, "__init__", initialize)
        app = AppTest.from_file(str(ROOT / "src" / "agrogami" / "ui" / "app.py"), default_timeout=30).run()
        assert app.sidebar.selectbox[0].value == "Custom applicant UUID"
        app.sidebar.selectbox[0].set_value("Rahim — synthetic furniture workshop (scored)").run()
        app.sidebar.radio[0].set_value("Financial Profile").run()
        assert not app.exception and not app.error
        metrics = {item.label: item.value for item in app.metric}
        assert metrics["Evidence coverage"] == "Observed" and metrics["Payment history"] == "Available"
        for table in app.dataframe:
            rows = {row["Underwriting measure"]: row["Value"] for row in table.value.to_dict("records")}
            for label in ("Net external cash flow", "Inflow variability", "Payment punctuality"):
                assert not rows[label].startswith("Unavailable")
            assert rows["Coverage days"] in {"30", "60", "90"}
        app.sidebar.radio[0].set_value("Assessment").run()
        assert not app.exception and not app.error
        assert app.session_state["assessment_id"] == str(built["assessment"].assessment_id)
        assert {item.label: item.value for item in app.metric}["Illustrative Project Score"] == str(built["assessment"].display_score)
        app.sidebar.radio[0].set_value("Explanation").run()
        assert not app.exception and "TreeSHAP reason codes" in [item.value for item in app.subheader]
        # Switching applicant drops Rahim's assessment; this store holds no abstention-applicant records.
        app.sidebar.selectbox[0].set_value("Abstention demo — insufficient evidence").run()
        assert not app.exception
        assert app.session_state["applicant"] == str(ABSTENTION_APPLICANT_ID)
        assert "assessment_id" not in app.session_state
