"""Central configuration; no model execution is implemented."""
from pathlib import Path
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
    enable_real_models: bool = False

    @model_validator(mode="after")
    def safe_mode(self) -> "Settings":
        if self.demo_mode and self.enable_real_models:
            raise ValueError("real models cannot be enabled in demo mode")
        return self
