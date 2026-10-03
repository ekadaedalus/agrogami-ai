# Responsible use

The current system computes descriptive evidence features; it does not predict repayment or automate a credit decision. Incomplete records can reflect access barriers, provider availability or documentation practices. Preserve unknowns, review reasons and contributor IDs throughout downstream work. Variability, missing receipts and sparse digital activity do not imply inability or unwillingness to repay.

Protected audit attributes are separately persisted with consent metadata and are excluded from baseline feature APIs. This separation is tested software behavior, not a fairness certification. Real-data use requires informed consent, lawful purpose, minimization, retention policy and access controls. No consent system, encryption/key management or reviewer authorization is implemented.

Human corrections preserve original records, candidates and lineage. Reviewer aliases are synthetic/demo-safe labels, not authentication. Ordinary logging accepts only a fixed operation vocabulary, UUID record ID and schema version. Never print raw inputs, private identifiers, environment secrets or database connection strings. Custom private-data/cache directories must remain outside source control (use ignored defaults or paths outside the repository).

Future evaluation must use consented annotated data, temporal splits and point-in-time evidence. Fairness analysis must examine subgroup coverage, calibration and errors with sufficient sample sizes; do not infer fairness from excluding protected attributes. Provide explanations and review/appeal paths before operational use. No real applicant outcome, model performance or fairness evidence exists here.
