from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OTP_", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://openotp:openotp@localhost:5432/openotp"
    log_level: str = "INFO"
    public_base_url: str | None = None
    api_key: str | None = None
    redis_url: str | None = None
    rate_limit_backend: str = "database"
    rate_limit_key_prefix: str = "openotp:ratelimit"
    trusted_proxy_ips: str = ""
    metrics_enabled: bool = True
    metrics_bearer_token: str | None = None
    phone_default_region: str = "US"
    allowed_countries: str = ""
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

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def trusted_proxy_ip_set(self) -> set[str]:
        return {item.strip() for item in self.trusted_proxy_ips.split(",") if item.strip()}

    @property
    def allowed_country_set(self) -> set[str]:
        return {item.strip().upper() for item in self.allowed_countries.split(",") if item.strip()}

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if not self.is_production:
            return self

        errors: list[str] = []
        if self.otp_pepper == "replace-me-in-production":
            errors.append("OTP_OTP_PEPPER must be changed in production.")
        if self.sms_provider == "console":
            errors.append("OTP_SMS_PROVIDER=console is not allowed in production.")
        if not self.api_key:
            errors.append("OTP_API_KEY is required in production.")
        if not self.public_base_url or not self.public_base_url.startswith("https://"):
            errors.append("OTP_PUBLIC_BASE_URL must be an https:// URL in production.")
        if self.metrics_enabled and not self.metrics_bearer_token:
            errors.append("OTP_METRICS_BEARER_TOKEN is required when metrics are enabled in production.")

        if errors:
            raise ValueError(" ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
