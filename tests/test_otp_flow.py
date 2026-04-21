from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_sms_provider
from app.api.client_ip import client_ip_from_request
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.models.otp import AuditLog, OTPChallenge, OTPStatus
from app.services.cleanup_service import CleanupService
from app.services.rate_limit import DatabaseRateLimiter, RateLimiter
from app.services.sms.failover import FailoverSMSProvider, SMSFailoverError
from app.services.sms.base import SMSDeliveryResult, SMSDeliveryWebhookEvent, SMSProvider


class RecordingSMSProvider(SMSProvider):
    name = "recording"

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send_sms(self, to_number: str, message: str, status_callback_url: str | None = None) -> SMSDeliveryResult:
        self.messages.append((to_number, message))
        return SMSDeliveryResult(provider_name=self.name, provider_message_id=f"msg-{len(self.messages)}")

    def supports_webhooks(self) -> bool:
        return True

    def validate_webhook(self, url: str, params: dict[str, str], signature: str | None) -> bool:
        return signature == "test-signature"

    def parse_delivery_webhook(self, params: dict[str, str]) -> SMSDeliveryWebhookEvent:
        return SMSDeliveryWebhookEvent(
            provider_message_id=params["MessageSid"],
            status=params["MessageStatus"],
            error_code=params.get("ErrorCode"),
        )


class FailingSMSProvider(SMSProvider):
    name = "failing"

    def send_sms(self, to_number: str, message: str, status_callback_url: str | None = None) -> SMSDeliveryResult:
        raise RuntimeError("simulated send failure")


class InMemoryRateLimiter(RateLimiter):
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}

    def hit(self, scope: str, limit: int, window_seconds: int) -> bool:
        self.counters[scope] = self.counters.get(scope, 0) + 1
        return self.counters[scope] <= limit


@pytest.fixture()
def client(tmp_path) -> Generator[tuple[TestClient, RecordingSMSProvider], None, None]:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    provider = RecordingSMSProvider()
    rate_limiter = InMemoryRateLimiter()

    def override_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_sms_provider] = lambda: provider
    from app.api import deps

    app.dependency_overrides[deps.get_db_session] = override_db
    app.dependency_overrides[deps.get_rate_limiter] = lambda: rate_limiter
    app.dependency_overrides[deps.get_sms_provider_registry] = lambda: {"recording": provider}
    with TestClient(app) as test_client:
        yield test_client, provider
    app.dependency_overrides.clear()


def _extract_code(message: str) -> str:
    return message.split(" ", 1)[0]


def test_send_and_verify_otp(client: tuple[TestClient, RecordingSMSProvider]) -> None:
    test_client, provider = client
    send_response = test_client.post("/v1/otp/send", json={"phone_number": "+14155552671", "purpose": "login"})
    assert send_response.status_code == 202
    assert len(provider.messages) == 1

    code = _extract_code(provider.messages[0][1])
    verify_response = test_client.post(
        "/v1/otp/verify",
        json={"phone_number": "+14155552671", "purpose": "login", "code": code},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["success"] is True


def test_resend_cooldown_blocks_immediate_resend(client: tuple[TestClient, RecordingSMSProvider]) -> None:
    test_client, _provider = client
    first = test_client.post("/v1/otp/send", json={"phone_number": "+14155552671", "purpose": "login"})
    second = test_client.post("/v1/otp/send", json={"phone_number": "+14155552671", "purpose": "login"})
    assert first.status_code == 202
    assert second.status_code == 429


def test_invalid_code_is_rejected(client: tuple[TestClient, RecordingSMSProvider]) -> None:
    test_client, _provider = client
    test_client.post("/v1/otp/send", json={"phone_number": "+14155552671", "purpose": "login"})
    verify_response = test_client.post(
        "/v1/otp/verify",
        json={"phone_number": "+14155552671", "purpose": "login", "code": "000000"},
    )
    assert verify_response.status_code == 400
    assert verify_response.json()["detail"] == "Invalid verification code."


def test_api_key_is_required_when_configured(client: tuple[TestClient, RecordingSMSProvider]) -> None:
    test_client, _provider = client
    settings = get_settings()
    original = settings.api_key
    settings.api_key = "secret-api-key"
    try:
        denied = test_client.post("/v1/otp/send", json={"phone_number": "+14155552671", "purpose": "login"})
        accepted = test_client.post(
            "/v1/otp/send",
            json={"phone_number": "+14155552671", "purpose": "login"},
            headers={"X-OpenOTP-API-Key": "secret-api-key"},
        )
        assert denied.status_code == 401
        assert accepted.status_code == 202
    finally:
        settings.api_key = original


def test_invalid_phone_number_is_rejected(client: tuple[TestClient, RecordingSMSProvider]) -> None:
    test_client, _provider = client
    response = test_client.post("/v1/otp/send", json={"phone_number": "12345", "purpose": "login"})
    assert response.status_code == 422


def test_delivery_status_webhook_updates_challenge(client: tuple[TestClient, RecordingSMSProvider]) -> None:
    test_client, _provider = client
    send_response = test_client.post("/v1/otp/send", json={"phone_number": "+14155552671", "purpose": "login"})
    challenge_id = send_response.json()["challenge_id"]

    webhook_response = test_client.post(
        "/v1/webhooks/sms/recording/status",
        data={"MessageSid": "msg-1", "MessageStatus": "delivered"},
        headers={"X-Twilio-Signature": "test-signature"},
    )
    assert webhook_response.status_code == 200

    from app.api import deps

    db_generator = app.dependency_overrides[deps.get_db_session]()
    db = next(db_generator)
    try:
        challenge = db.get(OTPChallenge, challenge_id)
        assert challenge is not None
        assert challenge.delivery_status == "delivered"
        assert challenge.delivery_reference == "msg-1"
    finally:
        db.close()


def test_database_rate_limiter_uses_persisted_rate_limit_hits(tmp_path) -> None:
    db_path = tmp_path / "rate_limit.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        db.add(
            AuditLog(
                event_type="rate_limit_hit",
                outcome="accepted",
                phone_number="+14155552671",
                purpose="login",
                details='"send_otp:phone:+14155552671:purpose:login"',
            )
        )
        db.commit()

        limiter = DatabaseRateLimiter(db)
        assert limiter.hit("send_otp:phone:+14155552671:purpose:login", limit=2, window_seconds=3600) is True
        assert limiter.hit("send_otp:phone:+14155552671:purpose:login", limit=1, window_seconds=3600) is False


