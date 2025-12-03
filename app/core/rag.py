from typing import List, Dict, Any, Optional
import logging

from app.config import settings
from app.core.embeddings import EmbeddingModel
from app.core.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _to_float(value: Any) -> float | None:
    """Best-effort float conversion that tolerates None/strings."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_model: Optional[EmbeddingModel] = None,
    ) -> None:
        self.vector_store = vector_store or VectorStore()
        self.embedding_model = embedding_model or EmbeddingModel()

    def retrieve_context(
        self,
        query: str,
        top_k: int = None,
        metadata_filter: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query."""
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K

        try:
            query_embedding = self.embedding_model.encode_query(query)
            results = self.vector_store.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                metadata_filter=metadata_filter,
            )

            context_chunks: List[Dict[str, Any]] = []
            for index, match in enumerate(results.get("matches", []), start=1):
                metadata = match.get("metadata", {})
                context_chunks.append({
                    "rank": index,
                    "score": match.get("score"),
                    "text": metadata.get("content") or metadata.get("text", ""),
                    "source": metadata.get("source", ""),
                    "source_type": metadata.get("source_type", "document"),
                    "chunk_id": match.get("id"),
                    "doc_id": metadata.get("doc_id"),
                    "section_id": metadata.get("section_id"),
                    "section_title": metadata.get("section_title"),
                    "section_path": metadata.get("section_path"),
                    "image_paths": metadata.get("image_paths", []),
                    "block_ids": metadata.get("block_ids", []),
                    "start_seconds": _to_float(metadata.get("start_seconds")),
                    "end_seconds": _to_float(metadata.get("end_seconds")),
                    "video_url": metadata.get("video_url"),
                    "txt_url": metadata.get("txt_url"),
                    "srt_url": metadata.get("srt_url"),
                    "vtt_url": metadata.get("vtt_url"),
                })

            return context_chunks

        except Exception as exc:
            logger.error("Failed to retrieve context for query: %s", exc)
            raise

    def format_context(self, context_chunks: List[Dict[str, Any]], max_length: int = None) -> str:
        """Format context chunks into a single context string."""
        if max_length is None:
            max_length = settings.MAX_CONTEXT_LENGTH

        context_parts: List[str] = []
        total_length = 0

        for chunk in context_chunks:
            title_line = f"Title: {chunk['section_title']}\n" if chunk.get("section_title") else ""
            body = chunk.get("text") or ""
            chunk_text = f"Source: {chunk.get('source', '')}\n{title_line}{body}\n"

            if total_length + len(chunk_text) > max_length:
                break

            context_parts.append(chunk_text)
            total_length += len(chunk_text)

        return "\n---\n".join(context_parts)
