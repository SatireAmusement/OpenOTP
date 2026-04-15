from __future__ import annotations

from dataclasses import dataclass

from app.services.sms.base import SMSDeliveryResult, SMSProvider


@dataclass
class SMSFailoverError(Exception):
    attempts: list[str]

    def __str__(self) -> str:
        return "All SMS providers failed: " + "; ".join(self.attempts)


class FailoverSMSProvider(SMSProvider):
    name = "failover"

    def __init__(self, providers: list[SMSProvider]):
        if not providers:
            raise ValueError("FailoverSMSProvider requires at least one provider.")
        self.providers = providers

    def send_sms(self, to_number: str, message: str, status_callback_url: str | None = None) -> SMSDeliveryResult:
        attempts: list[str] = []
        for provider in self.providers:
            try:
                return provider.send_sms(to_number, message, status_callback_url=status_callback_url)
            except Exception as exc:
                attempts.append(f"{provider.name}: {exc}")
        raise SMSFailoverError(attempts)