def test_cleanup_service_expires_and_purges_old_records(tmp_path) -> None:
    db_path = tmp_path / "cleanup.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    now = datetime.now(UTC).replace(tzinfo=None)

    with TestingSessionLocal() as db:
        db.add(
            OTPChallenge(
                phone_number="+14155552671",
                purpose="login",
                otp_hash="hash",
                otp_salt="salt",
                status=OTPStatus.pending,
                expires_at=now - timedelta(minutes=10),
                last_sent_at=now - timedelta(minutes=20),
                max_attempts=5,
            )
        )
        db.add(
            OTPChallenge(
                phone_number="+14155552671",
                purpose="signup",
                otp_hash="hash",
                otp_salt="salt",
                status=OTPStatus.verified,
                expires_at=now - timedelta(days=40),
                last_sent_at=now - timedelta(days=40),
                verified_at=now - timedelta(days=39),
                created_at=now - timedelta(days=40),
                updated_at=now - timedelta(days=40),
                max_attempts=5,
            )
        )
        db.add(
            AuditLog(
                event_type="send_otp",
                outcome="accepted",
                phone_number="+14155552671",
                purpose="login",
                created_at=now - timedelta(days=120),
            )
        )
        db.commit()

        service = CleanupService(db)
        service.settings.challenge_retention_days = 30
        service.settings.audit_log_retention_days = 90
        result = service.run()

        assert result.expired_marked == 1
        assert result.challenges_deleted == 1
        assert result.audit_logs_deleted == 1

        remaining = db.query(OTPChallenge).all()
        assert len(remaining) == 1
        assert remaining[0].status == OTPStatus.expired


def test_failover_sms_provider_uses_secondary_provider() -> None:
    provider = FailoverSMSProvider([FailingSMSProvider(), RecordingSMSProvider()])
    result = provider.send_sms("+14155552671", "hello", status_callback_url="https://example.com/v1/webhooks/sms/{provider}/status")
    assert result.provider_name == "recording"
    assert result.provider_message_id == "msg-1"


def test_failover_sms_provider_raises_when_all_fail() -> None:
    provider = FailoverSMSProvider([FailingSMSProvider()])
    with pytest.raises(SMSFailoverError):
        provider.send_sms("+14155552671", "hello")


def test_metrics_endpoint_exposes_prometheus_metrics(client: tuple[TestClient, RecordingSMSProvider]) -> None:
    test_client, _provider = client
    response = test_client.get("/metrics")
    assert response.status_code == 200
    assert "openotp_http_requests_total" in response.text
    assert "openotp_otp_send_total" in response.text


def test_metrics_endpoint_requires_token_when_configured(client: tuple[TestClient, RecordingSMSProvider]) -> None:
    test_client, _provider = client
    settings = get_settings()
    original = settings.metrics_bearer_token
    settings.metrics_bearer_token = "test-token"
    try:
        assert test_client.get("/metrics").status_code == 401
        assert test_client.get("/metrics", headers={"Authorization": "Bearer test-token"}).status_code == 200
    finally:
        settings.metrics_bearer_token = original


def test_forwarded_for_only_used_from_trusted_proxy(client: tuple[TestClient, RecordingSMSProvider]) -> None:
    test_client, _provider = client
    settings = get_settings()
    original = settings.trusted_proxy_ips
    try:
        request = SimpleNamespace(client=SimpleNamespace(host="10.0.0.1"))
        assert client_ip_from_request(request, "203.0.113.10") == "10.0.0.1"

        settings.trusted_proxy_ips = "10.0.0.1"
        assert client_ip_from_request(request, "203.0.113.10") == "203.0.113.10"
    finally:
        settings.trusted_proxy_ips = original
