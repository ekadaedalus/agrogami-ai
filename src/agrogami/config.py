"""Central configuration; no model execution is implemented."""
from pathlib import Path
from uuid import UUID
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGROGAMI_", env_file=".env", extra="ignore", populate_by_name=True)
    env: str = "development"
    database_url: str = Field(default="sqlite:///private_data/agrogami.db", repr=False,
                              validation_alias=AliasChoices("AGROGAMI_DATABASE_URL", "DATABASE_URL"))
    private_data_dir: Path = Path("private_data")
    model_cache_dir: Path = Path("model_cache")
    log_level: str = "INFO"
    demo_mode: bool = True
    local_demo_mode: bool = False
    enable_real_models: bool = False
    demo_tokens: dict[str, str] = Field(default_factory=dict, repr=False)
    applicant_grants: dict[str, tuple[UUID, ...]] = Field(default_factory=dict, repr=False)
    risk_model_path: Path | None = None
    calibrator_path: Path | None = None
    shap_background_path: Path | None = None
    deberta_checkpoint: Path | None = None
    trocr_checkpoint: Path | None = None
    layoutlmv3_checkpoint: Path | None = None
    api_url: str = "http://127.0.0.1:8000"
    public_api_url: str = "http://127.0.0.1:8000"
    docs_dir: Path = Path("docs")
    mcp_enabled: bool = False
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8001, ge=1, le=65535)
    mcp_auth_token: str | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def safe_mode(self) -> "Settings":
        if self.local_demo_mode and self.env.strip().lower() in {"production", "deployment", "public"}:
            raise ValueError("local demo access cannot be enabled in a deployment environment")
        if self.demo_mode and self.enable_real_models:
            raise ValueError("real models cannot be enabled in demo mode")
        if any(role not in {"viewer", "reviewer", "admin"} for role in self.demo_tokens.values()):
            raise ValueError("unknown demo authorization role")
        if (self.risk_model_path is None) != (self.calibrator_path is None):
            raise ValueError("model and calibrator paths must be configured together")
        if any((self.deberta_checkpoint, self.trocr_checkpoint, self.layoutlmv3_checkpoint)) and not self.enable_real_models:
            raise ValueError("local extraction checkpoints require explicitly enabled research models")
        return self
