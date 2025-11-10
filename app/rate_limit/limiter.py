"""
Optional rate limiter for local development keyed by user id or IP.

If RATE_LIMIT_REDIS_URL is set and fastapi-limiter is installed, use it.
Otherwise, fall back to an in-memory sliding window limiter.
"""
import asyncio
import os
import time
from typing import Any, Callable, Dict, Tuple

from fastapi import HTTPException, Request, status


REDIS_URL = os.getenv("RATE_LIMIT_REDIS_URL")

try:
    if REDIS_URL:
        from fastapi_limiter import FastAPILimiter
        from fastapi_limiter.depends import RateLimiter
        import redis.asyncio as aioredis  # type: ignore
        _available = True
    else:
        FastAPILimiter = None  # type: ignore
        RateLimiter = None  # type: ignore
        aioredis = None  # type: ignore
        _available = False
except Exception:
    FastAPILimiter = None  # type: ignore
    RateLimiter = None  # type: ignore
    aioredis = None  # type: ignore
    _available = False


async def init_rate_limiter(app: Any) -> None:
    if not _available:
        return
    assert aioredis is not None
    assert FastAPILimiter is not None
    redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)


def _identifier(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user and user.get("id"):
        return f"user:{user['id']}"
    ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


def limit(spec: str) -> Callable:
    """Return a dependency suitable for FastAPI to enforce a rate limit.

    Example usage: Depends(limit("20/minute"))
    Keyed by user id when authenticated, else IP.
    """
    count, window = _parse_spec(spec)

    if _available and RateLimiter is not None:
        # Try to use fastapi-limiter; fall back to memory otherwise.
        try:
            return RateLimiter(times=count, seconds=window)
        except Exception:
            pass

    # In-memory fallback
    store: Dict[str, Tuple[int, float]] = {}  # key -> (used, window_start)
    lock = asyncio.Lock()

    async def _dep(request: Request):
        key_root = _identifier(request)
        route = request.url.path
        key = f"{key_root}|{route}|{count}/{window}"
        now = time.monotonic()
        async with lock:
            used, start = store.get(key, (0, now))
            if now - start >= window:
                used, start = 0, now
            if used >= count:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
            store[key] = (used + 1, start)
        return True

    return _dep


def _parse_spec(spec: str) -> Tuple[int, int]:
    # "20/minute" -> (20, 60)
    try:
        times_s, per = spec.split("/")
        times = int(times_s.strip())
        per = per.strip().lower()
        if per in ("s", "sec", "second", "seconds"):
            return times, 1
        if per in ("m", "min", "minute", "minutes"):
            return times, 60
        if per in ("h", "hour", "hours"):
            return times, 3600
        if per in ("d", "day", "days"):
            return times, 86400
    except Exception:
        pass
    return 1, 60
