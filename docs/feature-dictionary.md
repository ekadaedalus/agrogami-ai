# Feature dictionary v1.0

All windows are 30, 60 or 90 days: `t0-window <= event_time < t0`. Only accepted current versions known before t0 contribute. Linked duplicates and full reversals have no additional economic effect. Own transfers, credit sales/receivables/payables, and unproven cash-in/out are excluded from external flows. Credit settlement must link a prior accepted receivable; it adds cash only at settlement time, with cumulative settlement capped at the sale amount.

Every value includes contributing_event_ids and coverage/review reasons. Cash totals are totals of verified evidence, not estimates of complete real cash flow. With no qualifying events and incomplete coverage they are null; with an explicitly complete observed window, zero is known. Unknown days are never inserted into daily statistics. Contributor IDs include coverage evidence where relevant and reversal records when cancellation affected an in-window original. Source duplicates remain in evidence coverage counts but contribute once to economic totals.

| Feature | Definition / null behavior |
|---|---|
| external_inflow_total | Sum verified external inflows; excludes inflow fees under v1 flow convention |
| external_outflow_total | Sum verified external outflows plus separately recorded fees |
| net_external_cash_flow | Inflows minus fee-inclusive outflows; partial evidence labeled incomplete |
| inflow_cv | Population SD of daily external inflow divided by mean + epsilon; only explicitly complete observed UTC days, null if none |
| payment_punctuality | Verified paid-by-due obligations / verified obligations due in window; null if complete schedule or payment record unavailable or denominator empty |
| median_payment_delay_days | Median max(0,payment_date-due_date) among verified paid obligations; null for unknown schedule/payment record or no payments |
| liquidity_floor | Linear-interpolated Q0.10(daily closing balance) / arithmetic mean; requires one account, exactly one accepted closing value per day and complete attested window; null for incomplete/negative/nonpositive denominator |
| observed_minimum_balance | Minimum verified observed balance retained even with incomplete history; null if no observations |
| turnover_circulation_proxy | Fee-inclusive external outflows / mean daily closing balance; requires valid balance and complete cash observation window |
| coverage_days | Count explicitly complete observed UTC days in window |
| coverage_length_days | Inclusive calendar span between first and last complete observed days; zero if none |
| observed_day_share | coverage_days / window_days |
| observation_gaps | ISO dates without explicit complete observation |
| active_day_count / active_day_share | Verified effective transaction event days / window days, excluding BALANCE_SNAPSHOT; no implication that other days had zero activity |
| source_count / source_mix | Unique source IDs / evidence event counts by source type in window |
| balance_coverage | Attested complete balance dates / window days; does not alone certify valid balance values |
| obligation_coverage | Attested complete schedule dates / window days; does not alone establish complete payment record |
| missingness_count / missingness_reasons | Count per-event missing/review reasons plus coverage reasons / distinct reasons |
| reviewed_event_share | Reviewed versions / all available in-window events; null if no events |
| accepted_event_share | Accepted after reconciliation / all available in-window events; null if no events |

Epsilon is Decimal('0.01') BDT, used only for numerical stability. Population variance and Decimal square root use precision 28. High CV is descriptive; it does not imply inability to repay. Turnover is a circulation proxy, never monetary velocity. There is no feature weighting, scoring, imputation or predictive model.

Obligations may originate before the window; their due dates determine the punctuality denominator. Payment dates on/after scoring date are excluded conservatively because they have day-level precision. Missing receipts do not establish nonpayment. Only an explicitly complete payment record permits an unpaid obligation to count as unpaid. Negative balances remain observable but invalidate liquidity/turnover ratios. The caller must provide verified daily closing balance records, not transaction-level samples labeled complete.

Full reversal semantics cancel the linked original and reversal as an economic pair, including originals outside the window. Partial reversals and mismatched fees require review; v1 does not model refunds as new standalone income. Cash-in/out and own-transfer fees require a separate explicitly external fee event if they are to enter cash-flow features. No consolidated multi-account balance aggregation is implemented. Coverage uses UTC full days; non-midnight scoring cannot certify all full-day ratios in v1.
