from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.metrics import http_requests_total, observe_http_duration


def metric_path(path: str) -> str:
    known_prefixes = (
        "/v1/otp/send",
        "/v1/otp/verify",
        "/v1/webhooks/sms/",
        "/metrics",
        "/health",
        "/docs",
        "/openapi.json",
    )
    if path.startswith("/v1/webhooks/sms/"):
        return "/v1/webhooks/sms/{provider}/status"
    if path in known_prefixes:
        return path
    if path.startswith("/docs"):
        return "/docs"
    return "other"


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = metric_path(request.url.path)
        stop_timer = observe_http_duration(request.method, path)
        response = await call_next(request)
        stop_timer()
        http_requests_total.labels(
            method=request.method,
            path=path,
            status_code=str(response.status_code),
        ).inc()
        return response
