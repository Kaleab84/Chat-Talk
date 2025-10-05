from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class HealthResponse(BaseModel):
    """Response model for health check."""
    ok: bool
    message: str
    version: Optional[str] = None

class IngestResponse(BaseModel):
    """Response model for document ingestion."""
    success: bool
    message: str
    chunks_processed: Optional[int] = None
    sections_processed: Optional[int] = None
    images_processed: Optional[int] = None
    doc_id: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None

class BulkIngestResponse(BaseModel):
    """Response model for bulk document ingestion."""
    success: bool
    message: str
    successful_files: int
    failed_files: int
    total_chunks: int
    total_sections: Optional[int] = None
    total_images: Optional[int] = None
    errors: Optional[List[Dict[str, str]]] = None

class SearchResult(BaseModel):
    """Individual search result model."""
    rank: int
    score: float
    text: str
    source: str
    source_type: str
    chunk_id: str
    doc_id: Optional[str] = None
    section_id: Optional[str] = None
    section_path: Optional[str] = None
    section_title: Optional[str] = None
    image_paths: Optional[List[str]] = None

class SearchResponse(BaseModel):
    """Response model for document search."""
    success: bool
    query: str
    results: List[SearchResult]
    total_results: int
    error: Optional[str] = None

class AskResponse(BaseModel):
    """Response model for asking questions."""
    success: bool
    question: str
    answer: Optional[str] = None
    context_used: List[SearchResult]
    confidence: Optional[float] = None
    error: Optional[str] = None

class RecommendationItem(BaseModel):
    """Individual recommendation item model."""
    title: str
    relevance_score: float
    preview: str
    source_type: str
    doc_id: Optional[str] = None
    section_id: Optional[str] = None
    section_path: Optional[str] = None
    section_title: Optional[str] = None
    image_paths: Optional[List[str]] = None

class Recommendations(BaseModel):
    """Collection of recommendations by type."""
    documents: List[RecommendationItem]
    videos: List[RecommendationItem]
    related_topics: List[RecommendationItem]

class RecommendationResponse(BaseModel):
    """Response model for recommendations."""
    success: bool
    query: str
    recommendations: Recommendations
    total_items: int
    error: Optional[str] = None

class NamespaceStats(BaseModel):
    """Namespace-level vector statistics."""
    name: str
    vector_count: int


class VectorStoreStatsResponse(BaseModel):
    """Vector store visibility response model."""
    success: bool
    index_name: str
    total_vectors: int
    dimension: Optional[int] = None
    index_fullness: Optional[float] = None
    namespaces: List[NamespaceStats] = Field(default_factory=list)
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None





