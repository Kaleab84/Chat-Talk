from typing import List, Dict, Any, Optional
import logging

from app.config import settings
from app.core.embeddings import EmbeddingModel
from app.core.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline."""

    def __init__(self) -> None:
        self.vector_store = VectorStore()
        self.embedding_model = EmbeddingModel()

    def retrieve_context(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query."""
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K

        try:
            query_embedding = self.embedding_model.encode_query(query)

            raw_matches: List[Dict[str, Any]] = []
            seen_ids: set[str] = set()

            for namespace in self._namespaces_to_query():
                results = self.vector_store.query(
                    vector=query_embedding,
                    top_k=top_k,
                    include_metadata=True,
                    namespace=namespace,
                )

                for match in results.get("matches", []):
                    match_id = match.get("id")
                    if match_id and match_id in seen_ids:
                        continue
                    raw_matches.append({
                        "namespace": namespace,
                        "match": match,
                    })
                    if match_id:
                        seen_ids.add(match_id)

            raw_matches.sort(key=lambda item: item["match"].get("score", 0.0), reverse=True)
            trimmed_matches = raw_matches[:top_k]

            context_chunks: List[Dict[str, Any]] = []
            for index, item in enumerate(trimmed_matches, start=1):
                match = item["match"]
                metadata = match.get("metadata", {}) or {}
                start_seconds = metadata.get("start_seconds", metadata.get("start"))
                end_seconds = metadata.get("end_seconds", metadata.get("end"))
                transcript_urls = metadata.get("transcript_urls")
                if not transcript_urls:
                    transcript_urls = {
                        key: metadata.get(key)
                        for key in ("txt_url", "srt_url", "vtt_url")
                        if metadata.get(key)
                    }

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
                    "namespace": item["namespace"] or "default",
                    "video_slug": metadata.get("slug"),
                    "video_url": metadata.get("video_url"),
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "start_timecode": self._format_timecode(start_seconds),
                    "end_timecode": self._format_timecode(end_seconds),
                    "transcript_urls": transcript_urls or None,
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

    def _namespaces_to_query(self) -> List[Optional[str]]:
        """
        Determine which Pinecone namespaces to search.
        Ensures the configured namespace (if any) and the default namespace are included.
        """
        namespaces: List[Optional[str]] = []
        if self.vector_store.namespace:
            namespaces.append(self.vector_store.namespace)
        namespaces.append(None)  # default namespace

        # Deduplicate while preserving order
        deduped: List[Optional[str]] = []
        seen: set[Optional[str]] = set()
        for ns in namespaces:
            if ns not in seen:
                seen.add(ns)
                deduped.append(ns)
        return deduped

    @staticmethod
    def _format_timecode(seconds: Optional[float]) -> Optional[str]:
        if seconds is None:
            return None
        total_seconds = int(max(seconds, 0))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
