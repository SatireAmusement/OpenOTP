from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SMSDeliveryResult:
    provider_name: str
    provider_message_id: str | None


@dataclass
class SMSDeliveryWebhookEvent:
    provider_message_id: str
    status: str
    error_code: str | None = None


class SMSProvider(ABC):
    name: str

    @abstractmethod
    def send_sms(self, to_number: str, message: str, status_callback_url: str | None = None) -> SMSDeliveryResult:
        raise NotImplementedError

    def supports_webhooks(self) -> bool:
        return False

    def validate_webhook(self, url: str, params: dict[str, str], signature: str | None) -> bool:
        return False

    def parse_delivery_webhook(self, params: dict[str, str]) -> SMSDeliveryWebhookEvent:
        raise NotImplementedError


def resolve_status_callback_url(status_callback_url: str | None, provider_name: str) -> str | None:
    if not status_callback_url:
        return None
    return status_callback_url.replace("{provider}", provider_name)
