"""
CFC Animal Feed Software Chatbot API
Main FastAPI application with organized structure
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from dotenv import load_dotenv
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Load env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "app" / ".env")

# Import settings + API endpoints
from app.config import settings
from app.api.endpoints import health, ingest, chat, visibility, transcripts
from app.api.endpoints.upload import router as upload_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="AI-powered help chatbot for animal-feed software with document search and Q&A capabilities"
)

# -------------------------
# FRONTEND UI SUPPORT
# -------------------------

# Serve static folder (chat.html must be inside /static folder)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_chat_ui():
    """
    Serves the chatbot UI webpage.
    """
    with open("static/chat.html", "r", encoding="utf-8") as f:
        return f.read()

# -------------------------
# CORS (allows browser UI calls)
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # For now allow all. Restrict for production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# API ROUTERS
# -------------------------
app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(chat.router, prefix="/api")   # ✅ Chat endpoint is /api/chat
app.include_router(visibility.router)
app.include_router(transcripts.router)
app.include_router(upload_router, prefix="/files", tags=["Files"])

# -------------------------
# EVENTS
# -------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("Starting CFC Chatbot API...")
    settings.DATA_DIR.mkdir(exist_ok=True)
    settings.DOCUMENTS_DIR.mkdir(exist_ok=True)
    settings.VIDEOS_DIR.mkdir(exist_ok=True)
    settings.PROCESSED_DIR.mkdir(exist_ok=True)
    (settings.DOCUMENTS_DIR / "docx").mkdir(exist_ok=True)
    (settings.DOCUMENTS_DIR / "doc").mkdir(exist_ok=True)
    (settings.VIDEOS_DIR / "transcripts").mkdir(exist_ok=True)
    logger.info("Startup complete. UI available at http://127.0.0.1:8000")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down CFC Chatbot API...")

# -------------------------
# RUN SERVER
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )
