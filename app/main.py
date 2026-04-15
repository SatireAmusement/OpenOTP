from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.metrics import router as metrics_router
from app.api.routes.otp import router as otp_router
from app.api.routes.webhooks import router as webhooks_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.observability.middleware import MetricsMiddleware
from app.services.redis_client import build_redis_client
from app.services.sms.base import SMSProvider
from app.services.sms.console import ConsoleSMSProvider
from app.services.sms.failover import FailoverSMSProvider
from app.services.sms.twilio import TwilioSMSProvider


def build_sms_providers() -> dict[str, SMSProvider]:
    settings = get_settings()
    providers: dict[str, SMSProvider] = {"console": ConsoleSMSProvider()}
    try:
        providers["twilio"] = TwilioSMSProvider(settings)
    except ValueError:
        pass
    return providers


def build_sms_provider(provider_registry: dict[str, SMSProvider]) -> SMSProvider:
    settings = get_settings()
    provider_order = [settings.sms_provider, *[item.strip() for item in settings.sms_failover_providers.split(",") if item.strip()]]
    resolved = [provider_registry[name] for name in provider_order if name in provider_registry]
    if not resolved:
        raise ValueError("No configured SMS providers are available.")
    if len(resolved) == 1:
        return resolved[0]
    return FailoverSMSProvider(resolved)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()
    app.state.sms_providers = build_sms_providers()
    app.state.sms_provider = build_sms_provider(app.state.sms_providers)
    app.state.redis_client = build_redis_client()
    app.state.rate_limit_backend = settings.rate_limit_backend
    app.state.rate_limit_key_prefix = settings.rate_limit_key_prefix
    logger.info("application_started", extra={"sms_provider": app.state.sms_provider.name})
    yield
    logger.info("application_stopped")


app = FastAPI(
    title="OpenOTP",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.include_router(otp_router)
app.include_router(webhooks_router)
app.include_router(metrics_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
