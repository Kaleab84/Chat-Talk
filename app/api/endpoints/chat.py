from fastapi import APIRouter, HTTPException, Depends
import logging
from app.api.models.requests import SearchRequest, AskRequest, RecommendationRequest
from app.api.models.responses import SearchResponse, AskResponse, RecommendationResponse, SearchResult
from app.services.chat_service import ChatService
from app.auth.dependencies import require_user
from app.rate_limit.limiter import limit

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"], dependencies=[Depends(require_user)])

# Initialize chat service
chat_service = ChatService()

@router.post("/search", response_model=SearchResponse, dependencies=[Depends(limit("30/minute"))])
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

@router.post("/ask", response_model=AskResponse, dependencies=[Depends(limit("20/minute"))])
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
            )
            for item in result["context_used"]
        ]
        
        return AskResponse(
            success=True,
            question=request.question,
            answer=result["answer"],
            context_used=context_results,
            confidence=result.get("confidence")
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
