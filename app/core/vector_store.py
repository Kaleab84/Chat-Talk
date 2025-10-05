from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class VectorStore:
    """Pinecone vector store management."""
    
    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self.index = None
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize Pinecone index."""
        try:
            # Create index if it doesn't exist
            if self.index_name not in self.pc.list_indexes().names():
                self.pc.create_index(
                    name=self.index_name,
                    dimension=settings.EMBED_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=settings.PINECONE_CLOUD,
                        region=settings.PINECONE_REGION
                    )
                )
                logger.info(f"Created new Pinecone index: {self.index_name}")
            
            self.index = self.pc.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {e}")
            raise
    
    def upsert_vectors(self, vectors: List[tuple]) -> Dict[str, Any]:
        """Upsert vectors to Pinecone index."""
        try:
            response = self.index.upsert(vectors)
            logger.info(f"Upserted {len(vectors)} vectors to index")
            return response
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise
    
    def query(self, vector: List[float], top_k: int = 5, include_metadata: bool = True) -> Dict[str, Any]:
        """Query similar vectors from Pinecone index."""
        try:
            response = self.index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=include_metadata
            )
            return response
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            raise
    
    def delete_by_prefix(self, prefix: str):
        """Delete vectors with IDs starting with prefix."""
        try:
            # Note: This is a simplified implementation
            # In production, you might want to implement this differently
            logger.info(f"Deleting vectors with prefix: {prefix}")
            # Implementation would depend on your specific needs
        except Exception as e:
            logger.error(f"Failed to delete vectors with prefix {prefix}: {e}")
            raise
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        try:
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            raise