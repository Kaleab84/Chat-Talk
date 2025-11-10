import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from app.config import settings


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def _now() -> int:
    return int(time.time())


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)


COOKIE_NAME = _env("SESSION_COOKIE_NAME", "CFC_SESSION")
TTL_DAYS = int(_env("SESSION_TTL_DAYS", "7"))
SESSION_TTL_SECONDS = TTL_DAYS * 24 * 60 * 60
SESSION_SECRET = (_env("SESSION_SECRET") or "dev-secret-change-me").encode("utf-8")


@dataclass
class SessionCookie:
    session_id: str
    exp: int

    @classmethod
    def create(cls, session_id: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
        exp = _now() + ttl_seconds
        payload = f"{session_id}.{exp}".encode("utf-8")
        sig = _b64url(_hmac_sha256(SESSION_SECRET, payload))
        token = f"{session_id}.{exp}.{sig}"
        return token

    @classmethod
    def parse_and_verify(cls, token: str) -> Optional["SessionCookie"]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            session_id, exp_s, sig = parts
            payload = f"{session_id}.{exp_s}".encode("utf-8")
            expected_sig = _b64url(_hmac_sha256(SESSION_SECRET, payload))
            if not hmac.compare_digest(expected_sig, sig):
                return None
            exp = int(exp_s)
            if _now() > exp:
                return None
            return cls(session_id=session_id, exp=exp)
        except Exception:
            return None


def build_cookie_header(value: str, *, domain: Optional[str] = None, path: str = "/") -> Tuple[str, str]:
    parts = [f"{COOKIE_NAME}={value}", f"Path={path}", "HttpOnly", "Secure", "SameSite=None"]
    # In local dev, domain may be omitted to default to host-only cookies
    if domain:
        parts.append(f"Domain={domain}")
    # Max-Age preferred to Expires; browser will handle deletion on logout
    parts.append(f"Max-Age={SESSION_TTL_SECONDS}")
    return ("set-cookie", "; ".join(parts))


def build_clear_cookie_header(*, domain: Optional[str] = None, path: str = "/") -> Tuple[str, str]:
    parts = [f"{COOKIE_NAME}=", f"Path={path}", "HttpOnly", "Secure", "SameSite=None", "Max-Age=0"]
    if domain:
        parts.append(f"Domain={domain}")
    return ("set-cookie", "; ".join(parts))

