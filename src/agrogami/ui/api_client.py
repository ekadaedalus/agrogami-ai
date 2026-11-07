"""One typed HTTP boundary shared by UI and smoke tooling."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from uuid import UUID
from agrogami.application import Job
from agrogami.assessment import AssessmentSnapshot
from agrogami.schemas import CandidateExtraction, CanonicalEvent, FeatureSnapshot
from agrogami.ui.i18n import t

class ClientError(Exception):
    """Safe user-facing failure; never contains server response bodies."""

class APIClient:
    def __init__(self, base_url: str, token: str = "", transport=None):
        if not base_url.startswith(("http://", "https://")):
            raise ClientError(t("client.url_scheme"))
        self.base_url, self.token, self.transport = base_url.rstrip("/"), token, transport

    def request(self, method: str, path: str, payload: dict | None = None):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Agrogami-Token"] = self.token
        try:
            if self.transport is not None:
                response = self.transport.request(method, path, json=payload, headers=headers)
                if response.status_code >= 400:
                    raise ClientError(self._message(response.status_code))
                return response.json()
            request = Request(self.base_url + path, data=json.dumps(payload).encode() if payload is not None else None,
                              headers=headers, method=method)
            with urlopen(request, timeout=20) as response:
                return json.load(response)
        except HTTPError as exc:
            raise ClientError(self._message(exc.code)) from None
        except (URLError, TimeoutError, OSError):
            raise ClientError(t("client.unavailable")) from None

    @staticmethod
    def _message(status: int) -> str:
        return t(f"client.{status}") if status in (401, 403, 404, 409, 422, 503) else t("client.failed")

    def intake_sms(self, payload: dict) -> Job:
        return Job.model_validate(self.request("POST", "/api/v1/intake/sms", payload))

    def candidate(self, identifier: UUID) -> CandidateExtraction:
        return CandidateExtraction.model_validate(self.request("GET", f"/api/v1/candidates/{identifier}"))

    def events(self, applicant: UUID) -> list[CanonicalEvent]:
        return [CanonicalEvent.model_validate(v) for v in self.request("GET", f"/api/v1/applicants/{applicant}/events")]

    def assessment(self, identifier: UUID) -> AssessmentSnapshot:
        return AssessmentSnapshot.model_validate(self.request("GET", f"/api/v1/assessments/{identifier}"))
