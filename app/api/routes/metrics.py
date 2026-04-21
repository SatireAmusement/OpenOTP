from fastapi import APIRouter, Header, HTTPException, Response, status

from app.core.config import get_settings
from app.observability.metrics import metrics_payload

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics(authorization: str | None = Header(default=None)) -> Response:
    settings = get_settings()
    if not settings.metrics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if settings.metrics_bearer_token:
        expected = f"Bearer {settings.metrics_bearer_token}"
        if authorization != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")
    payload, content_type = metrics_payload()
    return Response(content=payload, media_type=content_type)
