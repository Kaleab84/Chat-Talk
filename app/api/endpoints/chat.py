from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
import logging
from app.api.models.requests import SearchRequest, AskRequest, RecommendationRequest
from app.api.models.responses import SearchResponse, AskResponse, RecommendationResponse, SearchResult, ImageReference
from app.services.chat_service import ChatService
from app.config import settings
from app.services.content_repository import ContentRepository
from app.services.supabase_content_repository import SupabaseContentRepository

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

# Initialize chat service
chat_service = ChatService()

# Initialize content repository (same logic as ingest.py)
if settings.SUPABASE_URL and settings.SUPABASE_BUCKET:
    _content_repository = SupabaseContentRepository()
    logger.info("Using SupabaseContentRepository for image serving.")
else:
    _content_repository = ContentRepository()
    logger.info("Using local ContentRepository for image serving.")

@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search for relevant document chunks."""
    try:
        result = chat_service.search_documents(request.query, request.top_k)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Convert to response format
        search_results = [
            SearchResult(
                rank=item["rank"],
                score=item["score"],
                text=item["text"],
                source=item["source"],
                source_type=item.get("source_type", "document"),
                chunk_id=item["chunk_id"],
                doc_id=item.get("doc_id"),
                section_id=item.get("section_id"),
                section_path=item.get("section_path"),
                section_title=item.get("section_title"),
                image_paths=item.get("image_paths"),
                start_seconds=item.get("start_seconds"),
                end_seconds=item.get("end_seconds"),
                video_url=item.get("video_url"),
                txt_url=item.get("txt_url"),
                srt_url=item.get("srt_url"),
                vtt_url=item.get("vtt_url"),
            )
            for item in result["results"]
        ]
        
        return SearchResponse(
            success=True,
            query=request.query,
            results=search_results,
            total_results=len(search_results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a question and get an AI-powered answer."""
    try:
        result = chat_service.ask_question(request.question, request.top_k)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Convert context to response format
        context_results = [
            SearchResult(
                rank=item["rank"],
                score=item["score"],
                text=item["text"],
                source=item["source"],
                source_type=item.get("source_type", "document"),
                chunk_id=item["chunk_id"],
                doc_id=item.get("doc_id"),
                section_id=item.get("section_id"),
                section_path=item.get("section_path"),
                section_title=item.get("section_title"),
                image_paths=item.get("image_paths"),
                start_seconds=item.get("start_seconds"),
                end_seconds=item.get("end_seconds"),
                video_url=item.get("video_url"),
                txt_url=item.get("txt_url"),
                srt_url=item.get("srt_url"),
                vtt_url=item.get("vtt_url"),
            )
            for item in result["context_used"]
        ]
        
        # Convert relevant_images to ImageReference objects
        relevant_images = None
        if result.get("relevant_images"):
            relevant_images = [
                ImageReference(
                    path=img.get("path"),
                    position=img.get("position"),
                    alt_text=img.get("alt_text"),
                    relevance_score=img.get("relevance_score"),
                    context_text=img.get("context_text"),
                )
                for img in result["relevant_images"]
            ]
        
        return AskResponse(
            success=True,
            question=request.question,
            answer=result["answer"],
            context_used=context_results,
            confidence=result.get("confidence"),
            video_context=result.get("video_context"),
            relevant_images=relevant_images,
            answer_video_url=result.get("answer_video_url"),
            answer_start_seconds=result.get("answer_start_seconds"),
            answer_end_seconds=result.get("answer_end_seconds"),
            answer_timestamp=result.get("answer_timestamp"),
            answer_end_timestamp=result.get("answer_end_timestamp"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask/video", response_model=AskResponse)
async def ask_video_question(request: AskRequest):
    """Ask a question that should only use video transcripts for context."""
    try:
        result = chat_service.ask_video_question(request.question, request.top_k)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error") or "Unable to answer video question")
        
        context_results = [
            SearchResult(
                rank=item["rank"],
                score=item["score"],
                text=item["text"],
                source=item["source"],
                source_type=item.get("source_type", "video"),
                chunk_id=item["chunk_id"],
                doc_id=item.get("doc_id"),
                section_id=item.get("section_id"),
                section_path=item.get("section_path"),
                section_title=item.get("section_title"),
                image_paths=item.get("image_paths"),
                start_seconds=item.get("start_seconds"),
                end_seconds=item.get("end_seconds"),
                video_url=item.get("video_url"),
                txt_url=item.get("txt_url"),
                srt_url=item.get("srt_url"),
                vtt_url=item.get("vtt_url"),
            )
            for item in result["context_used"]
        ]
        
        return AskResponse(
            success=True,
            question=request.question,
            answer=result["answer"],
            context_used=context_results,
            confidence=result.get("confidence"),
            video_context=result.get("video_context"),
            answer_video_url=result.get("answer_video_url"),
            answer_start_seconds=result.get("answer_start_seconds"),
            answer_end_seconds=result.get("answer_end_seconds"),
            answer_timestamp=result.get("answer_timestamp"),
            answer_end_timestamp=result.get("answer_end_timestamp"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Get content recommendations based on a query."""
    try:
        result = chat_service.get_recommendations(request.query, request.content_type)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return RecommendationResponse(
            success=True,
            query=request.query,
            recommendations=result["recommendations"],
            total_items=result["total_items"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/content/images/{path:path}")
async def serve_image(path: str):
    """Serve images from document storage.
    
    Path format: docs/{doc_id}/images/{filename}
    For Supabase: Returns redirect to public URL
    For local: Returns file from filesystem
    """
    try:
        # Validate path format
        if not path.startswith("docs/"):
            raise HTTPException(status_code=400, detail="Invalid image path format")
        
        # Handle Supabase storage
        if isinstance(_content_repository, SupabaseContentRepository):
            try:
                public_url = _content_repository.public_url(path)
                return RedirectResponse(url=public_url)
            except Exception as e:
                logger.error(f"Error getting Supabase URL for {path}: {e}")
                raise HTTPException(status_code=404, detail="Image not found in Supabase storage")
        
        # Handle local storage
        # Convert storage path (docs/{doc_id}/images/{filename}) to filesystem path
        # Storage path: docs/{doc_id}/images/{filename}
        # Filesystem path: {LOCAL_CONTENT_ROOT}/{doc_id}/images/{filename}
        path_parts = path.split("/")
        if len(path_parts) < 4 or path_parts[0] != "docs" or path_parts[2] != "images":
            raise HTTPException(status_code=400, detail="Invalid image path format")
        
        doc_id = path_parts[1]
        filename = "/".join(path_parts[3:])  # Handle filenames with subdirectories (unlikely but safe)
        
        # Build filesystem path
        image_path = settings.LOCAL_CONTENT_ROOT / doc_id / "images" / filename
        
        # Security check: ensure path is within content root
        try:
            image_path.resolve().relative_to(settings.LOCAL_CONTENT_ROOT.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Determine content type from extension
        ext = image_path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
        }
        media_type = media_types.get(ext, "image/png")
        
        return FileResponse(
            path=image_path,
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
