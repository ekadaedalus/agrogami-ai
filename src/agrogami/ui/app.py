"""Streamlit underwriting evidence workflow. No financial arithmetic lives here."""
import base64
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from urllib.parse import urlencode
import streamlit as st
from agrogami.config import Settings
from agrogami.assessment import AssessmentSnapshot, SnapshotStatus
from agrogami.schemas import CanonicalEvent
from agrogami.ui.api_client import APIClient, ClientError
from agrogami.ui.samples import SCENARIOS, sample_sms, synthetic_account
from agrogami.ui.formatting import display, money, humanize, short_id, source_label, financial_summary

PAGES = ("Overview", "Applicant Evidence", "Evidence Review", "Event Ledger", "Financial Profile",
         "Assessment", "Explanation", "Fairness & Evaluation", "Audit Trail", "Documentation")

PAGE_HELPERS: dict[str, str] = {
    "Applicant Evidence": "Add financial records to begin building a traceable evidence profile.",
    "Evidence Review": "Corroborate extracted facts and preserve each reviewed version.",
    "Event Ledger": "Inspect recorded transactions and their review status.",
    "Financial Profile": "Explore verified cash flow, coverage, and financial history.",
    "Assessment": "Assess available evidence or load a previous assessment.",
    "Explanation": "See the evidence and reasons behind a stored assessment.",
    "Fairness & Evaluation": "Inspect stored research evaluations and authorized aggregate fairness reports.",
    "Audit Trail": "Trace original evidence, reviewed versions, and assessment history.",
    "Documentation": "Explore the project workflow, evidence contracts, and API reference.",
}


def technical_evidence(payload: object, context: str = "", *, codes: tuple[str, ...] = ()) -> None:
    """Keep complete authorized payloads available without leading with machine output."""
    label = "Technical evidence" + (f" — {context}" if context else "")
    with st.expander(label, expanded=False):
        for code in codes:
            st.caption(f"Audit code: {code}")
        st.json(payload)


def review_reasons(codes: tuple[str, ...]) -> None:
    for code in codes:
        st.write(humanize(code))
        if code == "AMBIGUOUS_OWNERSHIP":
            st.write("Ownership of this transaction could not be confirmed.")


def show_job(job: dict) -> None:
    st.subheader(f"Evidence status: {humanize(job['status'])}")
    review_reasons(tuple(job.get("reasons", ())))
    st.caption("Source records and original candidates remain available for evidence review.")
    technical_evidence(job, "intake record", codes=tuple(job.get("reasons", ())))


def show_event(event: CanonicalEvent) -> None:
    st.subheader(f"Evidence status: {humanize(event.validation_status)}")
    st.write(f"Amount: {money(event.amount, event.currency)}")
    st.write(f"Source: {source_label(event.source_type, event.provider)}")
    st.caption(f"{humanize(event.transaction_type)} · {event.event_timestamp.isoformat()}")
    st.caption(f"Event {short_id(event.event_id)}")
    review_reasons(event.review_reason)
    if event.supersedes_event_id:
        st.caption("Reviewed version; the original evidence remains in the audit trail.")
    technical_evidence(event.model_dump(mode="json"), "event version", codes=event.review_reason)


def show_assessment(result: AssessmentSnapshot) -> None:
    if result.display_score is None:
        if result.status == SnapshotStatus.INSUFFICIENT_EVIDENCE:
            st.subheader("Assessment withheld — Insufficient evidence")
            st.write("Agrogami does not generate a credit-risk score when the verified evidence is not sufficient to support one.")
        else:
            st.subheader("Assessment withheld")
            st.markdown(f"**{humanize(result.status)}**")
            st.write("A credit-risk score is unavailable until the evidence review and model requirements are met.")
        st.caption(f"System state: {result.status}")
        st.markdown("#### Why the assessment was withheld")
        features = result.feature_snapshot.features
        reasons = []
        balance = features.get("liquidity_floor")
        if balance is not None and balance.value is None:
            balance_coverage = features.get("balance_coverage")
            if balance_coverage is not None and balance_coverage.value == 1:
                reasons.append("Available balance evidence does not support a valid liquidity measure")
            else:
                reasons.append("Complete balance history is unavailable")
        payment = features.get("payment_punctuality")
        if payment is not None and payment.value is None:
            if "complete_obligation_denominator_unknown" in payment.reasons:
                reasons.append("Complete obligation history is unavailable")
            else:
                reasons.extend(humanize(reason) for reason in payment.reasons)
        if result.model_validation_scope != "REAL_LINKED_OUTCOME_EXPERIMENT":
            reasons.append("Representative linked borrower outcomes have not yet been established")
        reasons.extend(limitation for limitation in result.limitations
                       if any(term in limitation.lower() for term in
                              ("withheld", "unavailable", "fresh coverage")))
        for reason in dict.fromkeys(reasons):
            st.write(f"- {reason}")
    else:
        st.subheader(humanize(result.status))
        st.metric("Illustrative Project Score", display(result.display_score))
        st.caption(f"System state: {result.status}")
    st.caption(f"Artifact scope: {humanize(result.model_validation_scope)}")
    st.caption("The project-specific 300–850 mapping is not FICO, bureau-equivalent, internationally standardized, or an approval decision. Scaling does not create calibration.")
    st.caption(f"Assessment {short_id(result.assessment_id)}")
    technical_evidence(result.model_dump(mode="json"), "assessment snapshot",
                       codes=tuple(reason.code for reason in result.reasons))


