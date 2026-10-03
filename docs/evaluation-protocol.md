# Evaluation protocol boundary

Current evaluation is deterministic unit/integration testing, including all synthetic scenarios and as-of leakage cases. See codex-handoff.md for actual results. No model or real-data benchmark has been run.

Before downstream models: obtain consented evidence, annotate canonical facts and uncertain fields with source locations, validate inter-reviewer consistency, define temporal train/validation/test splits and preserve availability timestamps. Evaluate extraction independently from reconciliation and predictive performance. Only then evaluate calibration, errors, coverage and protected-group fairness with adequate data. Record actual versions, seeds and results; never use invented numbers or a synthetic fixture score as predictive evidence.
