from typing import Union
from uuid import UUID

from pydantic import BaseModel, EmailStr


class RequestMagicLinkRequest(BaseModel):
    email: EmailStr


class ExchangeTokenRequest(BaseModel):
    access_token: str


class UserOut(BaseModel):
    id: Union[str, UUID]
    email: EmailStr
    role: str
