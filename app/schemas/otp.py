from datetime import datetime

from pydantic import BaseModel, Field


class OTPSendRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=32)
    purpose: str = Field(min_length=2, max_length=64)


class OTPVerifyRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=32)
    purpose: str = Field(min_length=2, max_length=64)
    code: str = Field(min_length=4, max_length=10)


class OTPResponse(BaseModel):
    success: bool
    message: str
    challenge_id: str | None = None
    expires_at: datetime | None = None
