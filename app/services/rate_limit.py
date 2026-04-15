from __future__ import annotations

from abc import ABC, abstractmethod
import json
from datetime import UTC, datetime, timedelta

from redis import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.otp import AuditLog


class RateLimiter(ABC):
    @abstractmethod
    def hit(self, scope: str, limit: int, window_seconds: int) -> bool:
        raise NotImplementedError


class DatabaseRateLimiter(RateLimiter):
    def __init__(self, db: Session):
        self.db = db

    def hit(self, scope: str, limit: int, window_seconds: int) -> bool:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=window_seconds)
        stmt = select(func.count(AuditLog.id)).where(
            AuditLog.event_type == "rate_limit_hit",
            AuditLog.outcome == "accepted",
            AuditLog.details == json.dumps(scope),
            AuditLog.created_at >= cutoff,
        )
        count = self.db.scalar(stmt) or 0
        return count < limit


class RedisRateLimiter(RateLimiter):
    def __init__(self, client: Redis, key_prefix: str):
        self.client = client
        self.key_prefix = key_prefix

    def hit(self, scope: str, limit: int, window_seconds: int) -> bool:
        key = f"{self.key_prefix}:{scope}"
        current = self.client.incr(key)
        if current == 1:
            self.client.expire(key, window_seconds)
        return int(current) <= limit
