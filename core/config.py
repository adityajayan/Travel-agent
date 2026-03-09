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
            v = _strip_inline_comment(v)
            # If env var is empty, fall back to .env file value
            if not v:
                from dotenv import dotenv_values
                v = dotenv_values(".env").get("ANTHROPIC_API_KEY", "test-key")
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

    # M8 — Fallback providers
    duffel_api_token: str = ""
    getyourguide_api_key: str = ""

    # M8 — Redis cache
    redis_url: str = ""

    # M8 — Price re-verification threshold (percentage)
    price_change_threshold_pct: float = 5.0

    # M6 — Auth
    auth_provider_url: str = ""
    auth_secret: str = ""  # legacy — use jwt_secret instead

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/api/auth/callback/google"
    jwt_secret: str = ""  # used to sign/verify JWTs issued by this app
    jwt_expiry_hours: int = 72
    frontend_url: str = "http://localhost:3000"

    # Waitlist / invite-code gate
    invite_codes: str = ""  # comma-separated valid invite codes
    waitlist_enabled: bool = True

    # Stripe payments
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    service_fee_cents: int = 999  # $9.99 service fee

    # Email (Resend)
    resend_api_key: str = ""
    email_from: str = "Concierge <bookings@concierge.com>"

    # M6 — Push notifications
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_contact_email: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
