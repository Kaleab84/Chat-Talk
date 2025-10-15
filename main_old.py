"""
CFC Animal Feed Software Chatbot API
Main FastAPI application with organized structure
"""

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path
from fastapi import FastAPI
from app.api.upload import router as upload_router

app = FastAPI()

app.include_router(upload_router, prefix="/files", tags=["Files"])


load_dotenv()

# Import the organized modules
from app.config import settings
from app.api.endpoints import health, ingest, chat, visibility

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="AI-powered help chatbot for animal-feed software with document search and Q&A capabilities"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(visibility.router)

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

