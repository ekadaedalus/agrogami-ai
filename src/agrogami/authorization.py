"""Minimal shared role/applicant boundary; not production identity or tenancy."""
from dataclasses import dataclass
from enum import StrEnum
import hmac
from typing import Mapping
from uuid import UUID

from agrogami.config import Settings
from agrogami.schemas import Source
from agrogami.storage import SourceRow, Store
from sqlalchemy import select
from sqlalchemy.orm import Session


class Role(StrEnum):
    viewer = "viewer"
    reviewer = "reviewer"
    admin = "admin"


CAPABILITIES = {
    Role.viewer: frozenset({"read"}),
    Role.reviewer: frozenset({"read", "intake", "review", "assess", "fairness"}),
    Role.admin: frozenset({"read", "intake", "review", "assess", "fairness"}),
}


@dataclass(frozen=True)
class Principal:
    role: Role
    applicants: frozenset[UUID] = frozenset()
    authenticated: bool = True
    local_demo: bool = False

    def can(self, capability: str) -> bool:
        return capability in CAPABILITIES[self.role]

    def allows_applicant(self, applicant_id: UUID) -> bool:
        # Admin is an explicit dataset-wide grant; nonadmins default to no applicants.
        return self.local_demo or self.role == Role.admin or applicant_id in self.applicants


def can_access_applicant(principal: Principal, applicant_id: UUID, store: Store) -> bool:
    if not principal.allows_applicant(applicant_id):
        return False
    if principal.authenticated:
        return True
    # Anonymous convenience is limited to explicitly marked synthetic sources,
    # including candidates that have not yet produced a canonical event.
    with Session(store.engine) as session:
        sources = session.scalars(select(SourceRow.payload).where(SourceRow.applicant_id == str(applicant_id)))
        return all(Source.model_validate_json(payload).synthetic for payload in sources)


def authenticate(supplied: str | None, settings: Settings, *,
                 tokens: Mapping[str, str] | None = None, prism: bool = False) -> Principal | None:
    if not supplied:
        return None
    configured = settings.demo_tokens if tokens is None else tokens
    for token, role in configured.items():
        if hmac.compare_digest(supplied.encode(), token.encode()):
            return Principal(Role(role), frozenset(settings.applicant_grants.get(token, ())),
                             local_demo=settings.local_demo_mode)
    if prism and settings.mcp_auth_token and hmac.compare_digest(supplied.encode(), settings.mcp_auth_token.encode()):
        return Principal(Role.viewer, frozenset(settings.applicant_grants.get(settings.mcp_auth_token, ())),
                         local_demo=settings.local_demo_mode)
    return None
