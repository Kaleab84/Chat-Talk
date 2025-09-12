from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import re
import math
import numpy as np

# Embeddings (local + free)
from sentence_transformers import SentenceTransformer
from docx import Document

app = FastAPI(title="CFC Chatbot API")

# -------- Config --------
DATA_DIR = Path(__file__).parent / "data"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # small+fast CPU

# -------- Simple in-memory "vector store" --------
class VectorIndex:
    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
        self.embeddings: Optional[np.ndarray] = None  # shape: (N, d)
        self.texts: List[str] = []
        self.source: Optional[str] = None

    def load_model(self):
        if self.model is None:
            self.model = SentenceTransformer(EMBED_MODEL_NAME)

    def build(self, texts: List[str], source: str):
        self.load_model()
        self.texts = texts
        self.source = source
        self.embeddings = np.array(self.model.encode(texts, show_progress_bar=False), dtype=np.float32)

    def search(self, query: str, top_k: int = 5):
        assert self.embeddings is not None and len(self.texts) > 0, "Index is empty. Ingest first."
        self.load_model()
        q = np.array(self.model.encode([query], show_progress_bar=False)[0], dtype=np.float32)
        # cosine similarity
        norms = np.linalg.norm(self.embeddings, axis=1) * (np.linalg.norm(q) + 1e-12)
        sims = (self.embeddings @ q) / (norms + 1e-12)
        idx = np.argsort(-sims)[:top_k]
        return [{"rank": int(i)+1, "score": float(sims[i]), "text": self.texts[i]} for i in idx]

INDEX = VectorIndex()

# -------- Helpers --------
def read_docx(path: Path) -> str:
    """Extract plain text from a .docx file."""
    doc = Document(str(path))
    paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(paras)

def split_into_chunks(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Rough tokenizer-free chunker by characters with overlap."""
    # normalize newlines; keep headings as anchors
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        # try to cut at a sentence boundary if possible
        cut = text.rfind(".", start, end)
        if cut == -1 or cut <= start + 0.5 * chunk_size:
            cut = end
        chunks.append(text[start:cut].strip())
        start = max(cut - overlap, cut)
    return [c for c in chunks if c]

# -------- Request/Response models --------
class IngestRequest(BaseModel):
    filename: Optional[str] = "sample_guide.docx"  # relative to data/

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class AskRequest(BaseModel):
    question: str
    top_k: Optional[int] = 4

# -------- Endpoints --------
@app.get("/")
def root():
    return {"ok": True, "message": "CFC Chatbot API running"}

@app.post("/ingest")
def ingest(req: IngestRequest):
    path = (DATA_DIR / req.filename).resolve()
    if not path.exists():
        return {"ok": False, "error": f"File not found: {path}"}

    text = read_docx(path)
    chunks = split_into_chunks(text, chunk_size=600, overlap=120)
    if not chunks:
        return {"ok": False, "error": "No text extracted from DOCX."}

    INDEX.build(chunks, source=str(path))
    return {
        "ok": True,
        "source": str(path),
        "num_chunks": len(chunks),
        "example_chunk": chunks[0][:240]
    }

@app.post("/search")
def search(req: SearchRequest):
    results = INDEX.search(req.query, top_k=req.top_k or 5)
    return {"ok": True, "results": results}

@app.post("/ask")
def ask(req: AskRequest):
    """Very naive 'answer' = top chunks stitched. Good enough for backend smoke-test."""
    hits = INDEX.search(req.question, top_k=req.top_k or 4)
    context = "\n\n".join(h["text"] for h in hits)
    return {
        "ok": True,
        "question": req.question,
        "context_snippets": hits,
        "answer_stub": context[:1200]  # stub: front-end (or LLM) would generate a nicer answer from context
    }
