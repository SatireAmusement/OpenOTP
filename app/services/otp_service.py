import hashlib
import hmac
import json
import math
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.otp import AuditLog, OTPChallenge, OTPStatus
from app.observability.metrics import otp_send_total, otp_verify_total
from app.schemas.otp import OTPResponse, OTPSendRequest, OTPVerifyRequest
from app.services.rate_limit import RateLimiter
from app.services.sms.base import SMSProvider
from app.utils.phone import InvalidPhoneNumberError, normalize_phone_number

logger = get_logger(__name__)
INVALID_OTP_DETAIL = "Invalid verification code."


class OTPService:
    def __init__(self, db: Session, sms_provider: SMSProvider, rate_limiter: RateLimiter):
        self.db = db
        self.sms_provider = sms_provider
        self.rate_limiter = rate_limiter
        self.settings = get_settings()

    def send_otp(self, payload: OTPSendRequest, ip_address: str | None, user_agent: str | None) -> OTPResponse:
        phone_number = self._normalize_phone_number(payload.phone_number)
        now = self._now()
        status_callback_url = self._status_callback_url()

        self._enforce_event_window(
            event_type="send_otp",
            phone_number=phone_number,
            purpose=payload.purpose,
            limit=self.settings.send_max_per_window,
            window_seconds=self.settings.send_window_seconds,
            ip_address=ip_address,
            error_detail="Send rate limit exceeded.",
        )

        challenge = self._get_active_challenge(phone_number=phone_number, purpose=payload.purpose, now=now)
        is_resend = challenge is not None
        if challenge:
            cooldown_available_at = challenge.last_sent_at + timedelta(seconds=self.settings.resend_cooldown_seconds)
            if now < cooldown_available_at:
                self._log_event(
                    event_type="send_otp",
                    outcome="blocked",
                    phone_number=phone_number,
                    purpose=payload.purpose,
                    challenge_id=challenge.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "cooldown_active"},
                )
                otp_send_total.labels(outcome="blocked", provider="n/a", purpose=self._metric_purpose(payload.purpose)).inc()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Resend cooldown is still active.",
                )

            if challenge.resend_count >= self.settings.resend_max_per_challenge:
                challenge.status = OTPStatus.blocked
                self.db.add(challenge)
                self.db.commit()
                self._log_event(
                    event_type="send_otp",
                    outcome="blocked",
                    phone_number=phone_number,
                    purpose=payload.purpose,
                    challenge_id=challenge.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "resend_limit_reached"},
                )
                otp_send_total.labels(
                    outcome="blocked",
                    provider=challenge.delivery_provider or "n/a",
                    purpose=self._metric_purpose(payload.purpose),
                ).inc()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Resend limit reached for the current OTP challenge.",
                )
        else:
            challenge = OTPChallenge(
                phone_number=phone_number,
                purpose=payload.purpose,
                status=OTPStatus.pending,
                max_attempts=self.settings.otp_max_verify_attempts,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=now + timedelta(seconds=self.settings.otp_ttl_seconds),
                last_sent_at=now,
            )

        code = self._generate_otp()
        otp_salt = secrets.token_hex(16)
        challenge.otp_salt = otp_salt
        challenge.otp_hash = self._hash_otp(code=code, salt=otp_salt)
        challenge.expires_at = now + timedelta(seconds=self.settings.otp_ttl_seconds)
        challenge.last_sent_at = now
        challenge.resend_count = challenge.resend_count + 1 if is_resend else 0

        expiry_minutes = max(1, math.ceil(self.settings.otp_ttl_seconds / 60))
        message = f"{code} is your verification code for {payload.purpose}. It expires in {expiry_minutes} minutes."
        delivery = self.sms_provider.send_sms(phone_number, message, status_callback_url=status_callback_url)
        challenge.delivery_provider = delivery.provider_name
        challenge.delivery_reference = delivery.provider_message_id
        challenge.delivery_status = "queued"
        challenge.delivery_status_at = now

        self.db.add(challenge)
        self.db.commit()
        self.db.refresh(challenge)

        self._log_event(
            event_type="send_otp",
            outcome="accepted",
            phone_number=phone_number,
            purpose=payload.purpose,
            challenge_id=challenge.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"provider": delivery.provider_name},
        )
        otp_send_total.labels(outcome="accepted", provider=delivery.provider_name, purpose=self._metric_purpose(payload.purpose)).inc()
        logger.info("otp_sent", extra={"challenge_id": challenge.id, "phone_number": phone_number, "purpose": payload.purpose})
        return OTPResponse(
            success=True,
            message="OTP sent successfully.",
            challenge_id=challenge.id,
            expires_at=challenge.expires_at,
        )

    def verify_otp(self, payload: OTPVerifyRequest, ip_address: str | None, user_agent: str | None) -> OTPResponse:
        phone_number = self._normalize_phone_number(payload.phone_number)
        now = self._now()

        self._enforce_event_window(
            event_type="verify_otp",
            phone_number=phone_number,
            purpose=payload.purpose,
            limit=self.settings.verify_max_per_window,
            window_seconds=self.settings.verify_window_seconds,
            ip_address=ip_address,
            error_detail="Verification rate limit exceeded.",
        )

        challenge = self._get_latest_challenge(phone_number=phone_number, purpose=payload.purpose)
        if not challenge:
            self._log_event(
                event_type="verify_otp",
                outcome="rejected",
                phone_number=phone_number,
                purpose=payload.purpose,
                challenge_id=None,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "challenge_missing"},
            )
            otp_verify_total.labels(outcome="rejected", purpose=self._metric_purpose(payload.purpose)).inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_OTP_DETAIL)

        if challenge.status == OTPStatus.verified:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_OTP_DETAIL)
        if challenge.status == OTPStatus.blocked:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_OTP_DETAIL)
        if challenge.expires_at <= now:
            challenge.status = OTPStatus.expired
            self.db.add(challenge)
            self.db.commit()
            self._log_event(
                event_type="verify_otp",
                outcome="rejected",
                phone_number=phone_number,
                purpose=payload.purpose,
                challenge_id=challenge.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "expired"},
            )
            otp_verify_total.labels(outcome="rejected", purpose=self._metric_purpose(payload.purpose)).inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_OTP_DETAIL)

        if challenge.attempt_count >= challenge.max_attempts:
            challenge.status = OTPStatus.blocked
            self.db.add(challenge)
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_OTP_DETAIL)

        candidate_hash = self._hash_otp(code=payload.code, salt=challenge.otp_salt)
        if not hmac.compare_digest(candidate_hash, challenge.otp_hash):
            challenge.attempt_count += 1
            if challenge.attempt_count >= challenge.max_attempts:
                challenge.status = OTPStatus.blocked
            self.db.add(challenge)
            self.db.commit()
            self._log_event(
                event_type="verify_otp",
                outcome="rejected",
                phone_number=phone_number,
                purpose=payload.purpose,
                challenge_id=challenge.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "code_mismatch", "attempt_count": challenge.attempt_count},
            )
            otp_verify_total.labels(outcome="rejected", purpose=self._metric_purpose(payload.purpose)).inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_OTP_DETAIL)

        challenge.status = OTPStatus.verified
        challenge.verified_at = now
        challenge.attempt_count += 1
        self.db.add(challenge)
        self.db.commit()
        self._log_event(
            event_type="verify_otp",
            outcome="accepted",
            phone_number=phone_number,
            purpose=payload.purpose,
            challenge_id=challenge.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"provider": challenge.delivery_provider},
        )
        otp_verify_total.labels(outcome="accepted", purpose=self._metric_purpose(payload.purpose)).inc()
        logger.info("otp_verified", extra={"challenge_id": challenge.id, "phone_number": phone_number, "purpose": payload.purpose})
        return OTPResponse(success=True, message="OTP verified successfully.", challenge_id=challenge.id)

    def _get_active_challenge(self, phone_number: str, purpose: str, now: datetime) -> OTPChallenge | None:
        stmt = (
            select(OTPChallenge)
            .where(
                OTPChallenge.phone_number == phone_number,
                OTPChallenge.purpose == purpose,
                OTPChallenge.status == OTPStatus.pending,
                OTPChallenge.expires_at > now,
            )
            .order_by(OTPChallenge.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def _get_latest_challenge(self, phone_number: str, purpose: str) -> OTPChallenge | None:
        stmt = (
            select(OTPChallenge)
            .where(OTPChallenge.phone_number == phone_number, OTPChallenge.purpose == purpose)
            .order_by(OTPChallenge.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def _enforce_event_window(
        self,
        event_type: str,
        phone_number: str,
        purpose: str,
        limit: int,
        window_seconds: int,
        ip_address: str | None,
        error_detail: str,
    ) -> None:
        scopes = [f"{event_type}:phone:{phone_number}:purpose:{purpose}"]
        ip_allowed = True
        if ip_address:
            scopes.append(f"{event_type}:ip:{ip_address}:purpose:{purpose}")

        allowed = [self.rate_limiter.hit(scope, limit, window_seconds) for scope in scopes]
        phone_allowed = allowed[0]
        if len(allowed) > 1:
            ip_allowed = allowed[1]

        if not phone_allowed or not ip_allowed:
            self._log_event(
                event_type=event_type,
                outcome="blocked",
                phone_number=phone_number,
                purpose=purpose,
                challenge_id=None,
                ip_address=ip_address,
                user_agent=None,
                details={"reason": "window_rate_limit"},
            )
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_detail)

        for scope in scopes:
            self._log_event(
                event_type="rate_limit_hit",
                outcome="accepted",
                phone_number=phone_number,
                purpose=purpose,
                challenge_id=None,
                ip_address=ip_address,
                user_agent=None,
                details=scope,
            )

    def _generate_otp(self) -> str:
        digits = "0123456789"
        return "".join(secrets.choice(digits) for _ in range(self.settings.otp_length))

    def _normalize_phone_number(self, phone_number: str) -> str:
        try:
            return normalize_phone_number(phone_number, default_region=self.settings.phone_default_region)
        except InvalidPhoneNumberError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    def _hash_otp(self, code: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256",
            f"{code}{self.settings.otp_pepper}".encode("utf-8"),
            salt.encode("utf-8"),
            self.settings.otp_hash_iterations,
        ).hex()

    def _status_callback_url(self) -> str | None:
        if not self.settings.public_base_url or not self.sms_provider.supports_webhooks():
            return None
        base_url = self.settings.public_base_url.rstrip("/")
        return f"{base_url}/v1/webhooks/sms/{{provider}}/status"

    @staticmethod
    def _metric_purpose(purpose: str) -> str:
        known = {"login", "signup", "password_reset", "transaction"}
        return purpose if purpose in known else "other"

    def _log_event(
        self,
        event_type: str,
        outcome: str,
        phone_number: str,
        purpose: str,
        challenge_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
        details: dict | None,
    ) -> None:
        self.db.add(
            AuditLog(
                event_type=event_type,
                outcome=outcome,
                phone_number=phone_number,
                purpose=purpose,
                challenge_id=challenge_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=json.dumps(details or {}),
            )
        )
        self.db.commit()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)
