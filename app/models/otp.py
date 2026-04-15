import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OTPStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    expired = "expired"
    blocked = "blocked"


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class OTPChallenge(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number: Mapped[str] = mapped_column(String(32), index=True)
    purpose: Mapped[str] = mapped_column(String(64), index=True)
    otp_hash: Mapped[str] = mapped_column(String(128))
    otp_salt: Mapped[str] = mapped_column(String(64))
    status: Mapped[OTPStatus] = mapped_column(Enum(OTPStatus), default=OTPStatus.pending, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    resend_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    delivery_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delivery_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    delivery_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    delivery_error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delivery_status_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(), index=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=utcnow_naive,
        onupdate=utcnow_naive,
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    outcome: Mapped[str] = mapped_column(String(32), index=True)
    phone_number: Mapped[str] = mapped_column(String(32), index=True)
    purpose: Mapped[str] = mapped_column(String(64), index=True)
    challenge_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=utcnow_naive, index=True)
