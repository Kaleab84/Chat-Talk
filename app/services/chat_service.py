from typing import List, Dict, Any, Optional
import logging
from app.core.rag import RAGPipeline
from app.core.vector_store import VectorStore
from app.core.embeddings import EmbeddingModel
from app.services.document_processor import DocumentProcessor
from app.config import settings

logger = logging.getLogger(__name__)

class ChatService:
    """Main service for chatbot interactions."""
    
    def __init__(self):
        self.rag_pipeline = RAGPipeline()
        self.vector_store = VectorStore()
        self.embedding_model = EmbeddingModel()
        self.document_processor = DocumentProcessor()
    
    def search_documents(self, query: str, top_k: int = None) -> Dict[str, Any]:
        """Search for relevant document chunks."""
        try:
            if top_k is None:
                top_k = settings.DEFAULT_TOP_K
            
            # Check if vector store has any data
            if self._is_vector_store_empty():
                return {
                    "success": False,
                    "query": query,
                    "results": [],
                    "total_results": 0,
                    "error": "No documents have been ingested yet. Please use the /ingest endpoint to upload and process documents."
                }
            
            context_chunks = self.rag_pipeline.retrieve_context(query, top_k)
            
            if not context_chunks:
                return {
                    "success": True,
                    "query": query,
                    "results": [],
                    "total_results": 0,
                    "message": "No relevant documents found for your query. Try different keywords or check if documents covering this topic have been uploaded."
                }
            
            return {
                "success": True,
                "query": query,
                "results": context_chunks,
                "total_results": len(context_chunks)
            }
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }
    
    def ask_question(self, question: str, top_k: int = None) -> Dict[str, Any]:
        """Get context-aware response to a question."""
        try:
            if top_k is None:
                top_k = settings.DEFAULT_TOP_K
            
            # Check if vector store has any data
            if self._is_vector_store_empty():
                return {
                    "success": False,
                    "question": question,
                    "answer": "No documents have been ingested yet. Please use the /ingest endpoint to upload and process documents before asking questions.",
                    "context_used": [],
                    "confidence": 0.0,
                    "error": "empty_vector_store"
                }
            
            # Retrieve relevant context
            context_chunks = self.rag_pipeline.retrieve_context(question, top_k)
            
            if not context_chunks:
                return {
                    "success": True,
                    "question": question,
                    "answer": "I couldn't find relevant information to answer your question. This might be because the question is outside the scope of the ingested documents. Please try rephrasing or asking about topics covered in the uploaded documents.",
                    "context_used": [],
                    "confidence": 0.0
                }
            
            # Format context
            formatted_context = self.rag_pipeline.format_context(context_chunks)
            
            # For now, return formatted context (GPT integration will come later)
            # TODO: Integrate with OpenAI GPT for actual answer generation
            answer_stub = self._generate_simple_answer(question, context_chunks, formatted_context)
            
            return {
                "success": True,
                "question": question,
                "answer": answer_stub,
                "context_used": context_chunks,
                "confidence": self._calculate_confidence(context_chunks)
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "answer": None
            }
    
    def _generate_simple_answer(self, question: str, context_chunks: List[Dict[str, Any]], formatted_context: str) -> str:
        """Generate a simple answer from context (placeholder for GPT integration)."""
        # This is a placeholder implementation
        # In the full version, this would integrate with OpenAI GPT
        
        if not context_chunks:
            return "No relevant information found."
        
        documents = [c for c in context_chunks if c.get("source_type") != "video"]
        videos = [c for c in context_chunks if c.get("source_type") == "video"]

        response_lines = []

        if documents:
            top_doc = documents[0]
            snippet = (top_doc.get("text") or "")[:500].strip()
            response_lines.append("Based on the documentation, here's what I found:\n")
            response_lines.append(snippet + ("..." if len(snippet) == 500 else ""))
        else:
            top_chunk = context_chunks[0]
            snippet = (top_chunk.get("text") or "")[:500].strip()
            response_lines.append("Here's the most relevant information I found:\n")
            response_lines.append(snippet + ("..." if len(snippet) == 500 else ""))

        if videos:
            response_lines.append("\nRelevant video segments:")
            for video_chunk in videos[:3]:
                slug = video_chunk.get("video_slug") or video_chunk.get("source") or "Video"
                ts = video_chunk.get("start_timecode")
                if not ts and video_chunk.get("start_seconds") is not None:
                    ts = self._format_timecode(video_chunk["start_seconds"])
                link = video_chunk.get("video_url")
                start_seconds = video_chunk.get("start_seconds")
                if link and start_seconds is not None:
                    link = self._append_time_query(link, int(start_seconds))
                snippet = (video_chunk.get("text") or "").strip()
                preview = snippet[:180] + ("..." if len(snippet) > 180 else "")
                line = f"- {slug}"
                if ts:
                    line += f" @ {ts}"
                if preview:
                    line += f": {preview}"
                if link:
                    line += f" ({link})"
                response_lines.append(line)

        if len(context_chunks) > 1:
            response_lines.append(f"\nAdditional relevant material was found in {len(context_chunks) - 1} other snippets.")

        return "\n".join(response_lines)

    def _format_timecode(self, seconds: float) -> str:
        seconds_int = int(max(seconds, 0))
        hours = seconds_int // 3600
        minutes = (seconds_int % 3600) // 60
        secs = seconds_int % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _append_time_query(self, url: str, start_seconds: int) -> str:
        """Append a timestamp query parameter to the URL when possible."""
        if "?" in url:
            return f"{url}&t={start_seconds}"
        return f"{url}?t={start_seconds}"
    
    def _calculate_confidence(self, context_chunks: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on context quality."""
        if not context_chunks:
            return 0.0
        
        # Simple confidence calculation based on top match score
        top_score = context_chunks[0].get('score', 0.0)
        
        # Normalize score to 0-1 range (assuming Pinecone cosine similarity)
        confidence = max(0.0, min(1.0, top_score))
        
        return round(confidence, 3)
    
    def get_recommendations(self, query: str, content_type: str = "all") -> Dict[str, Any]:
        """Get content recommendations based on query."""
        try:
            # Search for relevant content
            search_result = self.search_documents(query, top_k=10)
            
            if not search_result["success"]:
                return search_result
            
            # Group by source and content type
            recommendations = {
                "documents": [],
                "videos": [],
                "related_topics": []
            }
            
            for result in search_result["results"]:
                source_type = result.get("source_type", "document")
                
                rec_item = {
                    "title": result.get("source"),
                    "relevance_score": result.get("score"),
                    "preview": (result.get("text") or "")[:200] + "...",
                    "source_type": source_type,
                    "doc_id": result.get("doc_id"),
                    "section_id": result.get("section_id"),
                    "section_path": result.get("section_path"),
                    "section_title": result.get("section_title"),
                    "image_paths": result.get("image_paths", []),
                    "video_slug": result.get("video_slug"),
                    "video_url": result.get("video_url"),
                    "start_seconds": result.get("start_seconds"),
                    "start_timecode": result.get("start_timecode"),
                    "transcript_urls": result.get("transcript_urls"),
                }
                
                if source_type == "video":
                    recommendations["videos"].append(rec_item)
                else:
                    recommendations["documents"].append(rec_item)
            
            # Remove duplicates and sort by relevance
            recommendations["documents"] = self._deduplicate_recommendations(recommendations["documents"])
            recommendations["videos"] = self._deduplicate_recommendations(recommendations["videos"])
            
            return {
                "success": True,
                "query": query,
                "recommendations": recommendations,
                "total_items": len(recommendations["documents"]) + len(recommendations["videos"])
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "recommendations": {"documents": [], "videos": [], "related_topics": []}
            }
    
    def _is_vector_store_empty(self) -> bool:
        """Return True when the vector store has no stored vectors."""
        try:
            stats = self.vector_store.get_index_stats()
        except AttributeError:
            logger.warning("VectorStore is missing get_index_stats(); skipping empty-store check.")
            return False
        except Exception as e:
            logger.warning(f"Could not check vector store stats: {e}")
            return False

        total_vectors = stats.get("total_vector_count")
        if total_vectors is None:
            namespaces = stats.get("namespaces") or {}
            total_vectors = sum(ns.get("vectorCount", 0) for ns in namespaces.values())

        return total_vectors == 0

    def _deduplicate_recommendations(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate recommendations based on title."""
        seen_titles = set()
        unique_items = []
        
        for item in sorted(items, key=lambda x: x["relevance_score"], reverse=True):
            if item["title"] not in seen_titles:
                seen_titles.add(item["title"])
                unique_items.append(item)
        
        return unique_items[:5]  # Limit to top 5





