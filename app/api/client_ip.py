from ipaddress import ip_address, ip_network

from fastapi import Request

from app.core.config import get_settings


def is_trusted_proxy(peer_ip: str | None) -> bool:
    if not peer_ip:
        return False
    try:
        peer = ip_address(peer_ip)
    except ValueError:
        return False

    for item in get_settings().trusted_proxy_ip_set:
        try:
            if "/" in item and peer in ip_network(item, strict=False):
                return True
            if peer == ip_address(item):
                return True
        except ValueError:
            continue
    return False


def client_ip_from_request(request: Request, x_forwarded_for: str | None) -> str | None:
    peer_ip = request.client.host if request.client else None
    if is_trusted_proxy(peer_ip) and x_forwarded_for:
        return x_forwarded_for.split(",", 1)[0].strip() or peer_ip
    return peer_ip
