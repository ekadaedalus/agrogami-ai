"""Stable identifiers of the SYNTHETIC demo applicants (no heavy imports; used by the UI)."""
from uuid import UUID, uuid5, NAMESPACE_URL

RAHIM_APPLICANT_ID = uuid5(NAMESPACE_URL, "agrogami-synthetic:applicant:rahim-furniture-workshop-v1")
# Existing abstention-demo applicant; recreated with this fixed UUID by scripts/build_demo.py.
ABSTENTION_APPLICANT_ID = UUID("fcba6da1-0b92-4a08-a776-664830b25a37")

DEMO_APPLICANTS = {
    "Rahim — synthetic furniture workshop (scored)": RAHIM_APPLICANT_ID,
    "Abstention demo — insufficient evidence": ABSTENTION_APPLICANT_ID,
}
