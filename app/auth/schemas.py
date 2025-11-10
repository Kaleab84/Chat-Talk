from typing import Optional
from pydantic import BaseModel, EmailStr


class RequestLinkPayload(BaseModel):
    email: EmailStr
    redirect_to: Optional[str] = None


class ExchangePayload(BaseModel):
    access_token: str


class AuthUser(BaseModel):
    id: str
    email: EmailStr
    role: str = "user"


class AuthMeResponse(BaseModel):
    authenticated: bool
    user: Optional[AuthUser] = None


class MessageResponse(BaseModel):
    ok: bool = True
    message: str = ""

