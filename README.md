# Chat-Talk Backend ⚙️

Welcome to the CFC help chatbot backend! This FastAPI service turns company know-how (DOC/DOCX/TXT) into searchable knowledge: we ingest documents, carve them into structured JSON blocks, keep the matching images handy, and use Pinecone to retrieve the best answers for chat users. Once we get videos working we also have a spot saved up for that.

## 🚀 Why This Setup Works
- **Lighting-fast onboarding** – drop your docs into a folder and hit `/ingest`.
- **Human-friendly storage** – sections and images are saved with readable filenames so Supabase (or any storage) stays organised.
- (**Might not need md format**)
- **Extensible RAG** – swap embeddings, add GPT answer generation, or plug in a UI without touching the ingestion core.

## ⚡ Quick Start
1. **Clone & install requirements**
   : Remember to clone the repo first, if not done.
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
2. **Configure secrets**
   ```bash
   cp .env.example .env
   # add your Pinecone API key (and Supabase/OpenAI keys when ready)
   ```
3. **Run the API**
   ```bash
   uvicorn main:app --reload
   ```
   Interactive docs live at [http://localhost:8000/docs](http://localhost:8000/docs).

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

Ask me (Nift) on questions!
