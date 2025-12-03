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
        self.embedding_model = EmbeddingModel()
        self.vector_store = VectorStore()
        self.document_rag_pipeline = RAGPipeline(
            vector_store=self.vector_store,
            embedding_model=self.embedding_model,
        )

        video_index_name = getattr(settings, "PINECONE_VIDEO_INDEX_NAME", self.vector_store.index_name)
        if video_index_name == self.vector_store.index_name:
            self.video_vector_store = self.vector_store
        else:
            self.video_vector_store = VectorStore(index_name=video_index_name)
        self.video_rag_pipeline = RAGPipeline(
            vector_store=self.video_vector_store,
            embedding_model=self.embedding_model,
        )

        self._log_vector_store_details(self.vector_store, "Document")
        self._log_vector_store_details(self.video_vector_store, "Video")

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
            
            context_chunks = self.document_rag_pipeline.retrieve_context(query, top_k)
            
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
        """Get context-aware response to a question (documents + general knowledge)."""
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
            context_chunks = self.document_rag_pipeline.retrieve_context(question, top_k)
            
            if not context_chunks:
                return {
                    "success": True,
                    "question": question,
                    "answer": "I couldn't find relevant information to answer your question. This might be because the question is outside the scope of the ingested documents. Please try rephrasing or asking about topics covered in the uploaded documents.",
                    "context_used": [],
                    "confidence": 0.0
                }
            
            # Format context
            formatted_context = self.document_rag_pipeline.format_context(context_chunks)

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
                "confidence": self._calculate_confidence(context_chunks),
                **self._extract_primary_video_reference([]),
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "answer": None
            }

    def ask_video_question(self, question: str, top_k: int = None) -> Dict[str, Any]:
        """Answer a question using only video transcript context."""
        try:
            if top_k is None:
                top_k = settings.DEFAULT_TOP_K

            if self._is_vector_store_empty(self.video_vector_store):
                return {
                    "success": False,
                    "question": question,
                    "answer": "No content has been ingested yet. Please upload and process video transcripts before asking questions.",
                    "context_used": [],
                    "confidence": 0.0,
                    "error": "empty_vector_store"
                }

            metadata_filter = {"source_type": {"$eq": "video"}}
            logger.info(
                "ask_video_question retrieval -> index=%s namespace=%s filter=%s",
                self.video_vector_store.index_name,
                getattr(self.video_vector_store, "namespace", None) or "default",
                metadata_filter,
            )

            context_chunks = self.video_rag_pipeline.retrieve_context(
                question,
                top_k,
                metadata_filter=metadata_filter,
            )
            if not context_chunks:
                logger.warning("No video matches found with metadata filter; retrying without filter for diagnostics.")
                context_chunks = self.video_rag_pipeline.retrieve_context(question, top_k)

            video_context = self._build_video_context(context_chunks)

            if not context_chunks:
                return {
                    "success": True,
                    "question": question,
                    "answer": "I couldn't find any video transcripts related to that question. Please try rephrasing or pick another video topic.",
                    "context_used": [],
                    "confidence": 0.0,
                    "video_context": [],
                    **self._extract_primary_video_reference([]),
                }

            formatted_context = self.video_rag_pipeline.format_context(context_chunks)

            if settings.OPENAI_API_KEY:
                try:
                    answer = self._generate_gpt_answer(question, formatted_context)
                except Exception as gpt_exc:
                    logger.warning(f"OpenAI generation failed for video question, falling back to stub: {gpt_exc}")
                    answer = self._generate_simple_answer(question, context_chunks, formatted_context)
            else:
                answer = self._generate_simple_answer(question, context_chunks, formatted_context)

            answer = self._attach_video_references(answer, video_context)

            return {
                "success": True,
                "question": question,
                "answer": answer,
                "context_used": context_chunks,
                "confidence": self._calculate_confidence(context_chunks),
                "video_context": video_context,
                **self._extract_primary_video_reference(video_context),
            }

        except Exception as e:
            logger.error(f"Error answering video question: {e}")
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

    def _build_video_context(self, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collect per-video metadata that callers can render."""
        clips: List[Dict[str, Any]] = []
        for chunk in context_chunks:
            if chunk.get("source_type") != "video":
                continue
            video_url = chunk.get("video_url")
            if not video_url:
                continue

            start = chunk.get("start_seconds")
            end = chunk.get("end_seconds")
            clip = {
                "video_url": video_url,
                "start_seconds": start,
                "end_seconds": end,
                "timestamp": self._format_timestamp(start),
                "end_timestamp": self._format_timestamp(end),
                "deep_link_url": self._build_video_link(video_url, start),
                "preview": (chunk.get("text") or "")[:240],
            }
            clips.append(clip)
        return clips

    def _format_timestamp(self, seconds: Optional[float]) -> Optional[str]:
        """Return HH:MM:SS timestamp for display."""
        if seconds is None:
            return None
        try:
            seconds = max(0, int(float(seconds)))
        except (TypeError, ValueError):
            return None
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _build_video_link(self, video_url: str, start_seconds: Optional[float]) -> str:
        """Append a fragment so web players can seek directly."""
        if start_seconds is None:
            return video_url
        try:
            start = max(0, int(float(start_seconds)))
        except (TypeError, ValueError):
            return video_url
        return f"{video_url}#t={start}"

    def _attach_video_references(self, answer: str, video_context: List[Dict[str, Any]]) -> str:
        """Append human-readable video references to the answer text."""
        if not video_context:
            return answer

        lines = ["Video reference:" if len(video_context) == 1 else "Video references:"]
        for clip in video_context[:3]:
            timestamp = clip.get("timestamp") or f"{int(clip.get('start_seconds', 0))}s"
            link = clip.get("deep_link_url") or clip.get("video_url")
            if not link:
                continue
            lines.append(f"- {timestamp}: {link}")

        if len(lines) == 1:
            return answer
        joiner = "\n".join(lines)
        if answer.endswith("\n"):
            return f"{answer.rstrip()}\n\n{joiner}"
        return f"{answer}\n\n{joiner}"
    
    def _extract_primary_video_reference(self, video_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return a single clip descriptor for clients that only need one video/timestamp."""
        default = {
            "answer_video_url": None,
            "answer_start_seconds": None,
            "answer_end_seconds": None,
            "answer_timestamp": None,
            "answer_end_timestamp": None,
        }
        if not video_context:
            return default
        clip = video_context[0]
        return {
            "answer_video_url": clip.get("deep_link_url") or clip.get("video_url"),
            "answer_start_seconds": clip.get("start_seconds"),
            "answer_end_seconds": clip.get("end_seconds"),
            "answer_timestamp": clip.get("timestamp"),
            "answer_end_timestamp": clip.get("end_timestamp"),
        }

    def _log_vector_store_details(self, store: VectorStore, label: str) -> None:
        """Log which Pinecone index/namespace a store is targeting."""
        namespace = getattr(store, "namespace", None) or "default"
        logger.info("%s vector store configured -> index=%s namespace=%s", label, store.index_name, namespace)
    
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
    
    def _is_vector_store_empty(self, store: Optional[VectorStore] = None) -> bool:
        """Return True when the vector store has no stored vectors."""
        try:
            target_store = store or self.vector_store
            stats = target_store.get_index_stats()
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





