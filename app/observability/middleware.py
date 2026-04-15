from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.metrics import http_requests_total, observe_http_duration


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        stop_timer = observe_http_duration(request.method, request.url.path)
        response = await call_next(request)
        stop_timer()
        http_requests_total.labels(
            method=request.method,
            path=request.url.path,
            status_code=str(response.status_code),
        ).inc()
        return response
