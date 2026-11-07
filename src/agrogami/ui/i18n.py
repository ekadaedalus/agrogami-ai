"""Interface-text localization (English / Bangla) for the Streamlit UI.

Scope: visible interface text only. Internal identifiers (page names, scenario keys, demo applicant
names), reason/status codes, UUIDs, hashes, model/version strings, API JSON and SMS sample text stay
exactly as they are. Numbers keep Western digits in both languages.

The Bangla strings were drafted with Claude Code and are pending native-speaker review by the team.
"""
from __future__ import annotations

from string import Formatter
from typing import Final, Literal

Language = Literal["en", "bn"]
LANGUAGES: Final[tuple[Language, ...]] = ("en", "bn")
DEFAULT_LANGUAGE: Final[Language] = "en"
LANGUAGE_NAMES: Final[dict[str, str]] = {"en": "English", "bn": "বাংলা"}
# Stable session_state keys: the selector widget and the resolved language.
LANGUAGE_WIDGET_KEY: Final = "ui_language_selector"
LANGUAGE_STATE_KEY: Final = "ui_language"

_EN: dict[str, str] = {
    # Sidebar
    "sidebar.language": "Language / ভাষা",
    "sidebar.navigation": "Navigation",
    "sidebar.demo_applicant": "Demo applicant",
    "sidebar.developer_settings": "Developer settings",
    "sidebar.api_url": "API URL",
    "sidebar.demo_credential": "Demo credential",
    "sidebar.applicant_uuid": "Applicant UUID",
    "applicant.Custom applicant UUID": "Custom applicant UUID",
    "applicant.Rahim — synthetic furniture workshop (scored)": "Rahim — synthetic furniture workshop (scored)",
    "applicant.Abstention demo — insufficient evidence": "Abstention demo — insufficient evidence",
    # Pages and helpers
    "page.Overview": "Overview",
    "page.Applicant Evidence": "Applicant Evidence",
    "page.Evidence Review": "Evidence Review",
    "page.Event Ledger": "Event Ledger",
    "page.Financial Profile": "Financial Profile",
    "page.Assessment": "Assessment",
    "page.Explanation": "Explanation",
    "page.Fairness & Evaluation": "Fairness & Evaluation",
    "page.Audit Trail": "Audit Trail",
    "page.Documentation": "Documentation",
    "helper.Applicant Evidence": "Add financial records to begin building a traceable evidence profile.",
    "helper.Evidence Review": "Corroborate extracted facts and preserve each reviewed version.",
    "helper.Event Ledger": "Inspect recorded transactions and their review status.",
    "helper.Financial Profile": "Explore verified cash flow, coverage, and financial history.",
    "helper.Assessment": "Assess available evidence or load a previous assessment.",
    "helper.Explanation": "See the evidence and reasons behind a stored assessment.",
    "helper.Fairness & Evaluation": "Inspect stored research evaluations and authorized aggregate fairness reports.",
    "helper.Audit Trail": "Trace original evidence, reviewed versions, and assessment history.",
    "helper.Documentation": "Explore the project workflow, evidence contracts, and API reference.",
    # Banner and Overview
    "demo.notice": ("**Demo environment** · Synthetic records only. Illustrative assessments are not lending "
                    "decisions or validated individual creditworthiness."),
    "overview.subtitle": "Traceable underwriting from financial records traditional credit systems ignore",
    "overview.caption": ("Turn mobile-money messages, informal ledger records, receipts, and bills into traceable "
                         "financial evidence for thin-file credit assessment."),
    "overview.positioning": "An explainable underwriting evidence and risk-audit workbench for thin-file credit.",
    "overview.pipeline": ("Evidence → Candidates → Validation & Reconciliation → Canonical Ledger → Features → Risk "
                          "→ Calibration → Explanation → Fairness → Immutable Assessment"),
    "overview.start": ("Start in Applicant Evidence, corroborate facts in Evidence Review, then inspect the Financial "
                       "Profile and Assessment. Every correction preserves its original evidence."),
    "overview.model_active": ("Calibrated LightGBM model active (SYNTHETIC_DEMO scope). No representative linked "
                              "borrower outcomes have been evaluated."),
    "overview.model_adapter": ("Model adapter available; trained Agrogami checkpoint not installed by default. No "
                               "representative linked borrower outcomes have been evaluated."),
    "overview.check_ready": "Check backend readiness",
    "overview.backend_status": "Backend status: {status}",
    # Shared evidence display
    "tech.label": "Technical evidence",
    "tech.label_context": "Technical evidence — {context}",
    "tech.audit_code": "Audit code: {code}",
    "ctx.intake_record": "intake record",
    "ctx.event_version": "event version",
    "ctx.assessment_snapshot": "assessment snapshot",
    "ctx.feature_snapshot": "{window}-day feature snapshot",
    "ctx.backend_readiness": "backend readiness",
    "ctx.original_candidate": "original candidate",
    "ctx.source_provenance": "source provenance · SHA-256",
    "ctx.corroborated_changes": "corroborated changes",
    "ctx.candidate_acceptance": "candidate acceptance",
    "ctx.explanation": "explanation",
    "ctx.stored_evaluation": "stored evaluation",
    "ctx.restricted_fairness": "restricted aggregate fairness",
    "ctx.assessment_versions": "assessment versions and predecessor links",
    "review.ownership_unconfirmed": "Ownership of this transaction could not be confirmed.",
    "job.status": "Evidence status: {status}",
    "job.sources_kept": "Source records and original candidates remain available for evidence review.",
    "event.amount": "Amount: {amount}",
    "event.source": "Source: {source}",
    "event.reference": "Event {identifier}",
    "event.reviewed_version": "Reviewed version; the original evidence remains in the audit trail.",
    # Event ledger table
    "ledger.col_date": "Date (UTC)",
    "ledger.col_amount": "Amount (Tk)",
    "ledger.col_direction": "Direction",
    "ledger.col_wallet": "Wallet",
    "ledger.col_status": "Status",
    "ledger.duplicate": "Duplicate",
    "ledger.reversed": "Reversed",
    "ledger.reversal": "Reversal",
    "ledger.own_transfer": "Own transfer (excluded)",
    "ledger.accepted": "Accepted",
    "ledger.synthetic_wallet": "Synthetic {name}",
    "ledger.count": "{count} stored event versions; review states remain visible.",
    "ledger.edge_only": "Show edge cases only",
    "ledger.caption": ("Latest versions only. Duplicates count once, reversals cancel the linked payment, "
                       "and own-wallet transfers are excluded from external cash flow."),
    "empty.no_events": "No event versions yet. Add and review evidence to begin the audit trail.",
    # Assessment
    "assess.withheld_insufficient": "Assessment withheld — Insufficient evidence",
    "assess.no_score_insufficient": ("Agrogami does not generate a credit-risk score when the verified evidence is "
                                     "not sufficient to support one."),
    "assess.withheld": "Assessment withheld",
    "assess.no_score_pending": ("A credit-risk score is unavailable until the evidence review and model "
                                "requirements are met."),
    "assess.system_state": "System state: {status}",
    "assess.why_withheld": "Why the assessment was withheld",
    "assess.reason_liquidity_invalid": "Available balance evidence does not support a valid liquidity measure",
    "assess.reason_balance_missing": "Complete balance history is unavailable",
    "assess.reason_obligation_missing": "Complete obligation history is unavailable",
    "assess.reason_no_outcomes": "Representative linked borrower outcomes have not yet been established",
    "assess.score_label": "Illustrative Project Score",
    "assess.probability": ("Calibrated probability of the modelled adverse label: {calibrated} "
                           "(raw model output {raw})."),
    "assess.artifact_scope": "Artifact scope: {scope}",
    "assess.scale_disclaimer": ("The project-specific 300–850 mapping is not FICO, bureau-equivalent, "
                                "internationally standardized, or an approval decision. Scaling does not create "
                                "calibration."),
    "assess.reference": "Assessment {identifier}",
    "assess.run": "Assess available evidence",
    "assess.load": "Load assessment",
    "assess.uuid": "Assessment UUID",
    # Financial profile
    "profile.last30": "Last 30 days · verified evidence only; totals do not establish complete cash flow.",
    "profile.verified_inflow": "Verified inflow",
    "profile.evidence_coverage": "Evidence coverage",
    "profile.payment_history": "Payment history",
    "profile.balance_history": "Balance history",
    "profile.detailed": "Detailed underwriting evidence",
    "profile.tab_days": "{days} days",
    "profile.col_measure": "Underwriting measure",
    "profile.col_value": "Value",
    "profile.col_notes": "Evidence notes",
    "profile.col_events": "Contributing events",
    "profile.full_keys": "Full feature keys and event identifiers are available in Technical evidence.",
    "profile.stored_as_of": "Stored feature snapshots as of {time}, with the coverage attested when they were computed.",
    # Applicant evidence
    "intake.scope": "Evidence scope",
    "intake.scenario": "Synthetic scenario",
    "intake.sms": "SMS evidence",
    "intake.sms_english_note": ("The SMS parser supports English synthetic templates only, so sample messages "
                                "stay in English."),
    "intake.provider": "Provider/template",
    "intake.account": "Account UUID (optional)",
    "intake.submit_sms": "Submit SMS",
    "intake.marker_required": "Synthetic evidence must retain its SYNTHETIC marker.",
    "intake.marker_scope": "Marked synthetic evidence must use the SYNTHETIC scope.",
    "intake.image_caption": ("Raster image upload preserves source identity; no OCR inference is claimed without "
                             "configured checkpoints."),
    "intake.image": "Image evidence",
    "intake.submit_image": "Submit image",
    "scenario.External inflow": "External inflow",
    "scenario.External outflow": "External outflow",
    "scenario.Send money": "Send money",
    "scenario.Cash in": "Cash in",
    "scenario.Cash out": "Cash out",
    "scenario.Reversal requiring linking": "Reversal requiring linking",
    # Evidence review
    "review.candidate_expander": "Review candidate evidence",
    "review.candidate_uuid": "Candidate UUID",
    "review.original_extraction": "Original extraction",
    "review.candidates_need_corroboration": ("Extracted candidates require corroboration before they become "
                                             "accepted financial evidence."),
    "review.event_select": "Event to review/correct",
    "review.changes": "Explicit corroborated changes (JSON)",
    "review.reason": "Correction reason",
    "review.alias": "Demo reviewer alias",
    "review.append": "Append reviewed version",
    "review.appended": "Reviewed version appended. Original evidence is preserved.",
    "review.candidate_only_caption": ("Candidate-only extraction can be accepted by supplying a full corroborated "
                                      "canonical contract."),
    "review.candidate_json": "Candidate-only canonical event JSON",
    "review.accept_candidate": "Accept corroborated candidate",
    # Explanation
    "explain.no_tree_shap": "No supported precomputed TreeSHAP explanation is available.",
    "explain.tree_shap": "TreeSHAP reason codes",
    "explain.col_input": "Model input",
    "explain.col_contribution": "Contribution to raw log-odds",
    "explain.col_direction": "Direction",
    "explain.raises": "Raises modelled risk",
    "explain.lowers": "Lowers modelled risk",
    "explain.no_effect": "No effect",
    "explain.base_value": "Base value {base} over background {background}.",
    "explain.shap_disclaimer": ("SHAP is association, not causality, legal adverse-action compliance, or calibrated "
                                "probability contribution."),
    "explain.prompt": ("Run an assessment on the Assessment page or load a stored assessment to view its "
                       "explanation."),
    # Fairness & evaluation
    "fair.not_evaluated": "Not evaluated with representative linked borrower outcomes.",
    "fair.advanced": "Advanced lookup",
    "fair.evaluation_uuid": "Stored evaluation UUID",
    "fair.scope": "Evaluation scope: {scope}",
    "fair.read_restricted": "Read restricted aggregate fairness",
    # Audit trail
    "audit.event_versions": "Immutable event versions",
    "audit.assessment_history": "Immutable assessment history",
    "audit.no_assessments": "No assessments yet. Assess available evidence to begin the assessment history.",
    "audit.correction_note": ("Correction appends a fresh unscored review snapshot. Original versions remain "
                              "recoverable."),
    "audit.lineage": "Source and extraction lineage",
    "audit.inspect_candidates": "Inspect original candidate versions (reviewer/admin)",
    # Documentation
    "docs.open_project": "Open synchronized project documentation",
    "docs.open_swagger": "Open API Swagger",
    # Errors
    "error.invalid_input": ("Invalid identifier, JSON, or response contract. Check the supplied evidence and "
                            "backend version."),
    "client.url_scheme": "API URL must use HTTP or HTTPS",
    "client.unavailable": "API unavailable. Start the local backend and check its URL.",
    "client.401": "Invalid demo credential",
    "client.403": "Reviewer/admin authorization required",
    "client.404": "Record not found",
    "client.409": "Immutable version conflict",
    "client.422": "Invalid or unresolved evidence",
    "client.503": "Subsystem unavailable",
    "client.failed": "Backend request failed",
    # formatting.py
    "fmt.unavailable": "Unavailable",
    "fmt.unavailable_because": "Unavailable — {reasons}",
    "fmt.insufficient_support": "insufficient supporting evidence",
    "fmt.insufficient": "Insufficient",
    "fmt.needs_review": "Needs review",
    "fmt.observed": "Observed",
    "fmt.available": "Available",
    "fmt.synthetic_source": "Synthetic {label}",
    "source.KHATA_IMAGE": "Informal ledger image",
    "source.UTILITY_DOCUMENT": "Utility document",
    "source.MOBILE_MONEY_SMS": "Mobile-money SMS",
    "source.PUBLIC_BENCHMARK": "Public benchmark record",
    "source.SYNTHETIC_FIXTURE": "Synthetic fixture",
    "provider.SYNTHETIC-bKash-like": "Synthetic bKash-like SMS",
    "provider.SYNTHETIC-Nagad-like": "Synthetic Nagad-like SMS",
    # Humanized codes (the raw code stays visible in audit codes and technical evidence)
    "label.external_inflow_total": "External inflow",
    "label.external_outflow_total": "External outflow",
    "label.inflow_cv": "Inflow variability",
    "label.coverage_length_days": "Coverage span (days)",
    "label.ACCEPTED": "Accepted",
    "label.NEEDS_REVIEW": "Needs review",
    "label.REJECTED": "Rejected",
    "label.INSUFFICIENT_EVIDENCE": "Insufficient evidence to assess",
    "label.EVIDENCE_PENDING": "Evidence pending",
    "label.REVIEW_REQUIRED": "Review required",
    "label.FEATURES_READY": "Financial evidence ready",
    "label.READY": "Assessment computation complete",
    "label.ILLUSTRATIVE": "Illustrative assessment",
    "label.COMPLETED": "Completed",
    "label.BLOCKED_MODEL_ARTIFACT": "Required model artifact unavailable",
    "label.MISSING_EVIDENCE": "Supporting evidence is missing",
    "label.AMBIGUOUS_AMOUNT": "Amount not confirmed",
    "label.CONTRADICTORY_DIRECTION": "Transaction direction conflicts with the evidence",
    "label.AMBIGUOUS_OWNERSHIP": "Ownership not confirmed",
    "label.UNSUPPORTED_TEMPLATE": "Source template requires review",
    "label.LOW_CONFIDENCE": "Extraction requires review",
    "label.CURRENCY_MISMATCH": "Currencies do not match",
    "label.IMPLAUSIBLE_AMOUNT": "Amount requires review",
    "label.AMBIGUOUS_MATCH": "Possible matching transaction requires review",
    "label.BALANCE_INCONSISTENCY": "Balance does not reconcile",
    "label.INVALID_LINK": "Linked transaction could not be verified",
    "label.RECEIPT": "Receipt",
    "label.SEND_MONEY": "Money sent",
    "label.CASH_IN": "Cash in",
    "label.CASH_OUT": "Cash out",
    "label.PAYMENT": "Payment",
    "label.REVERSAL": "Reversal",
    "label.TRANSFER": "Transfer",
    "label.CREDIT_SALE": "Credit sale",
    "label.RECEIVABLE": "Receivable",
    "label.PAYABLE": "Payable",
    "label.SETTLEMENT": "Settlement",
    "label.BALANCE_SNAPSHOT": "Balance observation",
    "label.OTHER": "Other",
    "label.INFLOW": "Inflow",
    "label.OUTFLOW": "Outflow",
    "label.NEUTRAL": "No cash-flow direction",
    "label.UNKNOWN": "Unknown",
    "label.UNTRAINED": "Untrained",
    "label.SYNTHETIC_DEMO": "Synthetic demonstration",
    "label.PUBLIC_DATASET_BENCHMARK": "Public dataset benchmark",
    "label.REAL_LINKED_OUTCOME_EXPERIMENT": "Experiment with linked borrower outcomes",
    "label.LATE_VERIFIED_BILLS": "Verified bills paid after their due dates",
    "label.LOWER_TAIL_LIQUIDITY": "Lower observed daily balance ratio",
    "label.complete_obligation_denominator_unknown": (
        "Payment history unavailable — complete obligation history is missing"),
    "label.payment_record_incomplete; absence_is_not_nonpayment": (
        "Payment history is incomplete — missing records do not establish nonpayment"),
    "label.no_verified_obligations_due": "No verified obligations due in this period",
    "label.no_verified_payments": "No verified payment records available",
    "label.incomplete_or_invalid_daily_balance_history": (
        "Balance history unavailable — complete valid daily balances are missing"),
    "label.incomplete_cash_observation": "Cash-flow history is incomplete",
    "label.incomplete_cash_observation; totals cover verified evidence only": (
        "Cash-flow history is incomplete — totals cover verified evidence only"),
    "label.CV uses attested complete days only; unobserved days omitted": (
        "Inflow variability uses complete observed days only; unobserved days are excluded"),
    "label.observed_values_only": "Observed balances only; complete history is unavailable",
    "label.no_verified_coverage_supplied": "Verified observation coverage has not been supplied",
    "label.correction_requires_fresh_coverage_and_reassessment": (
        "Corrected evidence requires fresh coverage and a new assessment"),
    "label.raw_model_candidates_require_review": "Extracted candidates require review",
    "label.line_level_regions_not_word_boxes": "Source locations identify lines, not individual words",
    # Feature names whose English label is the readable form of the key (identical to the prior fallback).
    "label.net_external_cash_flow": "Net external cash flow",
    "label.payment_punctuality": "Payment punctuality",
    "label.median_payment_delay_days": "Median payment delay days",
    "label.liquidity_floor": "Liquidity floor",
    "label.observed_minimum_balance": "Observed minimum balance",
    "label.turnover_circulation_proxy": "Turnover circulation proxy",
    "label.coverage_days": "Coverage days",
    "label.observed_day_share": "Observed day share",
    "label.observation_gaps": "Observation gaps",
    "label.balance_coverage": "Balance coverage",
    "label.obligation_coverage": "Obligation coverage",
    "label.reviewed_event_share": "Reviewed event share",
    "label.accepted_event_share": "Accepted event share",
}

