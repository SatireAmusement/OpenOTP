from fastapi import APIRouter, Response

from app.observability.metrics import metrics_payload

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics() -> Response:
    payload, content_type = metrics_payload()
    return Response(content=payload, media_type=content_type)
