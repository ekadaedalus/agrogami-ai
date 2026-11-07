"""Streamlit underwriting evidence workflow. No financial arithmetic lives here."""
import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4
from urllib.parse import urlencode
import streamlit as st
from agrogami.config import Settings
from agrogami.assessment import AssessmentSnapshot, SnapshotStatus
from agrogami.schemas import CanonicalEvent, ValidationStatus
from agrogami.validation.rules import lineage_current_ids, reconcile
from agrogami.ui.api_client import APIClient, ClientError
from agrogami.ui.samples import SCENARIOS, sample_sms, synthetic_account
from agrogami.ui.formatting import display, money, humanize, short_id, source_label, financial_summary
from agrogami.ui.i18n import (BANGLA_FONT_IMPORT, BANGLA_FONT_RULES, DEFAULT_LANGUAGE, LANGUAGES, LANGUAGE_NAMES,
                              LANGUAGE_STATE_KEY, LANGUAGE_WIDGET_KEY, current_language, has, t)
from agrogami.synthetic.identities import DEMO_APPLICANTS, RAHIM_APPLICANT_ID
from agrogami.synthetic.ledger import next_assessment_time
from agrogami.synthetic.rahim import rahim_messages

CUSTOM_APPLICANT = "Custom applicant UUID"

PAGES = ("Overview", "Applicant Evidence", "Evidence Review", "Event Ledger", "Financial Profile",
         "Assessment", "Explanation", "Fairness & Evaluation", "Audit Trail", "Documentation")

FAVICON = Path(__file__).parent / "assets" / "favicon.png"
# Keyed selectboxes whose option labels are translated (format_func).
TRANSLATED_SELECTBOXES = ("demo_applicant", "synthetic_scenario", "review_event")


def page_icon() -> str | None:
    """Project favicon; a missing asset falls back to Streamlit's default instead of failing."""
    return str(FAVICON) if FAVICON.is_file() else None


def shown(prefix: str, value: str, lang: str | None = None) -> str:
    """Display label for an internal English identifier; the identifier itself stays the logic value."""
    return t(prefix + value, lang) if has(prefix + value) else value


def language_selector() -> None:
    """Sidebar English/Bangla switch; the choice persists in session_state across reruns."""
    def keep_choice() -> None:
        chosen = st.session_state.get(LANGUAGE_WIDGET_KEY)
        if chosen in LANGUAGES:
            st.session_state[LANGUAGE_STATE_KEY] = chosen
            # Re-assigning keeps each selection but makes the browser redraw it with the new labels;
            # otherwise a closed selectbox keeps showing the previously formatted text.
            for key in TRANSLATED_SELECTBOXES:
                if key in st.session_state:
                    st.session_state[key] = st.session_state[key]
        else:  # Deselecting a segmented control keeps the current language.
            st.session_state[LANGUAGE_WIDGET_KEY] = st.session_state.get(LANGUAGE_STATE_KEY, DEFAULT_LANGUAGE)
    st.session_state.setdefault(LANGUAGE_WIDGET_KEY, st.session_state[LANGUAGE_STATE_KEY])
    st.sidebar.segmented_control(t("sidebar.language"), LANGUAGES, format_func=LANGUAGE_NAMES.__getitem__,
                                 key=LANGUAGE_WIDGET_KEY, on_change=keep_choice)


def technical_evidence(payload: object, context: str = "", *, codes: tuple[str, ...] = ()) -> None:
    """Keep complete authorized payloads available without leading with machine output."""
    label = t("tech.label_context", context=context) if context else t("tech.label")
    with st.expander(label, expanded=False):
        for code in codes:
            st.caption(t("tech.audit_code", code=code))
        st.json(payload)


def review_reasons(codes: tuple[str, ...]) -> None:
    for code in codes:
        st.write(humanize(code))
        if code == "AMBIGUOUS_OWNERSHIP":
            st.write(t("review.ownership_unconfirmed"))


def show_job(job: dict) -> None:
    st.subheader(t("job.status", status=humanize(job['status'])))
    review_reasons(tuple(job.get("reasons", ())))
    st.caption(t("job.sources_kept"))
    technical_evidence(job, t("ctx.intake_record"), codes=tuple(job.get("reasons", ())))


