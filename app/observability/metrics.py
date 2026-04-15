from __future__ import annotations

from time import perf_counter

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest


registry = CollectorRegistry()

http_requests_total = Counter(
    "openotp_http_requests_total",
    "Total HTTP requests handled by OpenOTP.",
    ["method", "path", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "openotp_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
    registry=registry,
)

otp_send_total = Counter(
    "openotp_otp_send_total",
    "Total OTP send attempts.",
    ["outcome", "provider", "purpose"],
    registry=registry,
)

otp_verify_total = Counter(
    "openotp_otp_verify_total",
    "Total OTP verification attempts.",
    ["outcome", "purpose"],
    registry=registry,
)

sms_webhook_total = Counter(
    "openotp_sms_webhook_total",
    "Total SMS webhook events processed.",
    ["provider", "outcome", "status"],
    registry=registry,
)

cleanup_runs_total = Counter(
    "openotp_cleanup_runs_total",
    "Total cleanup job runs.",
    ["outcome"],
    registry=registry,
)

cleanup_records_total = Counter(
    "openotp_cleanup_records_total",
    "Total records touched by cleanup jobs.",
    ["record_type", "action"],
    registry=registry,
)


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(registry), CONTENT_TYPE_LATEST


def observe_http_duration(method: str, path: str):
    start = perf_counter()

    def done() -> None:
        http_request_duration_seconds.labels(method=method, path=path).observe(perf_counter() - start)

    return done
