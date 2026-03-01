import os
from pydantic import field_validator
from pydantic_settings import BaseSettings


def _strip_inline_comment(value: str) -> str:
    """Strip trailing inline comments that python-dotenv keeps for unquoted values."""
    idx = value.find(" #")
    if idx != -1:
        value = value[:idx]
    return value.strip()


class Settings(BaseSettings):
    anthropic_api_key: str = "test-key"

    @field_validator("anthropic_api_key", mode="before")
    @classmethod
    def clean_api_key(cls, v: str) -> str:
        if isinstance(v, str):
            return _strip_inline_comment(v)
        return v

    database_url: str = "sqlite+aiosqlite:///./travel_agent.db"
    use_real_apis: bool = False
    approval_timeout_minutes: int = 30
    max_agent_iterations: int = 10
    log_level: str = "INFO"

    # M5 — Real API providers (required when USE_REAL_APIS=true)
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    amadeus_hostname: str = "test.api.amadeus.com"
    bookingcom_api_key: str = ""
    raileurope_api_key: str = ""
    hertz_client_id: str = ""
    hertz_client_secret: str = ""
    viator_api_key: str = ""

    # M6 — Auth
    auth_provider_url: str = ""
    auth_secret: str = ""

    # M6 — Push notifications
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_contact_email: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