def show_event(event: CanonicalEvent) -> None:
    st.subheader(t("job.status", status=humanize(event.validation_status)))
    st.write(t("event.amount", amount=money(event.amount, event.currency)))
    st.write(t("event.source", source=source_label(event.source_type, event.provider)))
    st.caption(f"{humanize(event.transaction_type)} · {event.event_timestamp.isoformat()}")
    st.caption(t("event.reference", identifier=short_id(event.event_id)))
    review_reasons(event.review_reason)
    if event.supersedes_event_id:
        st.caption(t("event.reviewed_version"))
    technical_evidence(event.model_dump(mode="json"), t("ctx.event_version"), codes=event.review_reason)


def rahim_receipt_sms() -> str:
    """Rahim's latest SYNTHETIC bKash-like customer receipt, verbatim from the demo fixture."""
    receipts = [m for m in rahim_messages(next_assessment_time()) if m.kind == "Receipt" and not m.tag
                and m.provider == "SYNTHETIC-bKash-like" and m.counterparty.startswith("SYN-CUST-")]
    return receipts[-1].text


def ledger_rows(events: list[CanonicalEvent], edge_cases_only: bool = False) -> list[dict[str, str]]:
    """Latest event versions labelled with the core reconciliation's duplicate and reversal links."""
    current_ids = lineage_current_ids(events)
    current = [event for event in events if current_ids[event.event_id] == event.event_id]
    duplicate_of = {event.event_id: event.duplicate_of_event_id for event in reconcile(current, lineage=events)}
    accepted = [event for event in current if event.validation_status == ValidationStatus.ACCEPTED]
    reversed_ids = {current_ids.get(event.reversal_of_event_id, event.reversal_of_event_id)
                    for event in accepted if event.reversal_of_event_id}
    duplicated_ids = {original for original in duplicate_of.values() if original}

    def status(event: CanonicalEvent) -> tuple[str, str]:
        """(internal state, displayed label); filtering uses the internal state only."""
        if event.validation_status != ValidationStatus.ACCEPTED:
            return "validation", humanize(event.validation_status)
        if duplicate_of.get(event.event_id):
            return "duplicate", t("ledger.duplicate")
        if event.event_id in reversed_ids:
            return "reversed", t("ledger.reversed")
        if event.reversal_of_event_id:
            return "reversal", t("ledger.reversal")
        if event.ownership == "own":
            return "own_transfer", t("ledger.own_transfer")
        return "accepted", t("ledger.accepted")
    rows = []
    for event in sorted(current, key=lambda event: (event.event_timestamp, bool(duplicate_of.get(event.event_id)))):
        state, label = status(event)
        if edge_cases_only and state == "accepted" and event.event_id not in duplicated_ids:
            continue
        wallet = event.provider or t("label.UNKNOWN")
        if wallet.startswith("SYNTHETIC-"):
            wallet = t("ledger.synthetic_wallet", name=wallet.replace("SYNTHETIC-", "", 1))
        rows.append({t("ledger.col_date"): f"{event.event_timestamp.astimezone(timezone.utc):%Y-%m-%d %H:%M}",
                     t("ledger.col_amount"): (f"{event.amount:,.2f}" if event.currency == "BDT"
                                              else money(event.amount, event.currency))
                                             if event.amount is not None else t("fmt.unavailable"),
                     t("ledger.col_direction"): humanize(event.direction),
                     t("ledger.col_wallet"): wallet,
                     t("ledger.col_status"): label})
    return rows


