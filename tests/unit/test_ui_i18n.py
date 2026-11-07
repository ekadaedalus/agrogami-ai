"""Interface-text localization: key parity, fallbacks, placeholders and unchanged logic identifiers."""
from pathlib import Path

import pytest

from agrogami.ui import i18n
from agrogami.ui.i18n import LANGUAGE_STATE_KEY, STRINGS, placeholders, t

ROOT = Path(__file__).resolve().parents[2]
RAHIM = "Rahim — synthetic furniture workshop (scored)"


def test_every_english_key_has_bangla_and_vice_versa():
    assert set(STRINGS["en"]) - set(STRINGS["bn"]) == set()
    assert set(STRINGS["bn"]) - set(STRINGS["en"]) == set()


@pytest.mark.parametrize("language", ["en", "bn"])
def test_no_empty_strings(language):
    assert [key for key, value in STRINGS[language].items() if not value.strip()] == []


def test_format_placeholders_match_between_languages():
    mismatched = {key: (placeholders(STRINGS["en"][key]), placeholders(STRINGS["bn"][key]))
                  for key in STRINGS["en"] if placeholders(STRINGS["en"][key]) != placeholders(STRINGS["bn"][key])}
    assert mismatched == {}


def test_missing_bangla_key_falls_back_to_english(monkeypatch):
    monkeypatch.delitem(STRINGS["bn"], "assess.run")
    assert t("assess.run", "bn") == STRINGS["en"]["assess.run"]
    assert t("job.status", "bn", status="X") == "প্রমাণের অবস্থা: X"


def test_missing_key_and_bad_format_never_raise():
    assert t("no.such.key") == "no.such.key"
    assert t("no.such.key", "bn", value=1) == "no.such.key"
    assert t("job.status", "bn") == STRINGS["bn"]["job.status"]  # unfilled placeholder left as-is
    assert t("job.status", "en", wrong=1) == STRINGS["en"]["job.status"]


def test_default_language_is_english_outside_streamlit():
    assert i18n.current_language() == "en"
    assert t("fmt.unavailable") == "Unavailable"


def test_logic_identifiers_unchanged_and_all_displayed_values_translated():
    from agrogami.synthetic.identities import DEMO_APPLICANTS
    from agrogami.ui.app import CUSTOM_APPLICANT, PAGES
    from agrogami.ui.samples import SCENARIOS
    assert PAGES == ("Overview", "Applicant Evidence", "Evidence Review", "Event Ledger", "Financial Profile",
                     "Assessment", "Explanation", "Fairness & Evaluation", "Audit Trail", "Documentation")
    assert list(SCENARIOS) == ["External inflow", "External outflow", "Send money", "Cash in", "Cash out",
                               "Reversal requiring linking"]
    assert CUSTOM_APPLICANT == "Custom applicant UUID"
    for page in PAGES:
        assert STRINGS["en"]["page." + page] == page
        assert page == "Overview" or "helper." + page in STRINGS["bn"]
    for scenario in SCENARIOS:
        assert STRINGS["en"]["scenario." + scenario] == scenario
    for name in (CUSTOM_APPLICANT, *DEMO_APPLICANTS):
        assert STRINGS["en"]["applicant." + name] == name


def test_language_switch_keeps_selection_credential_page_and_session(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from agrogami.ui.api_client import APIClient, ClientError

    def offline(self, method, path, payload=None):
        raise ClientError("offline test backend")
    monkeypatch.setattr(APIClient, "request", offline)
    app = AppTest.from_file(str(ROOT / "src" / "agrogami" / "ui" / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert app.session_state[LANGUAGE_STATE_KEY] == "en"
    app.sidebar.selectbox[0].set_value(RAHIM).run()
    next(field for field in app.sidebar.text_input if field.label == "Demo credential").set_value("synthetic-cred")
    app.sidebar.radio[0].set_value("Documentation").run()
    app.session_state["job"] = {"job_id": "kept"}
    app.session_state["assessment_id"] = "kept-assessment"
    app.run()

    app.sidebar.segmented_control[0].set_value("bn").run()
    assert not app.exception
    assert app.session_state[LANGUAGE_STATE_KEY] == "bn"
    assert app.title[0].value == "ডকুমেন্টেশন"
    assert app.sidebar.radio[0].value == "Documentation"
    assert app.sidebar.selectbox[0].value == RAHIM
    credential = next(field for field in app.sidebar.text_input if field.label == "ডেমো ক্রেডেনশিয়াল (টোকেন)")
    assert credential.value == "synthetic-cred"
    assert app.session_state["job"] == {"job_id": "kept"}
    assert app.session_state["assessment_id"] == "kept-assessment"
    assert "ডেমো পরিবেশ" in app.warning[0].value

    app.sidebar.segmented_control[0].set_value("en").run()
    assert not app.exception
    assert app.title[0].value == "Documentation"
    assert app.sidebar.selectbox[0].value == RAHIM
    assert next(field for field in app.sidebar.text_input if field.label == "Demo credential").value == "synthetic-cred"


def test_bangla_applicant_evidence_keeps_english_sms_and_notes_it(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from agrogami.ui.api_client import APIClient, ClientError

    def offline(self, method, path, payload=None):
        raise ClientError("offline test backend")
    monkeypatch.setattr(APIClient, "request", offline)
    app = AppTest.from_file(str(ROOT / "src" / "agrogami" / "ui" / "app.py"), default_timeout=30).run()
    app.sidebar.segmented_control[0].set_value("bn").run()
    app.sidebar.radio[0].set_value("Applicant Evidence").run()
    assert not app.exception
    assert app.text_area[0].value.startswith("SYNTHETIC: ")
    assert STRINGS["bn"]["intake.sms_english_note"] in [caption.value for caption in app.caption]
    assert next(box for box in app.selectbox if box.label == "সিন্থেটিক উদাহরণ").value == "External inflow"
