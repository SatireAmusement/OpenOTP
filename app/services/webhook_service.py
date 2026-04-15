from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.otp import OTPChallenge
from app.observability.metrics import sms_webhook_total
from app.services.sms.base import SMSProvider


class WebhookService:
    def __init__(self, db: Session, sms_provider_registry: dict[str, SMSProvider]):
        self.db = db
        self.sms_provider_registry = sms_provider_registry

    def handle_delivery_status(
        self,
        provider_name: str,
        webhook_url: str,
        params: dict[str, str],
        signature: str | None,
    ) -> None:
        sms_provider = self.sms_provider_registry.get(provider_name)
        if sms_provider is None or not sms_provider.supports_webhooks():
            sms_webhook_total.labels(provider=provider_name, outcome="rejected", status="provider_missing").inc()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook provider is not configured.")
        if not sms_provider.validate_webhook(webhook_url, params, signature):
            sms_webhook_total.labels(provider=provider_name, outcome="rejected", status="invalid_signature").inc()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook signature validation failed.")

        event = sms_provider.parse_delivery_webhook(params)
        challenge = self.db.scalar(select(OTPChallenge).where(OTPChallenge.delivery_reference == event.provider_message_id))
        if challenge is None:
            sms_webhook_total.labels(provider=provider_name, outcome="rejected", status=event.status).inc()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No OTP challenge found for delivery event.")

        challenge.delivery_status = event.status
        challenge.delivery_error_code = event.error_code
        challenge.delivery_status_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.add(challenge)
        self.db.commit()
        sms_webhook_total.labels(provider=provider_name, outcome="accepted", status=event.status).inc()
