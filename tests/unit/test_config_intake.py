import hashlib
import logging
import pytest
from agrogami.config import Settings
from agrogami.events.intake import intake, log_record
from agrogami.fixtures import APPLICANT
from agrogami.schemas import SourceType


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("AGROGAMI_DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("AGROGAMI_DEMO_MODE", "false")
    monkeypatch.setenv("AGROGAMI_PRIVATE_DATA_DIR", "private_data/test")
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///:memory:"
    assert not settings.demo_mode
    assert str(settings.private_data_dir).endswith("test")


def test_demo_real_model_guard():
    with pytest.raises(ValueError):
        Settings(demo_mode=True, enable_real_models=True, _env_file=None)


def test_database_url_alias_and_precedence(monkeypatch):
    monkeypatch.delenv("AGROGAMI_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    assert Settings(_env_file=None).database_url == "sqlite:///:memory:"
    monkeypatch.setenv("AGROGAMI_DATABASE_URL", "sqlite:///private_data/preferred.db")
    assert Settings(_env_file=None).database_url.endswith("preferred.db")


def test_intake_integrity_and_safe_logging(caplog):
    body = b"SYNTHETIC confidential financial payload"
    source = intake(body, APPLICANT, SourceType.SYNTHETIC_FIXTURE, synthetic=True)
    assert source.source_hash == hashlib.sha256(body).hexdigest()
    assert source.ingestion_timestamp.tzinfo is not None
    with caplog.at_level(logging.INFO):
        log_record(logging.getLogger("agrogami"), "intake", source.source_id, "1.0")
    assert body.decode() not in caplog.text
    assert str(APPLICANT) not in caplog.text
    assert str(source.source_id) in caplog.text
    with pytest.raises(ValueError):
        log_record(logging.getLogger("agrogami"), body.decode(), source.source_id, "1.0")
