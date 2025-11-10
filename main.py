"""
CFC Animal Feed Software Chatbot API
Main FastAPI application with organized structure
"""

import os
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# Import the organized modules
from app.config import settings
from app.api.endpoints import health, ingest, chat, visibility

from app.api.endpoints.upload import router as upload_router

#app = FastAPI()

#app.include_router(upload_router, prefix="/files", tags=["Files"])
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ENV = os.getenv("ENV", "development").lower()

# Initialize FastAPI app (docs only in development)
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="AI-powered help chatbot for animal-feed software with document search and Q&A capabilities",
    docs_url="/docs" if ENV == "development" else None,
    redoc_url=None,
)

# Add CORS middleware (local-only origins)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# Security headers on all responses
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    csp = "default-src 'self'; connect-src 'self' http://localhost:8000 http://localhost:3000; img-src 'self' data:;"
    response.headers.setdefault("Content-Security-Policy", csp)
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response

# Request timing + interaction tracking
from app.services.supabase_service import SupabaseService
_tracker_db = SupabaseService()

@app.middleware("http")
async def interactions_tracker(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        try:
            user = getattr(request.state, "user", None)
            user_id = (user or {}).get("id")
            _tracker_db.record_interaction(
                user_id=user_id,
                route=request.url.path,
                status=str(status_code),
                duration_ms=duration_ms,
                tokens_used=None,
                meta={"method": request.method},
            )
        except Exception:
            pass
    return response

from app.auth.middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

# Include routers (auth/admin + protected routers)
from app.auth import router as auth_router
from app.admin import router as admin_router

app.include_router(auth_router.router)
app.include_router(admin_router.router)

app.include_router(health.router)  # public
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(visibility.router)
app.include_router(upload_router, prefix="/files", tags=["Files"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting CFC Animal Feed Software Chatbot API")
    
    # Create data directories if they don't exist
    settings.DATA_DIR.mkdir(exist_ok=True)
    settings.DOCUMENTS_DIR.mkdir(exist_ok=True)
    settings.VIDEOS_DIR.mkdir(exist_ok=True)
    settings.PROCESSED_DIR.mkdir(exist_ok=True)
    
    # Create subdirectories
    (settings.DOCUMENTS_DIR / "docx").mkdir(exist_ok=True)
    (settings.DOCUMENTS_DIR / "doc").mkdir(exist_ok=True)
    (settings.VIDEOS_DIR / "transcripts").mkdir(exist_ok=True)
    
    logger.info("Data directories initialized")
    logger.info(f"API running at http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"API documentation available at http://{settings.API_HOST}:{settings.API_PORT}/docs")

    # Initialize rate limiter if configured
    try:
        from app.rate_limit.limiter import init_rate_limiter
        await init_rate_limiter(app)
    except Exception as _exc:
        logger.warning(f"Rate limiter not initialized: {_exc}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down CFC Animal Feed Software Chatbot API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )
