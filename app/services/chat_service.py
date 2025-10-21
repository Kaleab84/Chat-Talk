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

            # If OpenAI is configured, generate a grounded answer; otherwise use simple stub
            if settings.OPENAI_API_KEY:
                try:
                    answer = self._generate_gpt_answer(question, formatted_context)
                except Exception as gpt_exc:
                    logger.warning(f"OpenAI generation failed, falling back to stub: {gpt_exc}")
                    answer = self._generate_simple_answer(question, context_chunks, formatted_context)
            else:
                answer = self._generate_simple_answer(question, context_chunks, formatted_context)

            return {
                "success": True,
                "question": question,
                "answer": answer,
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
        
        # Return the most relevant chunk with some formatting
        best_match = context_chunks[0]
        answer = f"Based on the documentation, here's what I found:\n\n"
        answer += f"{best_match['text'][:500]}..."
        
        if len(context_chunks) > 1:
            answer += f"\n\nAdditional relevant information is available from {len(context_chunks) - 1} other sources."
        
        return answer

    def _generate_gpt_answer(self, question: str, formatted_context: str) -> str:
        """Use OpenAI Chat Completions to generate a grounded answer from context."""
        # Lazy import to avoid hard dependency if key is unset
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"OpenAI SDK not available: {exc}")

        client = OpenAI()

        system_prompt = (
            "You are a helpful assistant that answers strictly based on the provided context. "
            "If the context does not contain the answer, say you do not have enough information. "
            "Respond clearly and concisely."
        )
        user_prompt = (
            f"Question:\n{question}\n\n"
            f"Context (extracts from company docs):\n{formatted_context}\n\n"
            "Answer:"
        )

        resp = client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=500,
        )

        content = resp.choices[0].message.content if resp and resp.choices else None
        if not content:
            raise RuntimeError("Empty response from OpenAI")
        return content.strip()
    
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





