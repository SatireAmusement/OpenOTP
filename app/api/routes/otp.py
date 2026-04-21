from fastapi import APIRouter, Depends, Header, Request, status

from app.api.client_ip import client_ip_from_request
from app.api.deps import get_otp_service, require_api_key
from app.schemas.otp import OTPResponse, OTPSendRequest, OTPVerifyRequest
from app.services.otp_service import OTPService

router = APIRouter(prefix="/v1/otp", tags=["otp"])


@router.post("/send", response_model=OTPResponse, status_code=status.HTTP_202_ACCEPTED)
def send_otp(
    payload: OTPSendRequest,
    request: Request,
    _: None = Depends(require_api_key),
    otp_service: OTPService = Depends(get_otp_service),
    x_forwarded_for: str | None = Header(default=None),
    user_agent: str | None = Header(default=None),
) -> OTPResponse:
    client_ip = client_ip_from_request(request, x_forwarded_for)
    return otp_service.send_otp(payload=payload, ip_address=client_ip, user_agent=user_agent)


@router.post("/verify", response_model=OTPResponse)
def verify_otp(
    payload: OTPVerifyRequest,
    request: Request,
    _: None = Depends(require_api_key),
    otp_service: OTPService = Depends(get_otp_service),
    x_forwarded_for: str | None = Header(default=None),
    user_agent: str | None = Header(default=None),
) -> OTPResponse:
    client_ip = client_ip_from_request(request, x_forwarded_for)
    return otp_service.verify_otp(payload=payload, ip_address=client_ip, user_agent=user_agent)