def show_financial_profile(features: dict) -> None:
    summary = features["30"]["features"]
    st.caption("Last 30 days · verified evidence only; totals do not establish complete cash flow.")
    labels = ("Verified inflow", "Evidence coverage", "Payment history", "Balance history")
    for column, label, value in zip(st.columns(4), labels, financial_summary(summary)):
        column.metric(label, value)
    for name in ("payment_punctuality", "liquidity_floor"):
        if summary[name]["value"] is None:
            for reason in summary[name].get("reasons", ()):
                st.caption(humanize(reason))
    st.subheader("Detailed underwriting evidence")
    for tab, window in zip(st.tabs(["30 days", "60 days", "90 days"]), ("30", "60", "90")):
        with tab:
            snapshot = features[window]
            st.dataframe([
                {"Underwriting measure": humanize(name), "Value": display(v["value"]),
                 "Evidence notes": "; ".join(humanize(reason) for reason in v.get("reasons", ())),
                 "Contributing events": ", ".join(short_id(identifier) for identifier in v.get("contributing_event_ids", ()))}
                for name, v in snapshot["features"].items()
            ], hide_index=True, width="stretch")
            st.caption("Full feature keys and event identifiers are available in Technical evidence.")
            technical_evidence(snapshot, f"{window}-day feature snapshot")

