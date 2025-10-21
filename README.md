# Chat-Talk Backend ⚙️

Welcome to the CFC help chatbot backend! This FastAPI service turns company know-how (DOC/DOCX/TXT) into searchable knowledge: we ingest documents, carve them into structured JSON blocks, keep the matching images handy, and use Pinecone to retrieve the best answers for chat users. Once we get videos working we also have a spot saved up for that.

## 🚀 Why This Setup Works
- **Lighting-fast onboarding** – drop your docs into a folder and hit `/ingest`.
- **Human-friendly storage** – sections and images are saved with readable filenames so Supabase (or any storage) stays organised.
- **Extensible RAG** – swap embeddings, add GPT answer generation, or plug in a UI without touching the ingestion core.

## ⚡ Quick Start
1. **Clone & install requirements**
   > **Note:** Remember to clone the repo first if you haven't already.
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
2. **Configure secrets**
   ```bash
   # Windows (PowerShell)
   Copy-Item -LiteralPath '.env.example' -Destination '.env'
   # Windows (CMD)
   copy .env.example .env
   # macOS/Linux
   cp .env.example .env
   # Then edit .env and add your Pinecone API key (and Supabase/OpenAI keys when ready)
   ```
3. **Run the API**
   ```bash
   uvicorn main:app --reload
   ```
   Interactive docs live at [http://localhost:8000/docs](http://localhost:8000/docs).
   A simplified web UI lives at [http://localhost:8000/ui](http://localhost:8000/ui) for uploads and quick testing.

## One‑Step Upload (Recommended)
- Upload a file and trigger ingestion in one call:
  ```bash
  curl -X POST "http://localhost:8000/files/upload" \
       -H "Content-Type: multipart/form-data" \
       -F "file=@your-file.docx"
  ```
  The response includes ingestion results; processed sections and images are saved under `data/processed/content_repository/<doc-slug>/`.

### Bulk Upload
- Send multiple files in one request; each is saved and ingested:
  ```bash
  curl -X POST "http://localhost:8000/files/bulk" \
       -H "Content-Type: multipart/form-data" \
       -F "files=@doc1.docx" \
       -F "files=@doc2.txt"
  ```

## 🧠 How It Works
```
DOC/DOCX/TXT --> /ingest --> document_processor
    -> sections JSON + images (data/processed/...)
    -> embeddings --> Pinecone --> /search | /ask | /recommendations
```
- `main.py` loads `.env` (thanks to `python-dotenv`), sets up CORS, and registers routers.
- `document_processor.py` converts legacy `.doc` files, detects sections/headings/tables/images, and emits chunk metadata with doc slugs.
- `content_repository.py` currently writes to `data/processed/content_repository/<doc-slug>/`; the same filenames are ready for Supabase Storage when you flip the switch.
- `chat_service.py` + `app/core/rag.py` perform Pinecone lookups, return structured context, and calculate confidence scores.

## 🔗 Helpful Endpoints
- `POST /ingest/document` – process a single file by filename.
- `POST /ingest/bulk` – sweep an entire subdirectory.
- `POST /search` – get relevant chunks with section/image references.
- `POST /ask` – same results plus an answer stub (ready for GPT).
- `GET /visibility/vector-store` – quick Pinecone health check.

## ✅ Verify Setup
1. Ingest a document and check `data/processed/content_repository/<doc-slug>/sections/...` for readable JSON filenames.
2. Hit `/search` for a keyword and confirm the response includes the matching `section_path` + `image_paths`.
3. Visit `/visibility/vector-store` to see how many vectors Pinecone is holding.

## 🛠️ Next Steps
- Swap the local content repository for the Supabase SDK using the same filenames.
- Replace the placeholder answer generator with GPT (OpenAI key already wired for the future).
- Add a frontend or CLI that reads the JSON/image paths returned by the API.
- Extend the processor to cover PDF or video transcript ingestion.
