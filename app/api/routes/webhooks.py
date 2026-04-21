from fastapi import APIRouter, Depends, Header, Request
from urllib.parse import parse_qsl

from app.api.client_ip import is_trusted_proxy
from app.core.config import get_settings
from app.api.deps import get_webhook_service
from app.schemas.webhook import WebhookResponse
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/v1/webhooks/sms", tags=["webhooks"])


def _external_url(request: Request, x_forwarded_proto: str | None, x_forwarded_host: str | None) -> str:
    settings = get_settings()
    peer_ip = request.client.host if request.client else None
    trust_forwarded = is_trusted_proxy(peer_ip)
    scheme = x_forwarded_proto if trust_forwarded and x_forwarded_proto else request.url.scheme
    host = x_forwarded_host if trust_forwarded and x_forwarded_host else request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}{request.url.path}"


@router.post("/{provider}/status", response_model=WebhookResponse)
async def sms_status_webhook(
    provider: str,
    request: Request,
    webhook_service: WebhookService = Depends(get_webhook_service),
    x_twilio_signature: str | None = Header(default=None),
    x_forwarded_proto: str | None = Header(default=None),
    x_forwarded_host: str | None = Header(default=None),
) -> WebhookResponse:
    raw_body = (await request.body()).decode("utf-8")
    params = dict(parse_qsl(raw_body, keep_blank_values=True))
    webhook_service.handle_delivery_status(
        provider_name=provider,
        webhook_url=_external_url(request, x_forwarded_proto, x_forwarded_host),
        params=params,
        signature=x_twilio_signature,
    )
    return WebhookResponse(success=True, message="Webhook processed.")
