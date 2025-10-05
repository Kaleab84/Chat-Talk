from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException

from app.api.models.requests import BulkIngestRequest, IngestRequest
from app.api.models.responses import BulkIngestResponse, IngestResponse
from app.config import settings
from app.core.embeddings import EmbeddingModel
from app.core.vector_store import VectorStore
from app.services.content_repository import ContentRepository
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Initialize services
_document_processor = DocumentProcessor()
_vector_store = VectorStore()
_embedding_model = EmbeddingModel()
_content_repository = ContentRepository()


@router.post("/document", response_model=IngestResponse)
async def ingest_document(request: IngestRequest) -> IngestResponse:
    """Ingest a single document into storage and the vector index."""
    try:
        file_path = _locate_document(request.filename)
        processed = _document_processor.process_document(file_path)

        if not processed.get("success"):
            raise HTTPException(status_code=400, detail=processed.get("error", "Unknown processing error"))

        updated = _persist_document_content(processed)
        vectors, chunk_count = _prepare_vectors(updated["chunks"])

        if vectors:
            _vector_store.upsert_vectors(vectors)

        logger.info(
            "Successfully ingested %s: %s sections, %s chunks, %s images",
            request.filename,
            updated["section_count"],
            chunk_count,
            updated["image_count"],
        )

        return IngestResponse(
            success=True,
            message=f"Successfully ingested {request.filename}",
            chunks_processed=chunk_count,
            sections_processed=updated["section_count"],
            images_processed=updated["image_count"],
            doc_id=updated["doc_id"],
            source=str(file_path),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error ingesting document %s: %s", request.filename, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/bulk", response_model=BulkIngestResponse)
async def bulk_ingest(request: BulkIngestRequest) -> BulkIngestResponse:
    """Ingest all documents from the documents directory."""
    try:
        directory = settings.DOCUMENTS_DIR / request.subdirectory if request.subdirectory else settings.DOCUMENTS_DIR
        if not directory.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory}")

        results = _document_processor.process_directory(directory)
        if not results:
            return BulkIngestResponse(
                success=True,
                message="No supported documents found in directory",
                successful_files=0,
                failed_files=0,
                total_chunks=0,
            )

        total_chunks = 0
        total_sections = 0
        total_images = 0
        successful_files = 0
        failed_files = 0
        errors: List[Dict[str, str]] = []

        for result in results:
            if result.get("success"):
                updated = _persist_document_content(result)
                vectors, chunk_count = _prepare_vectors(updated["chunks"])
                if vectors:
                    _vector_store.upsert_vectors(vectors)
                total_chunks += chunk_count
                total_sections += updated["section_count"]
                total_images += updated["image_count"]
                successful_files += 1
                logger.info(
                    "Processed %s: %s sections, %s chunks", result.get("source"), updated["section_count"], chunk_count
                )
            else:
                failed_files += 1
                errors.append({
                    "file": Path(result.get("source", "unknown")).name,
                    "error": result.get("error", "Unknown error"),
                })
                logger.error("Failed to process %s: %s", result.get("source"), result.get("error"))

        return BulkIngestResponse(
            success=True,
            message=f"Bulk ingestion completed: {successful_files} successful, {failed_files} failed",
            successful_files=successful_files,
            failed_files=failed_files,
            total_chunks=total_chunks,
            total_sections=total_sections,
            total_images=total_images,
            errors=errors or None,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error in bulk ingestion: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def _locate_document(filename: str) -> Path:
    possible_paths = [
        settings.DOCUMENTS_DIR / filename,
        settings.DOCUMENTS_DIR / "docx" / filename,
        settings.DOCUMENTS_DIR / "doc" / filename,
        settings.DATA_DIR / filename,
    ]
    for path in possible_paths:
        if path.exists():
            return path
    raise HTTPException(status_code=404, detail=f"File '{filename}' not found in any of the expected locations")


def _persist_document_content(processed: Dict[str, Any]) -> Dict[str, Any]:
    doc_id: str = processed["doc_id"]
    sections: List[Dict] = processed.get("sections", [])
    images: List[Dict] = processed.get("images", [])

    stored_images = _content_repository.store_images(doc_id, images) if images else {}
    placeholder_to_path: Dict[str, str] = {}
    for image in images:
        storage = stored_images.get(image["image_id"])
        if storage:
            placeholder = f"images/{image['image_id']}{image.get('extension', '')}"
            placeholder_to_path[placeholder] = storage.storage_path
            image["storage_path"] = storage.storage_path
            image.pop("data", None)

    section_paths: Dict[str, str] = {}
    for section in sections:
        for block in section.get("blocks", []):
            if block.get("type") == "image":
                placeholder = block.get("path")
                if placeholder and placeholder in placeholder_to_path:
                    block["path"] = placeholder_to_path[placeholder]
                    block["storage_path"] = placeholder_to_path[placeholder]
        section["storage_path"] = f"docs/{doc_id}/sections/{section['section_id']}.json"
        stored_section = _content_repository.store_section(doc_id, section)
        section_paths[section["section_id"]] = stored_section.storage_path
        section["storage_path"] = stored_section.storage_path

    updated_chunks: List[Dict] = []
    for chunk in processed.get("chunks", []):
        chunk_copy = {**chunk}
        chunk_copy["section_path"] = section_paths.get(chunk_copy["section_id"])
        chunk_copy["image_paths"] = [placeholder_to_path.get(path, path) for path in chunk_copy.get("image_paths", [])]
        updated_chunks.append(chunk_copy)

    processed["sections"] = sections
    processed["images"] = images
    processed["chunks"] = updated_chunks
    processed["section_count"] = len(sections)
    processed["image_count"] = len(images)
    processed["section_paths"] = section_paths
    processed["chunk_count"] = len(updated_chunks)
    return processed


def _prepare_vectors(chunks: List[Dict]) -> Tuple[List[Tuple[str, List[float], Dict]], int]:
    if not chunks:
        return [], 0
    texts = [chunk["text"] for chunk in chunks]
    embeddings = _embedding_model.encode(texts)
    vectors: List[Tuple[str, List[float], Dict]] = []
    for index, chunk in enumerate(chunks):
        metadata = {k: v for k, v in chunk.items() if k != "text"}
        metadata["content"] = chunk.get("text")
        vectors.append((chunk["chunk_id"], embeddings[index], metadata))
    return vectors, len(chunks)








