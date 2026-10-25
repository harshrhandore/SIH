from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str
    jwt_secret: str
    mask_secret: str
    grant_secret: str
    demo_mode: bool = True
    demo_controls_enabled: bool = True
    local_benchmark_enabled: bool = True
    demo_as_of: str = "2026-10-25"
    web_origin: str = "http://localhost:3000"
    storage_root: str = str(ROOT / "storage")
    fixtures_root: str = str(ROOT / "fixtures")
    cookie_secure: bool = False
    llm_enabled: bool = False
    gemini_api_key: str = ""
    gemini_model: str = ""
    cache_ttl_seconds: int = 30
    cache_max_entries: int = 512

    def validate_secrets(self):
        for value in [self.jwt_secret, self.mask_secret, self.grant_secret]:
            if len(value) < 32:
                raise ValueError("Initialize local secrets with scripts/demo.py init-env")


settings = Settings()
settings.validate_secrets()
