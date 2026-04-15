from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OTP_", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://openotp:openotp@localhost:5432/openotp"
    log_level: str = "INFO"
    public_base_url: str | None = None
    redis_url: str | None = None
    rate_limit_backend: str = "database"
    rate_limit_key_prefix: str = "openotp:ratelimit"
    phone_default_region: str = "US"
    challenge_retention_days: int = Field(default=30, ge=1, le=3650)
    audit_log_retention_days: int = Field(default=90, ge=1, le=3650)

    otp_length: int = Field(default=6, ge=4, le=10)
    otp_ttl_seconds: int = Field(default=300, ge=60, le=1800)
    otp_max_verify_attempts: int = Field(default=5, ge=1, le=20)
    otp_hash_iterations: int = Field(default=120_000, ge=10_000, le=500_000)
    otp_pepper: str = "replace-me-in-production"

    send_max_per_window: int = Field(default=5, ge=1, le=100)
    send_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    verify_max_per_window: int = Field(default=10, ge=1, le=200)
    verify_window_seconds: int = Field(default=900, ge=60, le=86_400)
    resend_cooldown_seconds: int = Field(default=60, ge=0, le=3600)
    resend_max_per_challenge: int = Field(default=3, ge=0, le=20)

    sms_provider: str = "console"
    sms_failover_providers: str = ""
    sms_sender_id: str = "ExampleApp"
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