def show_assessment(result: AssessmentSnapshot) -> None:
    if result.display_score is None:
        if result.status == SnapshotStatus.INSUFFICIENT_EVIDENCE:
            st.subheader(t("assess.withheld_insufficient"))
            st.write(t("assess.no_score_insufficient"))
        else:
            st.subheader(t("assess.withheld"))
            st.markdown(f"**{humanize(result.status)}**")
            st.write(t("assess.no_score_pending"))
        st.caption(t("assess.system_state", status=result.status))
        st.markdown(f"#### {t('assess.why_withheld')}")
        features = result.feature_snapshot.features
        reasons = []
        balance = features.get("liquidity_floor")
        if balance is not None and balance.value is None:
            balance_coverage = features.get("balance_coverage")
            if balance_coverage is not None and balance_coverage.value == 1:
                reasons.append(t("assess.reason_liquidity_invalid"))
            else:
                reasons.append(t("assess.reason_balance_missing"))
        payment = features.get("payment_punctuality")
        if payment is not None and payment.value is None:
            if "complete_obligation_denominator_unknown" in payment.reasons:
                reasons.append(t("assess.reason_obligation_missing"))
            else:
                reasons.extend(humanize(reason) for reason in payment.reasons)
        if result.model_validation_scope != "REAL_LINKED_OUTCOME_EXPERIMENT":
            reasons.append(t("assess.reason_no_outcomes"))
        # Stored snapshot limitations are evidence text and stay in their recorded (English) wording.
        reasons.extend(limitation for limitation in result.limitations
                       if any(term in limitation.lower() for term in
                              ("withheld", "unavailable", "fresh coverage")))
        for reason in dict.fromkeys(reasons):
            st.write(f"- {reason}")
    else:
        st.subheader(humanize(result.status))
        st.metric(t("assess.score_label"), display(result.display_score))
        if result.calibrated_probability is not None and result.raw_probability is not None:
            st.caption(t("assess.probability", calibrated=f"{result.calibrated_probability:.2%}",
                         raw=f"{result.raw_probability:.2%}"))
        st.caption(t("assess.system_state", status=result.status))
    st.caption(t("assess.artifact_scope", scope=humanize(result.model_validation_scope)))
    st.caption(t("assess.scale_disclaimer"))
    st.caption(t("assess.reference", identifier=short_id(result.assessment_id)))
    technical_evidence(result.model_dump(mode="json"), t("ctx.assessment_snapshot"),
                       codes=tuple(reason.code for reason in result.reasons))


def show_financial_profile(features: dict) -> None:
    summary = features["30"]["features"]
    st.caption(t("profile.last30"))
    labels = (t("profile.verified_inflow"), t("profile.evidence_coverage"),
              t("profile.payment_history"), t("profile.balance_history"))
    for column, label, value in zip(st.columns(4), labels, financial_summary(summary)):
        column.metric(label, value)
    for name in ("payment_punctuality", "liquidity_floor"):
        if summary[name]["value"] is None:
            for reason in summary[name].get("reasons", ()):
                st.caption(humanize(reason))
    st.subheader(t("profile.detailed"))
    windows = ("30", "60", "90")
    for tab, window in zip(st.tabs([t("profile.tab_days", days=window) for window in windows]), windows):
        with tab:
            snapshot = features[window]
            st.dataframe([
                {t("profile.col_measure"): humanize(name), t("profile.col_value"): display(v["value"]),
                 t("profile.col_notes"): "; ".join(humanize(reason) for reason in v.get("reasons", ())),
                 t("profile.col_events"): ", ".join(short_id(identifier)
                                                    for identifier in v.get("contributing_event_ids", ()))}
                for name, v in snapshot["features"].items()
            ], hide_index=True, width="stretch")
            st.caption(t("profile.full_keys"))
            technical_evidence(snapshot, t("ctx.feature_snapshot", window=window))

