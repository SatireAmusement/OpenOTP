import secrets

import httpx
from twilio.request_validator import RequestValidator

from app.core.config import Settings
from app.services.sms.base import SMSDeliveryResult, SMSDeliveryWebhookEvent, SMSProvider, resolve_status_callback_url


class TwilioSMSProvider(SMSProvider):
    name = "twilio"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.validator = RequestValidator(settings.twilio_auth_token or "")
        if not all([settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from_number]):
            raise ValueError("Twilio configuration is incomplete.")

    def send_sms(self, to_number: str, message: str, status_callback_url: str | None = None) -> SMSDeliveryResult:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.settings.twilio_account_sid}/Messages.json"
        payload = {"To": to_number, "From": self.settings.twilio_from_number, "Body": message}
        resolved_callback_url = resolve_status_callback_url(status_callback_url, self.name)
        if resolved_callback_url:
            payload["StatusCallback"] = resolved_callback_url
        response = httpx.post(
            url,
            auth=(self.settings.twilio_account_sid, self.settings.twilio_auth_token),
            data=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        response_payload = response.json()
        return SMSDeliveryResult(
            provider_name=self.name,
            provider_message_id=response_payload.get("sid") or f"twilio-{secrets.token_hex(8)}",
        )

    def supports_webhooks(self) -> bool:
        return True

    def validate_webhook(self, url: str, params: dict[str, str], signature: str | None) -> bool:
        if not signature:
            return False
        return self.validator.validate(url, params, signature)

    def parse_delivery_webhook(self, params: dict[str, str]) -> SMSDeliveryWebhookEvent:
        message_sid = params.get("MessageSid")
        message_status = params.get("MessageStatus")
        if not message_sid or not message_status:
            raise ValueError("Twilio delivery webhook is missing MessageSid or MessageStatus.")
        return SMSDeliveryWebhookEvent(
            provider_message_id=message_sid,
            status=message_status,
            error_code=params.get("ErrorCode"),
        )
