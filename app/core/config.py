"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central config loaded from environment / .env file."""

    database_url: str = "postgresql://mfg_user:mfg_pass@localhost:5432/mfg_db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-key-change-in-prod"
    log_level: str = "INFO"

    # Automation thresholds
    defect_rate_threshold: float = 0.15        # 15 % defect rate triggers QA hold
    downtime_alert_minutes: int = 10            # station down > 10 min triggers pause
    cycle_time_threshold_minutes: float = 30.0  # avg cycle time bottleneck threshold

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
