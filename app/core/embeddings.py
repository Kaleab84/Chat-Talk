from typing import List, Optional
from sentence_transformers import SentenceTransformer
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingModel:
    """Sentence transformer embedding model management."""
    
    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
        self.model_name = settings.EMBED_MODEL_NAME
    
    def load_model(self):
        """Load the embedding model."""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
    
    def encode(self, texts: List[str], show_progress: bool = False) -> List[List[float]]:
        """Encode texts into embeddings."""
        if self.model is None:
            self.load_model()
        
        try:
            embeddings = self.model.encode(texts, show_progress_bar=show_progress)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to encode texts: {e}")
            raise
    
    def encode_query(self, query: str) -> List[float]:
        """Encode a single query into embedding."""
        if self.model is None:
            self.load_model()
        
        try:
            embedding = self.model.encode([query])[0]
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to encode query: {e}")
            raise