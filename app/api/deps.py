from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.otp_service import OTPService
from app.services.rate_limit import DatabaseRateLimiter, RateLimiter, RedisRateLimiter
from app.services.sms.base import SMSProvider
from app.services.webhook_service import WebhookService


def get_sms_provider(request: Request) -> SMSProvider:
    return request.app.state.sms_provider


def get_sms_provider_registry(request: Request) -> dict[str, SMSProvider]:
    return request.app.state.sms_providers


def get_rate_limiter(request: Request, db: Session = Depends(get_db_session)) -> RateLimiter:
    redis_client = getattr(request.app.state, "redis_client", None)
    backend = getattr(request.app.state, "rate_limit_backend", "database")
    if redis_client is not None and backend == "redis":
        return RedisRateLimiter(redis_client, request.app.state.rate_limit_key_prefix)
    return DatabaseRateLimiter(db)


def get_otp_service(
    db: Session = Depends(get_db_session),
    sms_provider: SMSProvider = Depends(get_sms_provider),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> OTPService:
    return OTPService(db=db, sms_provider=sms_provider, rate_limiter=rate_limiter)


def get_webhook_service(
    db: Session = Depends(get_db_session),
    sms_provider_registry: dict[str, SMSProvider] = Depends(get_sms_provider_registry),
) -> WebhookService:
    return WebhookService(db=db, sms_provider_registry=sms_provider_registry)