_BN: dict[str, str] = {
    # Sidebar
    "sidebar.language": "Language / ভাষা",
    "sidebar.navigation": "পাতাসমূহ",
    "sidebar.demo_applicant": "ডেমো আবেদনকারী",
    "sidebar.developer_settings": "ডেভেলপার সেটিংস",
    "sidebar.api_url": "API URL",
    "sidebar.demo_credential": "ডেমো ক্রেডেনশিয়াল (টোকেন)",
    "sidebar.applicant_uuid": "আবেদনকারীর UUID",
    "applicant.Custom applicant UUID": "নিজস্ব আবেদনকারী UUID",
    "applicant.Rahim — synthetic furniture workshop (scored)": "রহিম — সিন্থেটিক আসবাবপত্রের কারখানা (স্কোর আছে)",
    "applicant.Abstention demo — insufficient evidence": "স্কোর স্থগিত — প্রমাণ অপর্যাপ্ত (ডেমো)",
    # Pages and helpers
    "page.Overview": "সারসংক্ষেপ",
    "page.Applicant Evidence": "আবেদনকারীর প্রমাণ",
    "page.Evidence Review": "প্রমাণ যাচাই",
    "page.Event Ledger": "লেনদেনের লেজার",
    "page.Financial Profile": "আর্থিক প্রোফাইল",
    "page.Assessment": "মূল্যায়ন",
    "page.Explanation": "ব্যাখ্যা",
    "page.Fairness & Evaluation": "ন্যায্যতা ও মডেল পরীক্ষা",
    "page.Audit Trail": "অডিট ট্রেইল",
    "page.Documentation": "ডকুমেন্টেশন",
    "helper.Applicant Evidence": "যাচাইযোগ্য প্রমাণ-প্রোফাইল তৈরি শুরু করতে আর্থিক রেকর্ড যোগ করুন।",
    "helper.Evidence Review": "সংগৃহীত তথ্য মিলিয়ে নিশ্চিত করুন; প্রতিটি যাচাই করা সংস্করণ সংরক্ষিত থাকবে।",
    "helper.Event Ledger": "রেকর্ড করা লেনদেন ও সেগুলোর যাচাইয়ের অবস্থা দেখুন।",
    "helper.Financial Profile": "যাচাই করা নগদ প্রবাহ, তথ্যের কভারেজ ও আর্থিক ইতিহাস দেখুন।",
    "helper.Assessment": "প্রাপ্ত প্রমাণের ভিত্তিতে মূল্যায়ন করুন, অথবা আগের কোনো মূল্যায়ন খুলুন।",
    "helper.Explanation": "সংরক্ষিত মূল্যায়নের পেছনের প্রমাণ ও কারণগুলো দেখুন।",
    "helper.Fairness & Evaluation": "সংরক্ষিত গবেষণা-মূল্যায়ন ও অনুমোদিত সমষ্টিগত ন্যায্যতা রিপোর্ট দেখুন।",
    "helper.Audit Trail": "মূল প্রমাণ, যাচাই করা সংস্করণ ও মূল্যায়নের ইতিহাস ধাপে ধাপে দেখুন।",
    "helper.Documentation": "প্রকল্পের কাজের ধারা, প্রমাণের কাঠামো ও API রেফারেন্স দেখুন।",
    # Banner and Overview
    "demo.notice": ("**ডেমো পরিবেশ** · এখানে শুধু সিন্থেটিক (কৃত্রিম) রেকর্ড ব্যবহার করা হয়েছে। দৃষ্টান্তমূলক "
                    "মূল্যায়ন কোনো ঋণ-সিদ্ধান্ত নয়, কোনো ব্যক্তির ঋণযোগ্যতার যাচাই করা প্রমাণও নয়।"),
    "overview.subtitle": "প্রচলিত ঋণ-ব্যবস্থা যেসব আর্থিক রেকর্ড উপেক্ষা করে, সেগুলো থেকে যাচাইযোগ্য ঋণ-মূল্যায়ন",
    "overview.caption": ("মোবাইল মানির SMS, খাতার হিসাব, রসিদ ও বিলকে যাচাইযোগ্য আর্থিক প্রমাণে রূপান্তর করুন — "
                         "যাঁদের ক্রেডিট ইতিহাস কম, তাঁদের ঋণ-মূল্যায়নের জন্য।"),
    "overview.positioning": ("কম ক্রেডিট ইতিহাসের ঋণগ্রহীতাদের জন্য ব্যাখ্যাযোগ্য ঋণ-প্রমাণ ও ঝুঁকি-অডিটের "
                             "কর্মক্ষেত্র।"),
    "overview.pipeline": ("প্রমাণ → যাচাই-অপেক্ষমাণ তথ্য → যাচাই ও মিলকরণ → মূল লেজার → ফিচার → ঝুঁকি → ক্যালিব্রেশন "
                          "→ ব্যাখ্যা → ন্যায্যতা → অপরিবর্তনীয় মূল্যায়ন"),
    "overview.start": ("“আবেদনকারীর প্রমাণ” পাতা থেকে শুরু করুন, “প্রমাণ যাচাই” পাতায় তথ্য নিশ্চিত করুন, তারপর "
                       "“আর্থিক প্রোফাইল” ও “মূল্যায়ন” দেখুন। প্রতিটি সংশোধনে মূল প্রমাণ অক্ষত থাকে।"),
    "overview.model_active": ("ক্যালিব্রেটেড LightGBM মডেল চালু আছে (SYNTHETIC_DEMO পরিসর)। প্রতিনিধিত্বমূলক "
                              "নমুনার বাস্তব ঋণগ্রহীতাদের পরিশোধের ফলাফল দিয়ে এখনো কোনো মূল্যায়ন হয়নি।"),
    "overview.model_adapter": ("মডেল অ্যাডাপ্টার আছে; প্রশিক্ষিত Agrogami চেকপয়েন্ট ডিফল্টভাবে ইনস্টল করা নেই। "
                               "প্রতিনিধিত্বমূলক নমুনার বাস্তব ঋণগ্রহীতাদের পরিশোধের ফলাফল দিয়ে এখনো কোনো মূল্যায়ন হয়নি।"),
    "overview.check_ready": "ব্যাকএন্ড প্রস্তুত কি না দেখুন",
    "overview.backend_status": "ব্যাকএন্ডের অবস্থা: {status}",
    # Shared evidence display
    "tech.label": "কারিগরি প্রমাণ",
    "tech.label_context": "কারিগরি প্রমাণ — {context}",
    "tech.audit_code": "অডিট কোড: {code}",
    "ctx.intake_record": "জমা নেওয়ার রেকর্ড",
    "ctx.event_version": "ইভেন্টের সংস্করণ",
    "ctx.assessment_snapshot": "মূল্যায়নের স্ন্যাপশট",
    "ctx.feature_snapshot": "{window} দিনের ফিচার স্ন্যাপশট",
    "ctx.backend_readiness": "ব্যাকএন্ডের প্রস্তুতি",
    "ctx.original_candidate": "মূল যাচাই-অপেক্ষমাণ তথ্য",
    "ctx.source_provenance": "উৎসের বিবরণ · SHA-256",
    "ctx.corroborated_changes": "নিশ্চিত করা পরিবর্তন",
    "ctx.candidate_acceptance": "যাচাই-অপেক্ষমাণ তথ্য গ্রহণ",
    "ctx.explanation": "ব্যাখ্যা",
    "ctx.stored_evaluation": "সংরক্ষিত মূল্যায়ন",
    "ctx.restricted_fairness": "সীমিত-প্রবেশ সমষ্টিগত ন্যায্যতা",
    "ctx.assessment_versions": "মূল্যায়নের সংস্করণ ও আগের সংস্করণের সংযোগ",
    "review.ownership_unconfirmed": "এই লেনদেনটি কার, তা নিশ্চিত করা যায়নি।",
    "job.status": "প্রমাণের অবস্থা: {status}",
    "job.sources_kept": "উৎস-রেকর্ড ও মূল যাচাই-অপেক্ষমাণ তথ্য প্রমাণ যাচাইয়ের জন্য সংরক্ষিত থাকে।",
    "event.amount": "পরিমাণ: {amount}",
    "event.source": "উৎস: {source}",
    "event.reference": "ইভেন্ট {identifier}",
    "event.reviewed_version": "যাচাই করা সংস্করণ; মূল প্রমাণ অডিট ট্রেইলে রয়ে গেছে।",
    # Event ledger table
    "ledger.col_date": "তারিখ (UTC)",
    "ledger.col_amount": "পরিমাণ (টাকা)",
    "ledger.col_direction": "দিক",
    "ledger.col_wallet": "ওয়ালেট",
    "ledger.col_status": "অবস্থা",
    "ledger.duplicate": "ডুপ্লিকেট",
    "ledger.reversed": "রিভার্স হয়েছে",
    "ledger.reversal": "রিভার্সাল",
    "ledger.own_transfer": "নিজের অ্যাকাউন্টে স্থানান্তর (বাদ)",
    "ledger.accepted": "গৃহীত",
    "ledger.synthetic_wallet": "সিন্থেটিক {name}",
    "ledger.count": "সংরক্ষিত ইভেন্ট সংস্করণ: {count}টি; যাচাইয়ের অবস্থা দেখা যাচ্ছে।",
    "ledger.edge_only": "শুধু ব্যতিক্রমী লেনদেন দেখান",
    "ledger.caption": ("শুধু সর্বশেষ সংস্করণ। ডুপ্লিকেট একবারই গণনা হয়, রিভার্সাল সংশ্লিষ্ট পেমেন্ট বাতিল করে, "
                       "আর নিজের ওয়ালেটে স্থানান্তর বাইরের নগদ প্রবাহ থেকে বাদ থাকে।"),
    "empty.no_events": "এখনো কোনো ইভেন্ট সংস্করণ নেই। অডিট ট্রেইল শুরু করতে প্রমাণ যোগ ও যাচাই করুন।",
    # Assessment
    "assess.withheld_insufficient": "মূল্যায়ন স্থগিত — যথেষ্ট প্রমাণ নেই",
    "assess.no_score_insufficient": "যাচাই করা প্রমাণ যথেষ্ট না হলে Agrogami কোনো ক্রেডিট-ঝুঁকি স্কোর তৈরি করে না।",
    "assess.withheld": "মূল্যায়ন স্থগিত",
    "assess.no_score_pending": "প্রমাণ যাচাই ও মডেলের শর্ত পূরণ না হওয়া পর্যন্ত ক্রেডিট-ঝুঁকি স্কোর পাওয়া যাবে না।",
    "assess.system_state": "সিস্টেমের অবস্থা: {status}",
    "assess.why_withheld": "কেন মূল্যায়ন স্থগিত রাখা হয়েছে",
    "assess.reason_liquidity_invalid": "প্রাপ্ত ব্যালান্সের প্রমাণ দিয়ে তারল্যের সঠিক পরিমাপ করা যায় না",
    "assess.reason_balance_missing": "ব্যালান্সের সম্পূর্ণ ইতিহাস পাওয়া যায়নি",
    "assess.reason_obligation_missing": "বিল ও কিস্তি পরিশোধের সম্পূর্ণ ইতিহাস পাওয়া যায়নি",
    "assess.reason_no_outcomes": "প্রতিনিধিত্বমূলক নমুনার বাস্তব ঋণগ্রহীতাদের পরিশোধের ফলাফল এখনো পাওয়া যায়নি",
    "assess.score_label": "দৃষ্টান্তমূলক প্রকল্প স্কোর",
    "assess.probability": ("মডেল করা প্রতিকূল লেবেলের ক্যালিব্রেটেড সম্ভাবনা: {calibrated} "
                           "(মডেলের কাঁচা আউটপুট {raw})।"),
    "assess.artifact_scope": "মডেল আর্টিফ্যাক্টের পরিসর: {scope}",
    "assess.scale_disclaimer": ("প্রকল্প-নির্দিষ্ট 300–850 স্কেলটি FICO নয়, ক্রেডিট ব্যুরোর সমতুল্য নয়, "
                                "আন্তর্জাতিকভাবে মানসম্মত নয়, এবং কোনো ঋণ-অনুমোদনের সিদ্ধান্তও নয়। স্কেলে "
                                "রূপান্তর করলেই ক্যালিব্রেশন হয় না।"),
    "assess.reference": "মূল্যায়ন {identifier}",
    "assess.run": "প্রাপ্ত প্রমাণ মূল্যায়ন করুন",
    "assess.load": "মূল্যায়ন খুলুন",
    "assess.uuid": "মূল্যায়নের UUID",
    # Financial profile
    "profile.last30": "গত 30 দিন · শুধু যাচাই করা প্রমাণ; মোট অঙ্ক দিয়ে সম্পূর্ণ নগদ প্রবাহ প্রমাণিত হয় না।",
    "profile.verified_inflow": "যাচাই করা জমা (ইনফ্লো)",
    "profile.evidence_coverage": "প্রমাণের কভারেজ",
    "profile.payment_history": "পরিশোধের ইতিহাস",
    "profile.balance_history": "ব্যালান্সের ইতিহাস",
    "profile.detailed": "বিস্তারিত ঋণ-মূল্যায়ন প্রমাণ",
    "profile.tab_days": "{days} দিন",
    "profile.col_measure": "মূল্যায়নের মাপকাঠি",
    "profile.col_value": "মান",
    "profile.col_notes": "প্রমাণ-সংক্রান্ত নোট",
    "profile.col_events": "সংশ্লিষ্ট ইভেন্ট",
    "profile.full_keys": "ফিচারের পূর্ণ নাম ও ইভেন্টের শনাক্তকারী “কারিগরি প্রমাণ” অংশে আছে।",
    "profile.stored_as_of": "{time} পর্যন্ত সংরক্ষিত ফিচার স্ন্যাপশট, গণনার সময় ঘোষিত কভারেজসহ।",
    # Applicant evidence
    "intake.scope": "প্রমাণের ধরন",
    "intake.scenario": "সিন্থেটিক উদাহরণ",
    "intake.sms": "SMS প্রমাণ",
    "intake.sms_english_note": ("SMS পার্সার শুধু ইংরেজি সিন্থেটিক টেমপ্লেট বোঝে, তাই নমুনা SMS ইংরেজিতেই রাখা "
                                "হয়েছে।"),
    "intake.provider": "প্রোভাইডার/টেমপ্লেট",
    "intake.account": "অ্যাকাউন্ট UUID (ঐচ্ছিক)",
    "intake.submit_sms": "SMS জমা দিন",
    "intake.marker_required": "সিন্থেটিক প্রমাণে SYNTHETIC চিহ্নটি অবশ্যই রাখতে হবে।",
    "intake.marker_scope": "SYNTHETIC চিহ্নযুক্ত প্রমাণের জন্য SYNTHETIC ধরন বেছে নিতে হবে।",
    "intake.image_caption": ("ছবি আপলোড করলে উৎসের পরিচয় সংরক্ষিত থাকে; কনফিগার করা চেকপয়েন্ট ছাড়া কোনো OCR "
                             "ফলাফলের দাবি করা হয় না।"),
    "intake.image": "ছবির প্রমাণ",
    "intake.submit_image": "ছবি জমা দিন",
    "scenario.External inflow": "বাইরের উৎস থেকে টাকা জমা",
    "scenario.External outflow": "বাইরে টাকা পরিশোধ",
    "scenario.Send money": "সেন্ড মানি",
    "scenario.Cash in": "ক্যাশ ইন",
    "scenario.Cash out": "ক্যাশ আউট",
    "scenario.Reversal requiring linking": "রিভার্সাল (মূল লেনদেনের সাথে মেলাতে হবে)",
    # Evidence review
    "review.candidate_expander": "যাচাই-অপেক্ষমাণ তথ্য পর্যালোচনা করুন",
    "review.candidate_uuid": "যাচাই-অপেক্ষমাণ তথ্যের UUID",
    "review.original_extraction": "মূল সংগৃহীত তথ্য",
    "review.candidates_need_corroboration": ("সংগৃহীত তথ্য গৃহীত আর্থিক প্রমাণ হওয়ার আগে তা মিলিয়ে নিশ্চিত করতে "
                                             "হবে।"),
    "review.event_select": "যাচাই/সংশোধনের জন্য ইভেন্ট",
    "review.changes": "নিশ্চিত করা পরিবর্তন (JSON)",
    "review.reason": "সংশোধনের কারণ",
    "review.alias": "ডেমো রিভিউয়ারের ছদ্মনাম",
    "review.append": "যাচাই করা সংস্করণ যোগ করুন",
    "review.appended": "যাচাই করা সংস্করণ যোগ হয়েছে। মূল প্রমাণ সংরক্ষিত আছে।",
    "review.candidate_only_caption": ("শুধু যাচাই-অপেক্ষমাণ অবস্থায় থাকা তথ্য গ্রহণ করতে মূল লেজারের পূর্ণাঙ্গ ও "
                                      "নিশ্চিত করা ইভেন্ট দিতে হবে।"),
    "review.candidate_json": "যাচাই-অপেক্ষমাণ তথ্যের জন্য মূল লেজারের ইভেন্ট (JSON)",
    "review.accept_candidate": "নিশ্চিত করা যাচাই-অপেক্ষমাণ তথ্য গ্রহণ করুন",
    # Explanation
    "explain.no_tree_shap": "আগে থেকে গণনা করা সমর্থিত কোনো TreeSHAP ব্যাখ্যা নেই।",
    "explain.tree_shap": "TreeSHAP কারণ-কোড",
    "explain.col_input": "মডেলের ইনপুট",
    "explain.col_contribution": "কাঁচা লগ-অডস-এ অবদান",
    "explain.col_direction": "দিক",
    "explain.raises": "মডেলের হিসাবে ঝুঁকি বাড়ায়",
    "explain.lowers": "মডেলের হিসাবে ঝুঁকি কমায়",
    "explain.no_effect": "কোনো প্রভাব নেই",
    "explain.base_value": "ভিত্তি-মান {base}, ব্যাকগ্রাউন্ড {background}।",
    "explain.shap_disclaimer": ("SHAP শুধু সম্পর্ক দেখায় — এটি কার্যকারণ নয়, ঋণ নাকচের কারণ জানানোর আইনি বাধ্যবাধকতা "
                                "পূরণ করে না, আর ক্যালিব্রেটেড সম্ভাবনায় অবদানও নয়।"),
    "explain.prompt": "ব্যাখ্যা দেখতে “মূল্যায়ন” পাতায় মূল্যায়ন চালান, অথবা সংরক্ষিত কোনো মূল্যায়ন খুলুন।",
    # Fairness & evaluation
    "fair.not_evaluated": "প্রতিনিধিত্বমূলক নমুনার বাস্তব ঋণগ্রহীতাদের পরিশোধের ফলাফল দিয়ে মূল্যায়ন করা হয়নি।",
    "fair.advanced": "বিস্তারিত অনুসন্ধান",
    "fair.evaluation_uuid": "সংরক্ষিত মূল্যায়নের UUID",
    "fair.scope": "মূল্যায়নের পরিসর: {scope}",
    "fair.read_restricted": "সীমিত-প্রবেশ সমষ্টিগত ন্যায্যতা দেখুন",
    # Audit trail
    "audit.event_versions": "অপরিবর্তনীয় ইভেন্ট সংস্করণ",
    "audit.assessment_history": "অপরিবর্তনীয় মূল্যায়নের ইতিহাস",
    "audit.no_assessments": "এখনো কোনো মূল্যায়ন নেই। মূল্যায়নের ইতিহাস শুরু করতে প্রাপ্ত প্রমাণ মূল্যায়ন করুন।",
    "audit.correction_note": ("সংশোধন করলে স্কোর ছাড়া নতুন একটি যাচাই-স্ন্যাপশট যোগ হয়। মূল সংস্করণগুলো ফেরত "
                              "পাওয়া যায়।"),
    "audit.lineage": "উৎস ও তথ্য-সংগ্রহের ধারাবাহিকতা",
    "audit.inspect_candidates": "যাচাই-অপেক্ষমাণ তথ্যের মূল সংস্করণ দেখুন (রিভিউয়ার/অ্যাডমিন)",
    # Documentation
    "docs.open_project": "প্রকল্পের হালনাগাদ ডকুমেন্টেশন খুলুন",
    "docs.open_swagger": "API Swagger খুলুন",
    # Errors
    "error.invalid_input": ("শনাক্তকারী, JSON বা রেসপন্সের কাঠামো সঠিক নয়। দেওয়া প্রমাণ ও ব্যাকএন্ডের সংস্করণ "
                            "পরীক্ষা করুন।"),
    "client.url_scheme": "API URL অবশ্যই HTTP বা HTTPS হতে হবে",
    "client.unavailable": "API পাওয়া যাচ্ছে না। লোকাল ব্যাকএন্ড চালু করে এর URL পরীক্ষা করুন।",
    "client.401": "ডেমো ক্রেডেনশিয়াল সঠিক নয়",
    "client.403": "রিভিউয়ার/অ্যাডমিন অনুমতি প্রয়োজন",
    "client.404": "রেকর্ড পাওয়া যায়নি",
    "client.409": "অপরিবর্তনীয় সংস্করণে দ্বন্দ্ব",
    "client.422": "প্রমাণ সঠিক নয় বা অমীমাংসিত",
    "client.503": "সংশ্লিষ্ট সাবসিস্টেম চালু নেই",
    "client.failed": "ব্যাকএন্ডের অনুরোধ ব্যর্থ হয়েছে",
    # formatting.py
    "fmt.unavailable": "পাওয়া যায়নি",
    "fmt.unavailable_because": "পাওয়া যায়নি — {reasons}",
    "fmt.insufficient_support": "সমর্থনকারী প্রমাণ যথেষ্ট নয়",
    "fmt.insufficient": "অপর্যাপ্ত",
    "fmt.needs_review": "যাচাই প্রয়োজন",
    "fmt.observed": "পর্যবেক্ষিত",
    "fmt.available": "পাওয়া যায়",
    "fmt.synthetic_source": "সিন্থেটিক {label}",
    "source.KHATA_IMAGE": "খাতার ছবি",
    "source.UTILITY_DOCUMENT": "ইউটিলিটি বিল/নথি",
    "source.MOBILE_MONEY_SMS": "মোবাইল মানি SMS",
    "source.PUBLIC_BENCHMARK": "পাবলিক বেঞ্চমার্ক রেকর্ড",
    "source.SYNTHETIC_FIXTURE": "সিন্থেটিক নমুনা",
    "provider.SYNTHETIC-bKash-like": "সিন্থেটিক bKash-ধাঁচের SMS",
    "provider.SYNTHETIC-Nagad-like": "সিন্থেটিক Nagad-ধাঁচের SMS",
    # Humanized codes
    "label.external_inflow_total": "বাইরের উৎস থেকে মোট জমা",
    "label.external_outflow_total": "বাইরে মোট পরিশোধ",
    "label.inflow_cv": "জমার ওঠানামা",
    "label.coverage_length_days": "কভারেজের সময়কাল (দিন)",
    "label.ACCEPTED": "গৃহীত",
    "label.NEEDS_REVIEW": "যাচাই প্রয়োজন",
    "label.REJECTED": "বাতিল",
    "label.INSUFFICIENT_EVIDENCE": "মূল্যায়নের জন্য যথেষ্ট প্রমাণ নেই",
    "label.EVIDENCE_PENDING": "প্রমাণ অপেক্ষমাণ",
    "label.REVIEW_REQUIRED": "যাচাই আবশ্যক",
    "label.FEATURES_READY": "আর্থিক প্রমাণ প্রস্তুত",
    "label.READY": "মূল্যায়নের গণনা সম্পন্ন",
    "label.ILLUSTRATIVE": "দৃষ্টান্তমূলক মূল্যায়ন",
    "label.COMPLETED": "সম্পন্ন",
    "label.BLOCKED_MODEL_ARTIFACT": "প্রয়োজনীয় মডেল আর্টিফ্যাক্ট পাওয়া যায়নি",
    "label.MISSING_EVIDENCE": "সমর্থনকারী প্রমাণ নেই",
    "label.AMBIGUOUS_AMOUNT": "পরিমাণ নিশ্চিত নয়",
    "label.CONTRADICTORY_DIRECTION": "লেনদেনের দিক প্রমাণের সাথে মিলছে না",
    "label.AMBIGUOUS_OWNERSHIP": "মালিকানা নিশ্চিত নয়",
    "label.UNSUPPORTED_TEMPLATE": "উৎসের টেমপ্লেট যাচাই করতে হবে",
    "label.LOW_CONFIDENCE": "সংগৃহীত তথ্য যাচাই করতে হবে",
    "label.CURRENCY_MISMATCH": "মুদ্রা মিলছে না",
    "label.IMPLAUSIBLE_AMOUNT": "পরিমাণটি যাচাই করতে হবে",
    "label.AMBIGUOUS_MATCH": "মিলে যেতে পারে এমন লেনদেন যাচাই করতে হবে",
    "label.BALANCE_INCONSISTENCY": "ব্যালান্সের হিসাব মিলছে না",
    "label.INVALID_LINK": "সংযুক্ত লেনদেন যাচাই করা যায়নি",
    "label.RECEIPT": "টাকা গ্রহণ",
    "label.SEND_MONEY": "সেন্ড মানি",
    "label.CASH_IN": "ক্যাশ ইন",
    "label.CASH_OUT": "ক্যাশ আউট",
    "label.PAYMENT": "পেমেন্ট",
    "label.REVERSAL": "রিভার্সাল",
    "label.TRANSFER": "স্থানান্তর",
    "label.CREDIT_SALE": "বাকিতে বিক্রি",
    "label.RECEIVABLE": "পাওনা",
    "label.PAYABLE": "দেনা",
    "label.SETTLEMENT": "নিষ্পত্তি",
    "label.BALANCE_SNAPSHOT": "ব্যালান্সের তথ্য",
    "label.OTHER": "অন্যান্য",
    "label.INFLOW": "জমা (ইনফ্লো)",
    "label.OUTFLOW": "পরিশোধ (আউটফ্লো)",
    "label.NEUTRAL": "নগদ প্রবাহের কোনো দিক নেই",
    "label.UNKNOWN": "অজানা",
    "label.UNTRAINED": "প্রশিক্ষণহীন",
    "label.SYNTHETIC_DEMO": "সিন্থেটিক প্রদর্শনী",
    "label.PUBLIC_DATASET_BENCHMARK": "পাবলিক ডেটাসেট বেঞ্চমার্ক",
    "label.REAL_LINKED_OUTCOME_EXPERIMENT": "বাস্তব ঋণগ্রহীতাদের পরিশোধের ফলাফলসহ পরীক্ষা",
    "label.LATE_VERIFIED_BILLS": "যাচাই করা বিল নির্ধারিত তারিখের পরে পরিশোধ হয়েছে",
    "label.LOWER_TAIL_LIQUIDITY": "দৈনিক ব্যালান্সের পর্যবেক্ষিত অনুপাত কম",
    "label.complete_obligation_denominator_unknown": (
        "পরিশোধের ইতিহাস পাওয়া যায়নি — বিল ও কিস্তি পরিশোধের সম্পূর্ণ ইতিহাস নেই"),
    "label.payment_record_incomplete; absence_is_not_nonpayment": (
        "পরিশোধের রেকর্ড অসম্পূর্ণ — রেকর্ড না থাকা মানেই অপরিশোধ নয়"),
    "label.no_verified_obligations_due": "এই সময়ে পরিশোধযোগ্য কোনো যাচাই করা দেনা নেই",
    "label.no_verified_payments": "যাচাই করা কোনো পরিশোধের রেকর্ড নেই",
    "label.incomplete_or_invalid_daily_balance_history": (
        "ব্যালান্সের ইতিহাস পাওয়া যায়নি — সম্পূর্ণ ও সঠিক দৈনিক ব্যালান্স নেই"),
    "label.incomplete_cash_observation": "নগদ প্রবাহের ইতিহাস অসম্পূর্ণ",
    "label.incomplete_cash_observation; totals cover verified evidence only": (
        "নগদ প্রবাহের ইতিহাস অসম্পূর্ণ — মোট অঙ্ক শুধু যাচাই করা প্রমাণের"),
    "label.CV uses attested complete days only; unobserved days omitted": (
        "জমার ওঠানামা শুধু সম্পূর্ণ পর্যবেক্ষিত দিনের ভিত্তিতে; পর্যবেক্ষণহীন দিন বাদ দেওয়া হয়েছে"),
    "label.observed_values_only": "শুধু পর্যবেক্ষিত ব্যালান্স; সম্পূর্ণ ইতিহাস নেই",
    "label.no_verified_coverage_supplied": "যাচাই করা পর্যবেক্ষণ-কভারেজ দেওয়া হয়নি",
    "label.correction_requires_fresh_coverage_and_reassessment": (
        "সংশোধিত প্রমাণের জন্য নতুন কভারেজ ও নতুন মূল্যায়ন প্রয়োজন"),
    "label.raw_model_candidates_require_review": "সংগৃহীত যাচাই-অপেক্ষমাণ তথ্য পর্যালোচনা করতে হবে",
    "label.line_level_regions_not_word_boxes": "উৎসের অবস্থান লাইন ধরে চিহ্নিত, আলাদা শব্দ ধরে নয়",
    "label.net_external_cash_flow": "বাইরের নিট নগদ প্রবাহ",
    "label.payment_punctuality": "সময়মতো পরিশোধ",
    "label.median_payment_delay_days": "পরিশোধে বিলম্বের মধ্যমা (দিন)",
    "label.liquidity_floor": "তারল্যের নিম্নসীমা",
    "label.observed_minimum_balance": "পর্যবেক্ষিত সর্বনিম্ন ব্যালান্স",
    "label.turnover_circulation_proxy": "লেনদেন আবর্তনের আনুমানিক সূচক",
    "label.coverage_days": "কভারেজের দিন",
    "label.observed_day_share": "পর্যবেক্ষিত দিনের অনুপাত",
    "label.observation_gaps": "পর্যবেক্ষণের ফাঁক",
    "label.balance_coverage": "ব্যালান্সের কভারেজ",
    "label.obligation_coverage": "দেনার কভারেজ",
    "label.reviewed_event_share": "যাচাই করা ইভেন্টের অনুপাত",
    "label.accepted_event_share": "গৃহীত ইভেন্টের অনুপাত",
}

