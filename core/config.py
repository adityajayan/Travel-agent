import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = "test-key"
    database_url: str = "sqlite+aiosqlite:///./travel_agent.db"
    use_real_apis: bool = False
    approval_timeout_minutes: int = 30
    max_agent_iterations: int = 10
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