def main() -> None:
    st.set_page_config(page_title="Agrogami AI", layout="wide", page_icon=page_icon())
    st.session_state.setdefault(LANGUAGE_STATE_KEY, DEFAULT_LANGUAGE)
    bangla = current_language() == "bn"
    st.markdown("<style>" + (BANGLA_FONT_IMPORT if bangla else "") + """
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
        """ + (BANGLA_FONT_RULES if bangla else "") + "</style>", unsafe_allow_html=True)
    language_selector()
    lang = current_language()  # format_func closures keep the language they were rendered with.
    page = st.sidebar.radio(t("sidebar.navigation"), PAGES, format_func=lambda name: shown("page.", name, lang),
                            key="nav_page")
    if page == "Overview":
        st.title("Agrogami AI")
        st.subheader(t("overview.subtitle"))
        st.caption(t("overview.caption"))
    else:
        st.title(shown("page.", page))
        st.caption(t("helper." + page))
    with st.container(key="demo_notice"):
        st.warning(t("demo.notice"), icon="⚠️")
    settings = Settings()
    choice = st.sidebar.selectbox(t("sidebar.demo_applicant"), (CUSTOM_APPLICANT, *DEMO_APPLICANTS),
                                  format_func=lambda name: shown("applicant.", name, lang), key="demo_applicant")
    previous_choice = st.session_state.get("selected_demo")
    if previous_choice is not None and previous_choice != choice:
        # Switching applicants must not carry another applicant's assessment or intake job forward.
        for stale in ("assessment_id", "job"):
            st.session_state.pop(stale, None)
    st.session_state["selected_demo"] = choice
    if choice in DEMO_APPLICANTS:
        st.session_state["applicant"] = str(DEMO_APPLICANTS[choice])
    with st.sidebar.expander(t("sidebar.developer_settings"), expanded=False):
        api_url = (st.text_input(t("sidebar.api_url"), settings.api_url, key="api_url")
                   if settings.local_demo_mode else settings.api_url)
        token = st.text_input(t("sidebar.demo_credential"), type="password", key="demo_credential")
        applicant_default = st.session_state.setdefault("applicant", str(uuid4()))
        # The key follows the default so a newly selected applicant still refreshes the field,
        # while a language switch (label change only) keeps what was typed.
        applicant_text = st.text_input(t("sidebar.applicant_uuid"), applicant_default,
                                       key=f"applicant_uuid:{applicant_default}")
    try:
        client = APIClient(api_url, token)
        applicant = DEMO_APPLICANTS[choice] if choice in DEMO_APPLICANTS else UUID(applicant_text)

        def latest_stored_assessment() -> None:
            """Demo applicants open on their most recent stored assessment."""
            if choice in DEMO_APPLICANTS and not st.session_state.get("assessment_id"):
                history = client.request("GET", f"/api/v1/applicants/{applicant}/assessments")
                if history:
                    st.session_state["assessment_id"] = history[-1]["assessment_id"]
        if page == "Overview":
            st.write(t("overview.positioning"))
            st.write(t("overview.pipeline"))
            st.write(t("overview.start"))
            try:
                readiness = client.request("GET", "/ready")
            except ClientError:
                readiness = None
            if readiness and readiness.get("optional_models", {}).get("risk"):
                st.info(t("overview.model_active"))
            else:
                st.info(t("overview.model_adapter"))
            if st.button(t("overview.check_ready"), key="check_readiness"):
                readiness = client.request("GET", "/ready")
                st.write(t("overview.backend_status", status=humanize(readiness['status'])))
                technical_evidence(readiness, t("ctx.backend_readiness"))
        elif page == "Applicant Evidence":
            scope = st.selectbox(t("intake.scope"), ["SYNTHETIC", "REAL/DE-IDENTIFIED"], key="evidence_scope")
            scenario = st.selectbox(t("intake.scenario"), list(SCENARIOS),
                                    format_func=lambda name: shown("scenario.", name, lang), key="synthetic_scenario")
            rahim = applicant == RAHIM_APPLICANT_ID and scenario == "External inflow"
            prefill = rahim_receipt_sms() if rahim else sample_sms(scenario)
            text = st.text_area(t("intake.sms"), prefill if scope == "SYNTHETIC" else "",
                                key=f"sms-{scope}-{scenario}" + ("-rahim" if rahim else ""))
            if lang == "bn":
                st.caption(t("intake.sms_english_note"))
            provider = st.text_input(t("intake.provider"), "SYNTHETIC-bKash-like" if scope == "SYNTHETIC" else "unknown",
                                     key=f"provider:{scope}")
            account_text = (st.text_input(t("intake.account"), "", key="account_uuid")
                            if scope != "SYNTHETIC" else "")
            if st.button(t("intake.submit_sms"), key="submit_sms"):
                if scope == "SYNTHETIC" and not text.startswith("SYNTHETIC:"):
                    st.error(t("intake.marker_required"))
                elif scope != "SYNTHETIC" and text.startswith("SYNTHETIC:"):
                    st.error(t("intake.marker_scope"))
                else:
                    account = (synthetic_account(applicant, provider) if scope == "SYNTHETIC"
                               else UUID(account_text) if account_text.strip() else None)
                    job = client.intake_sms({"applicant_id": str(applicant), "account_id": str(account) if account else None,
                                             "text": text, "provider": provider})
                    st.session_state["job"] = job.model_dump(mode="json")
                    show_job(st.session_state["job"])
            st.caption(t("intake.image_caption"))
            image = st.file_uploader(t("intake.image"), type=["png", "jpg", "jpeg", "tiff"], key="image_evidence")
            if image and st.button(t("intake.submit_image"), key="submit_image"):
                job = client.request("POST", "/api/v1/intake/document", {"applicant_id": str(applicant),
                    "content_base64": base64.b64encode(image.getvalue()).decode(), "synthetic": scope == "SYNTHETIC"})
                st.session_state["job"] = job
                show_job(job)
        elif page == "Evidence Review":
            job = st.session_state.get("job", {})
            if job:
                if job.get("event_id"):
                    technical_evidence(job, t("ctx.intake_record"), codes=tuple(job.get("reasons", ())))
                else:
                    show_job(job)
            with st.expander(t("review.candidate_expander"), expanded=False):
                candidate_default = job.get("candidate_id") or ""
                candidate_id = st.text_input(t("review.candidate_uuid"), candidate_default,
                                             key=f"candidate_uuid:{candidate_default}")
            if candidate_id:
                candidate = client.candidate(UUID(candidate_id))
                source = client.request("GET", f"/api/v1/sources/{candidate.source_id}")
                st.subheader(t("review.original_extraction"))
                st.caption(t("review.candidates_need_corroboration"))
                provider = next((field.location.provider for field in candidate.fields.values() if field.location.provider), None)
                st.write(t("event.source", source=source_label(source['source_type'], provider, source['synthetic'])))
                technical_evidence(candidate.model_dump(mode="json"), t("ctx.original_candidate"))
                technical_evidence(source, t("ctx.source_provenance"))
            events = client.events(applicant)
            if events:
                choices = {str(event.event_id): event for event in events}
                def event_label(identifier: str) -> str:
                    event = choices[identifier]
                    return f"{humanize(event.transaction_type)} · {money(event.amount, event.currency)} · {humanize(event.validation_status)} · {event.created_at.isoformat()}"
                event_id = st.selectbox(t("review.event_select"), list(choices), format_func=event_label,
                                        key="review_event")
                show_event(choices[event_id])
                with st.expander(t("tech.label_context", context=t("ctx.corroborated_changes")), expanded=False):
                    changes = st.text_area(t("review.changes"), '{"ownership":"external"}', key="review_changes")
                reason = st.text_input(t("review.reason"), "Synthetic ownership corroborated", key="review_reason")
                alias = st.text_input(t("review.alias"), "reviewer-demo", key="review_alias")
                if st.button(t("review.append"), key="append_review"):
                    reviewed = client.request("POST", f"/api/v1/events/{event_id}/review",
                        {"changes": json.loads(changes), "reason": reason, "reviewer_alias": alias})
                    st.success(t("review.appended"))
                    show_event(CanonicalEvent.model_validate(reviewed))
            with st.expander(t("tech.label_context", context=t("ctx.candidate_acceptance")), expanded=False):
                st.caption(t("review.candidate_only_caption"))
                event_json = st.text_area(t("review.candidate_json"), "", key="candidate_event_json")
            if candidate_id and event_json and st.button(t("review.accept_candidate"), key="accept_candidate"):
                accepted = client.request("POST", f"/api/v1/candidates/{candidate_id}/review", {
                    "event": json.loads(event_json), "reason": "Explicit human corroboration", "reviewer_alias": "reviewer-demo"})
                show_event(CanonicalEvent.model_validate(accepted))
        elif page == "Event Ledger":
            events = client.events(applicant)
            if events:
                st.write(t("ledger.count", count=len(events)))
                edge_only = st.checkbox(t("ledger.edge_only"), value=True, key="ledger_edge_only")
                st.dataframe(ledger_rows(events, edge_only), hide_index=True, width="stretch")
                st.caption(t("ledger.caption"))
            else:
                st.info(t("empty.no_events"))
            for event in events:
                with st.container(border=True):
                    show_event(event)
        elif page == "Financial Profile":
            stored = client.request("GET", f"/api/v1/applicants/{applicant}/feature-snapshots")
            latest = max((snapshot["scoring_time"] for snapshot in stored), default=None)
            chosen = {str(snapshot["window_days"]): snapshot for snapshot in stored if snapshot["scoring_time"] == latest}
            if set(chosen) == {"30", "60", "90"}:
                st.caption(t("profile.stored_as_of", time=latest))
                features = chosen
            else:
                now = datetime.now(timezone.utc)
                features = client.request("GET", f"/api/v1/applicants/{applicant}/features?" + urlencode({"scoring_time": now.isoformat()}))
            show_financial_profile(features)
        elif page == "Assessment":
            latest_stored_assessment()
            if st.button(t("assess.run"), key="run_assessment"):
                now = datetime.now(timezone.utc)
                result = client.request("POST", "/api/v1/assessments", {"applicant_id": str(applicant),
                    "assessment_time": now.isoformat(), "coverage": {"applicant_id": str(applicant),
                    "known_at": (now - timedelta(microseconds=1)).isoformat(), "reasons": ["no_verified_coverage_supplied"]}})
                st.session_state["assessment_id"] = result["assessment_id"]
            with st.expander(t("assess.load"), expanded=False):
                assessment_default = st.session_state.get("assessment_id", "")
                identifier = st.text_input(t("assess.uuid"), assessment_default,
                                           key=f"assessment_uuid:{page}:{assessment_default}")
            if identifier:
                result = client.assessment(UUID(identifier))
                st.session_state["assessment_id"] = str(result.assessment_id)
                show_assessment(result)
        elif page == "Explanation":
            latest_stored_assessment()
            prompt = st.empty()
            with st.expander(t("assess.load"), expanded=False):
                assessment_default = st.session_state.get("assessment_id", "")
                identifier = st.text_input(t("assess.uuid"), assessment_default,
                                           key=f"assessment_uuid:{page}:{assessment_default}")
            if identifier:
                result = client.request("GET", f"/api/v1/assessments/{UUID(identifier)}/explanation")
                st.session_state["assessment_id"] = str(UUID(identifier))
                for reason in result["reasons"]:
                    st.subheader(humanize(reason["code"]))
                    st.write(reason["description"])
                if result["tree_shap"] is None:
                    st.info(t("explain.no_tree_shap"))
                else:
                    shap = result["tree_shap"]
                    st.subheader(t("explain.tree_shap"))
                    ranked = sorted(shap["contributions"].items(), key=lambda item: -abs(item[1]))
                    st.dataframe([{t("explain.col_input"): humanize(name),
                                   t("explain.col_contribution"): round(value, 4),
                                   t("explain.col_direction"): (t("explain.raises") if value > 0 else
                                                                t("explain.lowers") if value < 0 else
                                                                t("explain.no_effect"))}
                                  for name, value in ranked], hide_index=True, width="stretch")
                    st.caption(t("explain.base_value", base=f"{shap['base_value']:.4f}",
                                 background=shap['background_identity']))
                technical_evidence(result, t("ctx.explanation"), codes=tuple(reason["code"] for reason in result["reasons"]))
                st.caption(t("explain.shap_disclaimer"))
            else:
                prompt.info(t("explain.prompt"))
        elif page == "Fairness & Evaluation":
            st.info(t("fair.not_evaluated"))
            with st.expander(t("fair.advanced"), expanded=False):
                identifier = st.text_input(t("fair.evaluation_uuid"), key="evaluation_uuid")
            if identifier:
                evaluation = client.request("GET", f"/api/v1/evaluations/{UUID(identifier)}")
                st.write(t("fair.scope", scope=humanize(evaluation['scope'])))
                for limitation in evaluation["limitations"]:
                    st.caption(limitation)
                technical_evidence(evaluation, t("ctx.stored_evaluation"))
                if st.button(t("fair.read_restricted"), key="read_fairness"):
                    technical_evidence(client.request("GET", f"/api/v1/evaluations/{UUID(identifier)}/fairness"),
                                       t("ctx.restricted_fairness"))
        elif page == "Audit Trail":
            st.subheader(t("audit.event_versions"))
            events = client.events(applicant)
            if not events:
                st.info(t("empty.no_events"))
            for event in events:
                with st.container(border=True):
                    show_event(event)
            st.subheader(t("audit.assessment_history"))
            history = client.request("GET", f"/api/v1/applicants/{applicant}/assessments")
            for snapshot in history:
                st.write(f"{humanize(snapshot['status'])} · {snapshot['assessment_time']} · {short_id(snapshot['assessment_id'])}")
            if not history:
                st.caption(t("audit.no_assessments"))
            technical_evidence(history, t("ctx.assessment_versions"))
            st.caption(t("audit.correction_note"))
            job = st.session_state.get("job", {})
            if job:
                st.subheader(t("audit.lineage"))
                technical_evidence(client.request("GET", f"/api/v1/sources/{job['source_id']}"), t("ctx.source_provenance"))
                technical_evidence(job, t("ctx.intake_record"))
                if st.button(t("audit.inspect_candidates"), key="inspect_candidates"):
                    for identifier in job.get("candidate_ids", ()):
                        technical_evidence(client.candidate(UUID(identifier)).model_dump(mode="json"),
                                           t("ctx.original_candidate"))
        else:
            st.link_button(t("docs.open_project"), settings.public_api_url.rstrip("/") + "/docs")
            st.link_button(t("docs.open_swagger"), settings.public_api_url.rstrip("/") + "/api/docs")
    except ClientError as exc:
        st.error(str(exc))
    except (ValueError, KeyError, TypeError):
        st.error(t("error.invalid_input"))

if __name__ == "__main__":
    main()