def main() -> None:
    st.set_page_config(page_title="Agrogami AI", layout="wide")
    st.markdown("""<style>
        /* Preserve the header, toolbar and sidebar navigation controls. */
        [data-testid="stAppDeployButton"], .stDeployButton,
        [data-testid="stHeaderActionElements"], a.header-anchor {
            display:none !important;
        }
        .st-key-demo_notice [data-testid="stAlert"] {
            background-color:#fff7e6 !important;
            color:#594416 !important;
            border:1px solid #ead8ac;
            padding:.65rem .9rem;
        }
        .st-key-demo_notice [data-testid="stAlert"] [data-testid="stMarkdownContainer"],
        .st-key-demo_notice [data-testid="stAlert"] p,
        .st-key-demo_notice [data-testid="stAlert"] strong,
        .st-key-demo_notice [data-testid="stAlert"] [data-testid="stIconMaterial"] {
            color:#594416 !important;
        }
        .st-key-demo_notice [data-testid="stAlert"] p {
            font-size:.875rem;
            line-height:1.5;
        }
        </style>""", unsafe_allow_html=True)
    page = st.sidebar.radio("Navigation", PAGES)
    if page == "Overview":
        st.title("Agrogami AI")
        st.subheader("Traceable underwriting from financial records traditional credit systems ignore")
        st.caption("Turn mobile-money messages, informal ledger records, receipts, and bills into traceable financial evidence for thin-file credit assessment.")
    else:
        st.title(page)
        st.caption(PAGE_HELPERS[page])
    with st.container(key="demo_notice"):
        st.warning("**Demo environment** · Synthetic, sample, or de-identified records. Illustrative assessments are not lending decisions or validated individual creditworthiness.", icon="⚠️")
    settings = Settings()
    with st.sidebar.expander("Developer settings", expanded=False):
        api_url = st.text_input("API URL", settings.api_url) if settings.local_demo_mode else settings.api_url
        token = st.text_input("Demo credential", type="password")
        applicant_text = st.text_input("Applicant UUID", st.session_state.setdefault("applicant", str(uuid4())))
    try:
        client = APIClient(api_url, token)
        applicant = UUID(applicant_text)
        if page == "Overview":
            st.write("An explainable underwriting evidence and risk-audit workbench for thin-file credit.")
            st.write("Evidence → Candidates → Validation & Reconciliation → Canonical Ledger → Features → Risk → Calibration → Explanation → Fairness → Immutable Assessment")
            st.write("Start in Applicant Evidence, corroborate facts in Evidence Review, then inspect the Financial Profile and Assessment. Every correction preserves its original evidence.")
            st.info("Model adapter available; trained Agrogami checkpoint not installed by default. No representative linked borrower outcomes have been evaluated.")
            if st.button("Check backend readiness"):
                readiness = client.request("GET", "/ready")
                st.write(f"Backend status: {humanize(readiness['status'])}")
                technical_evidence(readiness, "backend readiness")
        elif page == "Applicant Evidence":
            scope = st.selectbox("Evidence scope", ["SYNTHETIC", "REAL/DE-IDENTIFIED"])
            scenario = st.selectbox("Synthetic scenario", list(SCENARIOS))
            text = st.text_area("SMS evidence", sample_sms(scenario) if scope == "SYNTHETIC" else "", key=f"sms-{scope}-{scenario}")
            provider = st.text_input("Provider/template", "SYNTHETIC-bKash-like" if scope == "SYNTHETIC" else "unknown")
            account_text = st.text_input("Account UUID (optional)", "") if scope != "SYNTHETIC" else ""
            if st.button("Submit SMS"):
                if scope == "SYNTHETIC" and not text.startswith("SYNTHETIC:"):
                    st.error("Synthetic evidence must retain its SYNTHETIC marker.")
                elif scope != "SYNTHETIC" and text.startswith("SYNTHETIC:"):
                    st.error("Marked synthetic evidence must use the SYNTHETIC scope.")
                else:
                    account = (synthetic_account(applicant, provider) if scope == "SYNTHETIC"
                               else UUID(account_text) if account_text.strip() else None)
                    job = client.intake_sms({"applicant_id": str(applicant), "account_id": str(account) if account else None,
                                             "text": text, "provider": provider})
                    st.session_state["job"] = job.model_dump(mode="json")
                    show_job(st.session_state["job"])
            st.caption("Raster image upload preserves source identity; no OCR inference is claimed without configured checkpoints.")
            image = st.file_uploader("Image evidence", type=["png", "jpg", "jpeg", "tiff"])
            if image and st.button("Submit image"):
                job = client.request("POST", "/api/v1/intake/document", {"applicant_id": str(applicant),
                    "content_base64": base64.b64encode(image.getvalue()).decode(), "synthetic": scope == "SYNTHETIC"})
                st.session_state["job"] = job
                show_job(job)
        elif page == "Evidence Review":
            job = st.session_state.get("job", {})
            if job:
                if job.get("event_id"):
                    technical_evidence(job, "intake record", codes=tuple(job.get("reasons", ())))
                else:
                    show_job(job)
            with st.expander("Review candidate evidence", expanded=False):
                candidate_id = st.text_input("Candidate UUID", job.get("candidate_id") or "")
            if candidate_id:
                candidate = client.candidate(UUID(candidate_id))
                source = client.request("GET", f"/api/v1/sources/{candidate.source_id}")
                st.subheader("Original extraction")
                st.caption("Extracted candidates require corroboration before they become accepted financial evidence.")
                provider = next((field.location.provider for field in candidate.fields.values() if field.location.provider), None)
                st.write(f"Source: {source_label(source['source_type'], provider, source['synthetic'])}")
                technical_evidence(candidate.model_dump(mode="json"), "original candidate")
                technical_evidence(source, "source provenance · SHA-256")
            events = client.events(applicant)
            if events:
                choices = {str(event.event_id): event for event in events}
                def event_label(identifier: str) -> str:
                    event = choices[identifier]
                    return f"{humanize(event.transaction_type)} · {money(event.amount, event.currency)} · {humanize(event.validation_status)} · {event.created_at.isoformat()}"
                event_id = st.selectbox("Event to review/correct", list(choices), format_func=event_label)
                show_event(choices[event_id])
                with st.expander("Technical evidence — corroborated changes", expanded=False):
                    changes = st.text_area("Explicit corroborated changes (JSON)", '{"ownership":"external"}')
                reason = st.text_input("Correction reason", "Synthetic ownership corroborated")
                alias = st.text_input("Demo reviewer alias", "reviewer-demo")
                if st.button("Append reviewed version"):
                    reviewed = client.request("POST", f"/api/v1/events/{event_id}/review",
                        {"changes": json.loads(changes), "reason": reason, "reviewer_alias": alias})
                    st.success("Reviewed version appended. Original evidence is preserved.")
                    show_event(CanonicalEvent.model_validate(reviewed))
            with st.expander("Technical evidence — candidate acceptance", expanded=False):
                st.caption("Candidate-only extraction can be accepted by supplying a full corroborated canonical contract.")
                event_json = st.text_area("Candidate-only canonical event JSON", "")
            if candidate_id and event_json and st.button("Accept corroborated candidate"):
                accepted = client.request("POST", f"/api/v1/candidates/{candidate_id}/review", {
                    "event": json.loads(event_json), "reason": "Explicit human corroboration", "reviewer_alias": "reviewer-demo"})
                show_event(CanonicalEvent.model_validate(accepted))
        elif page == "Event Ledger":
            events = client.events(applicant)
            if events:
                st.write(f"{len(events)} stored event versions; review states remain visible.")
            else:
                st.info("No event versions yet. Add and review evidence to begin the audit trail.")
            for event in events:
                with st.container(border=True):
                    show_event(event)
        elif page == "Financial Profile":
            now = datetime.now(timezone.utc)
            features = client.request("GET", f"/api/v1/applicants/{applicant}/features?" + urlencode({"scoring_time": now.isoformat()}))
            show_financial_profile(features)
        elif page == "Assessment":
            if st.button("Assess available evidence"):
                now = datetime.now(timezone.utc)
                result = client.request("POST", "/api/v1/assessments", {"applicant_id": str(applicant),
                    "assessment_time": now.isoformat(), "coverage": {"applicant_id": str(applicant),
                    "known_at": (now - timedelta(microseconds=1)).isoformat(), "reasons": ["no_verified_coverage_supplied"]}})
                st.session_state["assessment_id"] = result["assessment_id"]
            with st.expander("Load assessment", expanded=False):
                identifier = st.text_input("Assessment UUID", st.session_state.get("assessment_id", ""))
            if identifier:
                result = client.assessment(UUID(identifier))
                st.session_state["assessment_id"] = str(result.assessment_id)
                show_assessment(result)
        elif page == "Explanation":
            prompt = st.empty()
            with st.expander("Load assessment", expanded=False):
                identifier = st.text_input("Assessment UUID", st.session_state.get("assessment_id", ""))
            if identifier:
                result = client.request("GET", f"/api/v1/assessments/{UUID(identifier)}/explanation")
                st.session_state["assessment_id"] = str(UUID(identifier))
                for reason in result["reasons"]:
                    st.subheader(humanize(reason["code"]))
                    st.write(reason["description"])
                if result["tree_shap"] is None:
                    st.info("No supported precomputed TreeSHAP explanation is available.")
                technical_evidence(result, "explanation", codes=tuple(reason["code"] for reason in result["reasons"]))
                st.caption("SHAP is association, not causality, legal adverse-action compliance, or calibrated probability contribution.")
            else:
                prompt.info("Run an assessment on the Assessment page or load a stored assessment to view its explanation.")
        elif page == "Fairness & Evaluation":
            st.info("Not evaluated with representative linked borrower outcomes.")
            with st.expander("Advanced lookup", expanded=False):
                identifier = st.text_input("Stored evaluation UUID")
            if identifier:
                evaluation = client.request("GET", f"/api/v1/evaluations/{UUID(identifier)}")
                st.write(f"Evaluation scope: {humanize(evaluation['scope'])}")
                for limitation in evaluation["limitations"]:
                    st.caption(limitation)
                technical_evidence(evaluation, "stored evaluation")
                if st.button("Read restricted aggregate fairness"):
                    technical_evidence(client.request("GET", f"/api/v1/evaluations/{UUID(identifier)}/fairness"), "restricted aggregate fairness")
        elif page == "Audit Trail":
            st.subheader("Immutable event versions")
            events = client.events(applicant)
            if not events:
                st.info("No event versions yet. Add and review evidence to begin the audit trail.")
            for event in events:
                with st.container(border=True):
                    show_event(event)
            st.subheader("Immutable assessment history")
            history = client.request("GET", f"/api/v1/applicants/{applicant}/assessments")
            for snapshot in history:
                st.write(f"{humanize(snapshot['status'])} · {snapshot['assessment_time']} · {short_id(snapshot['assessment_id'])}")
            if not history:
                st.caption("No assessments yet. Assess available evidence to begin the assessment history.")
            technical_evidence(history, "assessment versions and predecessor links")
            st.caption("Correction appends a fresh unscored review snapshot. Original versions remain recoverable.")
            job = st.session_state.get("job", {})
            if job:
                st.subheader("Source and extraction lineage")
                technical_evidence(client.request("GET", f"/api/v1/sources/{job['source_id']}"), "source provenance · SHA-256")
                technical_evidence(job, "intake record")
                if st.button("Inspect original candidate versions (reviewer/admin)"):
                    for identifier in job.get("candidate_ids", ()):
                        technical_evidence(client.candidate(UUID(identifier)).model_dump(mode="json"), "original candidate")
        else:
            st.link_button("Open synchronized project documentation", settings.public_api_url.rstrip("/") + "/docs")
            st.link_button("Open API Swagger", settings.public_api_url.rstrip("/") + "/api/docs")
    except ClientError as exc:
        st.error(str(exc))
    except (ValueError, KeyError, TypeError):
        st.error("Invalid identifier, JSON, or response contract. Check the supplied evidence and backend version.")

if __name__ == "__main__":
    main()
