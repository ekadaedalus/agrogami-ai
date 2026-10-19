# SYNTHETIC borrower population — data card

**Every record here is synthetic.** The borrowers, wallets, phone-like identifiers, TrxIDs and
default labels are invented. The labels are produced by the rule below and say **nothing about
any real person's repayment**. Models trained on this data are `SYNTHETIC_DEMO` artefacts for
demonstrating the pipeline; they are not validated underwriting models.

| Item | Value |
|---|---|
| Generator version | `synthetic-population-v1` (`src/agrogami/synthetic/population.py`) |
| Seed | `20261016` (default; `--seed` flag) |
| Borrowers | 2000 (`--n` flag) |
| History per borrower | 92 days of SMS-style wallet messages |
| SMS messages generated | 362018 |
| Events not accepted after review | 0 |
| Default rate (observed labels) | 15.50% |
| Latent default rate (before noise) | 11.65% |
| Label noise | 5% symmetric flips (85 labels flipped) |
| Bridge rows / exclusions | 2000 / 0 |
| Train / calibration / test | 1200 (186 defaults) / 400 (62) / 400 (62) |

## How records are produced

Each borrower draws latent traits: monthly digital receipts, receipt **stability**, business
**margin**, bill-payment **discipline**, activity level, an optional second wallet, and two
**unobserved** drivers (`hidden_shock`, a post-assessment adverse shock with probability 10%,
and `hidden_burden`, an off-ledger informal debt z-score). A wallet simulator turns the observable
traits into 92 days of messages in the strict `SYNTHETIC:` bKash-like /
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
z = -3.5
    + 1.2 * (0.66 - stability) / 0.15
    + 1.0 * (0.12 - margin) / 0.09
    + 0.9 * (0.84 - discipline) / 0.10
    + 2.0 * hidden_shock          # unobserved
    + 0.6 * hidden_burden        # unobserved
latent_default ~ Bernoulli(sigmoid(z))
label = latent_default, flipped with probability 0.05
```

Stability, margin and discipline are only seen through noisy features (inflow CV, net cash
flow, punctuality over three bills a month). The two hidden drivers and the label noise are never
observable, so no model can recover the rule perfectly; `metrics.json` reports how well the rule
itself ranks the noisy test labels as a reference.

## Model inputs and splits

`agrogami.risk.bridge` converts each borrower's 90-day `FeatureSnapshot` into a
`RiskDataset` row over external_inflow_total, external_outflow_total, net_external_cash_flow, inflow_cv, payment_punctuality, median_payment_delay_days, active_day_share. The full attested history is used
because 30 days is too short to reveal the traits: with three bills a month and daily receipt
noise, 30-day features track margin, stability and discipline far more weakly than 90-day ones. A snapshot with any null, non-scalar or
reason-flagged selected feature is excluded and listed in `bridge_exclusions.json`; nothing is
zero-filled. Splits are a seeded per-class shuffle (60/20/20). Latent traits are published in
`population.jsonl` for audit only and never enter the bridge.

## Files

`population.jsonl` (per-borrower label, traits, compact 30/60/90 features), `risk_train.json`,
`risk_calibration.json`, `risk_test.json`, `bridge_exclusions.json`, `generation_manifest.json`,
`metrics.json` ("synthetic recovery test"). Regenerate with
`python -m scripts.build_demo` or `python -m scripts.generate_population --seed 20261016 --n 2000`.
