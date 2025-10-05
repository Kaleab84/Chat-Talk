from pathlib import Path
import os
from typing import Optional

class Settings:
    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    DOCUMENTS_DIR = DATA_DIR / "documents"
    VIDEOS_DIR = DATA_DIR / "videos"
    PROCESSED_DIR = DATA_DIR / "processed"
    
    # API Settings
    API_TITLE = "CFC Animal Feed Software Chatbot API"
    API_VERSION = "1.0.0"
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    
    # Model Settings
    EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    EMBED_DIMENSION = 384
    
    # Chunking Settings
    CHUNK_SIZE = 600
    CHUNK_OVERLAP = 120
    
    # Pinecone Settings
    PINECONE_API_KEY: Optional[str] = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "cfc-animal-feed-chatbot")
    PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
    
    # Supabase / Content Storage Settings
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_BUCKET: Optional[str] = os.getenv("SUPABASE_BUCKET")
    LOCAL_CONTENT_ROOT = PROCESSED_DIR / "content_repository"
    # OpenAI Settings (for future GPT integration)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = "gpt-3.5-turbo"
    
    # Search Settings
    DEFAULT_TOP_K = 5
    MAX_CONTEXT_LENGTH = 4000

settings = Settings()


