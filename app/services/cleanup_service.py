from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.otp import AuditLog, OTPChallenge, OTPStatus
from app.observability.metrics import cleanup_records_total, cleanup_runs_total


@dataclass
class CleanupResult:
    expired_marked: int
    challenges_deleted: int
    audit_logs_deleted: int


class CleanupService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def run(self) -> CleanupResult:
        now = datetime.now(UTC).replace(tzinfo=None)
        challenge_cutoff = now - timedelta(days=self.settings.challenge_retention_days)
        audit_cutoff = now - timedelta(days=self.settings.audit_log_retention_days)

        expired_marked = self._mark_expired_pending_challenges(now)
        challenges_deleted = self._delete_old_challenges(challenge_cutoff)
        audit_logs_deleted = self._delete_old_audit_logs(audit_cutoff)
        self.db.commit()
        cleanup_runs_total.labels(outcome="success").inc()
        cleanup_records_total.labels(record_type="otp_challenge", action="expired").inc(expired_marked)
        cleanup_records_total.labels(record_type="otp_challenge", action="deleted").inc(challenges_deleted)
        cleanup_records_total.labels(record_type="audit_log", action="deleted").inc(audit_logs_deleted)

        return CleanupResult(
            expired_marked=expired_marked,
            challenges_deleted=challenges_deleted,
            audit_logs_deleted=audit_logs_deleted,
        )

    def _mark_expired_pending_challenges(self, now: datetime) -> int:
        result = self.db.execute(
            update(OTPChallenge)
            .where(OTPChallenge.status == OTPStatus.pending, OTPChallenge.expires_at < now)
            .values(status=OTPStatus.expired, updated_at=now)
        )
        return int(result.rowcount or 0)

    def _delete_old_challenges(self, cutoff: datetime) -> int:
        result = self.db.execute(
            delete(OTPChallenge).where(
                OTPChallenge.updated_at < cutoff,
                OTPChallenge.status.in_([OTPStatus.verified, OTPStatus.expired, OTPStatus.blocked]),
            )
        )
        return int(result.rowcount or 0)

    def _delete_old_audit_logs(self, cutoff: datetime) -> int:
        result = self.db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        return int(result.rowcount or 0)
