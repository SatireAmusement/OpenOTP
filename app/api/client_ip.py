from fastapi import Request

from app.core.config import get_settings


def client_ip_from_request(request: Request, x_forwarded_for: str | None) -> str | None:
    peer_ip = request.client.host if request.client else None
    trusted_proxies = get_settings().trusted_proxy_ip_set
    if peer_ip and peer_ip in trusted_proxies and x_forwarded_for:
        return x_forwarded_for.split(",", 1)[0].strip() or peer_ip
    return peer_ip