STRINGS: Final[dict[str, dict[str, str]]] = {"en": _EN, "bn": _BN}

# Bangla glyphs fall back to Noto Sans Bengali; Latin text keeps Streamlit's default Source Sans.
BANGLA_FONT_IMPORT: Final = ("@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:"
                             "wght@400;500;600;700&display=swap');\n")
# Icons (Material Symbols), JSON payloads and code keep their own fonts.
BANGLA_FONT_RULES: Final = """
        .stApp, .stApp *:not([data-testid="stIconMaterial"]):not([data-testid="stJson"] *):not(code):not(code *):not(pre):not(pre *) {
            font-family: "Source Sans", "Source Sans Pro", "Noto Sans Bengali", sans-serif !important;
        }
"""


def placeholders(template: str) -> set[str]:
    """Named format fields used by a template."""
    return {field for _, field, _, _ in Formatter().parse(template) if field}


def current_language() -> Language:
    """Selected interface language; English outside a running Streamlit session or when unset."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx(suppress_warning=True) is None:
            return DEFAULT_LANGUAGE
        import streamlit as st
        value = st.session_state.get(LANGUAGE_STATE_KEY, DEFAULT_LANGUAGE)
    except Exception:  # Streamlit absent (API/smoke tooling) or no session: English.
        return DEFAULT_LANGUAGE
    return value if value in LANGUAGES else DEFAULT_LANGUAGE


def has(key: str) -> bool:
    return key in _EN


def t(key: str, lang: str | None = None, /, **fmt: object) -> str:
    """Translate a key; falls back to English, then to the key itself. Never raises."""
    language = lang if lang in LANGUAGES else current_language()
    template = STRINGS[language].get(key) or _EN.get(key) or key
    if not fmt:
        return template
    try:
        return template.format(**fmt)
    except (KeyError, IndexError, ValueError):
        try:
            return _EN.get(key, key).format(**fmt)
        except (KeyError, IndexError, ValueError):
            return template
