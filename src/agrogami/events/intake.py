"""Intake computes integrity metadata without logging financial content."""
import hashlib
import json
import logging
from uuid import UUID
from agrogami.schemas import Source, SourceType


def intake(content: bytes, applicant_id: UUID, source_type: SourceType,
           *, synthetic: bool = False, metadata: dict[str, str] | None = None) -> Source:
    return Source(applicant_id=applicant_id, source_type=source_type,
                  source_hash=hashlib.sha256(content).hexdigest(), synthetic=synthetic,
                  metadata=metadata or {})


def log_record(logger: logging.Logger, operation: str, record_id: UUID, version: str) -> None:
    """Fixed operation vocabulary and UUID-only identity prevent arbitrary payload logging."""
    if operation not in {"intake", "persist", "correct", "features"}:
        raise ValueError("unsupported log operation")
    if not isinstance(record_id, UUID) or version not in {"1.0"}:
        raise ValueError("unsafe logging metadata")
    logger.info(json.dumps({"operation": operation, "record_id": str(record_id), "version": version}))
