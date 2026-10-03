"""Streamlit research workflow. No financial arithmetic lives here."""
import base64
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from urllib.parse import urlencode
import streamlit as st
from agrogami.config import Settings
from agrogami.ui.api_client import APIClient, ClientError
from agrogami.ui.samples import SCENARIOS, sample_sms
from agrogami.ui.formatting import display

PAGES = ("Overview", "Intake / Samples", "Evidence Review", "Event Ledger", "Feature Summary",
         "Assessment", "Explanation", "Evaluation / Fairness", "Audit / Versions", "Documentation")

def main() -> None:
    st.set_page_config(page_title="Agrogami AI", layout="wide")
    st.title("Agrogami AI — Research Prototype")
    st.caption("A Multimodal Framework for Fair and Explainable Alternative Credit Scoring from Unstructured Mobile and Paper Records")
    st.warning("This demonstration uses sample, synthetic, or de-identified financial records. Illustrative assessment outputs are not lending decisions and do not represent validated individual creditworthiness.")
    settings = Settings()
    api_url = st.sidebar.text_input("API URL", settings.api_url)
    token = st.sidebar.text_input("Demo credential", type="password")
    applicant_text = st.sidebar.text_input("Applicant UUID", st.session_state.setdefault("applicant", str(uuid4())))
    page = st.sidebar.radio("Navigation", PAGES)
    try:
        client = APIClient(api_url, token)
        applicant = UUID(applicant_text)
        if page == "Overview":
            st.write("Evidence → Candidates → Validation & Reconciliation → Canonical Ledger → Features → Risk → Calibration → Explanation → Fairness → Immutable Assessment")
            st.info("Model adapter available; trained Agrogami checkpoint not installed by default. No representative linked borrower outcomes have been evaluated.")
            if st.button("Check backend readiness"):
                st.json(client.request("GET", "/ready"))
        elif page == "Intake / Samples":
            scope = st.selectbox("Evidence scope", ["SYNTHETIC", "REAL/DE-IDENTIFIED"])
            scenario = st.selectbox("Synthetic scenario", list(SCENARIOS))
            text = st.text_area("SMS evidence", sample_sms(scenario) if scope == "SYNTHETIC" else "", key=f"sms-{scope}-{scenario}")
            provider = st.text_input("Provider/template", "SYNTHETIC-bKash-like" if scope == "SYNTHETIC" else "unknown")
            if st.button("Submit SMS"):
                if scope == "SYNTHETIC" and not text.startswith("SYNTHETIC:"):
                    st.error("Synthetic evidence must retain its SYNTHETIC marker.")
                elif scope != "SYNTHETIC" and text.startswith("SYNTHETIC:"):
                    st.error("Marked synthetic evidence must use the SYNTHETIC scope.")
                else:
                    job = client.intake_sms({"applicant_id": str(applicant), "account_id": str(uuid4()), "text": text, "provider": provider})
                    st.session_state["job"] = job.model_dump(mode="json")
                    st.json(st.session_state["job"])
            st.caption("Raster image upload preserves source identity; no OCR inference is claimed without configured checkpoints.")
            image = st.file_uploader("Image evidence", type=["png", "jpg", "jpeg", "tiff"])
            if image and st.button("Submit image"):
                job = client.request("POST", "/api/v1/intake/document", {"applicant_id": str(applicant),
                    "content_base64": base64.b64encode(image.getvalue()).decode(), "synthetic": scope == "SYNTHETIC"})
                st.session_state["job"] = job
                st.json(job)
        elif page == "Evidence Review":
            job = st.session_state.get("job", {})
            if job:
                st.json(job)
            candidate_id = st.text_input("Candidate UUID", job.get("candidate_id") or "")
            if candidate_id:
                candidate = client.candidate(UUID(candidate_id))
                st.json(candidate.model_dump(mode="json"))
                st.json(client.request("GET", f"/api/v1/sources/{candidate.source_id}"))
            events = client.events(applicant)
            if events:
                event_id = st.selectbox("Event to review/correct", [str(e.event_id) for e in events])
                st.json(next(e.model_dump(mode="json") for e in events if str(e.event_id) == event_id))
                changes = st.text_area("Explicit corroborated changes (JSON)", '{"ownership":"external"}')
                reason = st.text_input("Correction reason", "Synthetic ownership corroborated")
                alias = st.text_input("Demo reviewer alias", "reviewer-demo")
                if st.button("Append reviewed version"):
                    st.json(client.request("POST", f"/api/v1/events/{event_id}/review",
                        {"changes": json.loads(changes), "reason": reason, "reviewer_alias": alias}))
            st.caption("Candidate-only extraction can be accepted by supplying a full corroborated canonical contract.")
            event_json = st.text_area("Candidate-only canonical event JSON", "")
            if candidate_id and event_json and st.button("Accept corroborated candidate"):
                st.json(client.request("POST", f"/api/v1/candidates/{candidate_id}/review", {
                    "event": json.loads(event_json), "reason": "Explicit human corroboration", "reviewer_alias": "reviewer-demo"}))
        elif page == "Event Ledger":
            events = client.events(applicant)
            st.write(f"{len(events)} stored event versions; review states remain visible.")
            for event in events:
                with st.expander(f"{event.validation_status} · {event.event_id}"):
                    st.json(event.model_dump(mode="json"))
        elif page == "Feature Summary":
            now = datetime.now(timezone.utc)
            features = client.request("GET", f"/api/v1/applicants/{applicant}/features?" + urlencode({"scoring_time": now.isoformat()}))
            for tab, window in zip(st.tabs(["30 days", "60 days", "90 days"]), ("30", "60", "90")):
                with tab:
                    snapshot = features[window]
                    st.dataframe([{"feature": name, "value": display(v["value"], tuple(v.get("reasons", ()))),
                                   "contributors": ", ".join(v.get("contributing_event_ids", ()))} for name, v in snapshot["features"].items()])
                    st.json(snapshot)
        elif page == "Assessment":
            st.info("The project-specific 300–850 mapping is not FICO, bureau-equivalent, internationally standardized, or an approval decision. Scaling does not create calibration.")
            if st.button("Create assessment with unknown coverage"):
                now = datetime.now(timezone.utc)
                result = client.request("POST", "/api/v1/assessments", {"applicant_id": str(applicant),
                    "assessment_time": now.isoformat(), "coverage": {"applicant_id": str(applicant),
                    "known_at": (now - timedelta(microseconds=1)).isoformat(), "reasons": ["no_verified_coverage_supplied"]}})
                st.session_state["assessment_id"] = result["assessment_id"]
            identifier = st.text_input("Assessment UUID", st.session_state.get("assessment_id", ""))
            if identifier:
                result = client.assessment(UUID(identifier))
                st.subheader(str(result.status))
                st.metric("Illustrative Project Score", display(result.display_score))
                st.json(result.model_dump(mode="json"))
        elif page == "Explanation":
            identifier = st.text_input("Assessment UUID", st.session_state.get("assessment_id", ""))
            if identifier:
                result = client.request("GET", f"/api/v1/assessments/{UUID(identifier)}/explanation")
                st.json(result)
                if result["tree_shap"] is None:
                    st.info("No supported precomputed TreeSHAP explanation is available.")
            st.caption("SHAP is association, not causality, legal adverse-action compliance, or calibrated probability contribution.")
        elif page == "Evaluation / Fairness":
            st.info("Not evaluated with representative linked borrower outcomes.")
            identifier = st.text_input("Stored evaluation UUID")
            if identifier:
                st.json(client.request("GET", f"/api/v1/evaluations/{UUID(identifier)}"))
                if st.button("Read restricted aggregate fairness"):
                    st.json(client.request("GET", f"/api/v1/evaluations/{UUID(identifier)}/fairness"))
        elif page == "Audit / Versions":
            job = st.session_state.get("job", {})
            if job:
                st.subheader("Source and extraction lineage")
                st.json(client.request("GET", f"/api/v1/sources/{job['source_id']}"))
                st.json(job)
                if st.button("Inspect original candidate versions (reviewer/admin)"):
                    for identifier in job.get("candidate_ids", ()):
                        st.json(client.candidate(UUID(identifier)).model_dump(mode="json"))
            st.subheader("Immutable event versions")
            for event in client.events(applicant):
                st.json(event.model_dump(mode="json"))
            st.subheader("Immutable assessment history")
            st.json(client.request("GET", f"/api/v1/applicants/{applicant}/assessments"))
            st.caption("Correction appends a fresh unscored review snapshot. Original versions remain recoverable.")
        else:
            st.link_button("Open synchronized project documentation", settings.public_api_url.rstrip("/") + "/docs")
            st.link_button("Open API Swagger", settings.public_api_url.rstrip("/") + "/api/docs")
    except ClientError as exc:
        st.error(str(exc))
    except (ValueError, KeyError, TypeError):
        st.error("Invalid identifier, JSON, or response contract. Check the supplied evidence and backend version.")

if __name__ == "__main__":
    main()
