import secrets

from app.core.logging import get_logger
from app.services.sms.base import SMSDeliveryResult, SMSProvider, resolve_status_callback_url

logger = get_logger(__name__)


class ConsoleSMSProvider(SMSProvider):
    name = "console"

    def send_sms(self, to_number: str, message: str, status_callback_url: str | None = None) -> SMSDeliveryResult:
        reference = f"console-{secrets.token_hex(8)}"
        logger.info(
            "sms_delivery_console",
            extra={
                "to_number": to_number,
                "message": message,
                "reference": reference,
                "status_callback_url": resolve_status_callback_url(status_callback_url, self.name),
            },
        )
        return SMSDeliveryResult(provider_name=self.name, provider_message_id=reference)
