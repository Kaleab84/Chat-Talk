# Chat-Talk Structure Overview

This document is a quick reference for where things live in the repo and what the most important pieces do.

```
Chat-Talk/
├─ main.py                   # FastAPI entry point that wires routes, settings, and startup logic
├─ requirements.txt          # Python dependencies for local and server installs
├─ app/
│  ├─ config.py              # Central settings (paths, chunk sizes, API keys, session config)
│  ├─ api/
│  │  ├─ endpoints/
│  │  │  ├─ health.py        # Basic uptime + dependency checks
│  │  │  ├─ ingest.py        # Document ingestion routes
│  │  │  └─ chat.py          # Search/chat endpoints
│  │  └─ models/
│  │     ├─ requests.py      # Pydantic request payloads
│  │     └─ responses.py     # Pydantic responses
│  ├─ core/
│  │  ├─ vector_store.py     # Pinecone helpers for storing/searching embeddings
│  │  ├─ embeddings.py       # SentenceTransformer loading and embedding helpers
│  │  └─ rag.py              # Retrieval-Augmented Generation orchestration
│  ├─ services/
│  │  ├─ document_processor.py # Reads DOCX/DOC files, extracts text/images, builds chunks
│  │  ├─ content_repository.py # Saves processed sections/images to local storage
│  │  └─ chat_service.py       # Business logic for answering questions with retrieved context
│  └─ utils/
│     ├─ text_processing.py  # Split/clean text and extract metadata
│     └─ file_handlers.py    # Utility code for handling local files
├─ data/
│  ├─ documents/             # Source docs grouped by type (docx, doc, txt, etc.)
│  ├─ videos/                # Uploaded videos and transcripts
│  └─ processed/             # Output from the ingestion pipeline (chunks, images, metadata)
├─ tests/
│  ├─ test_content_repository_utils.py
│  ├─ test_document_processor.py
│  └─ test_text_processing.py
└─ README.md / SETUP_GUIDE.md # High-level project overview and local setup steps
```

## Important Files at a Glance

- `main.py`: creates the FastAPI app, mounts routers from `app.api`, and sets global middleware such as CORS.
- `app/config.py`: single source of truth for environment variables, paths, chunk settings, Pinecone/Supabase info, and session options.
- `app/api/endpoints/ingest.py`: accepts document uploads or directory ingests and kicks off `DocumentProcessor`.
- `app/services/document_processor.py`: handles DOC/DOCX conversion, table extraction, chunking (`_build_chunks`), and image harvesting before persisting results.
- `app/services/content_repository.py`: writes processed sections/images to `data/processed/content_repository` with predictable naming and metadata.
- `app/core/vector_store.py`: wraps Pinecone CRUD with helper methods used by chat/search flows.
- `app/services/chat_service.py`: combines retrieval (`vector_store`, `rag`) with LLM responses (placeholder/OpenAI pipeline) for `POST /ask` and related routes.
- `app/utils/text_processing.py`: reusable utilities for cleaning text, splitting into overlapping chunks, and tagging metadata; heavily used during ingestion.
- `tests/…`: Pytest coverage for filename handling + storage behaviour, document chunking, and text utilities to keep regressions in check.

Use this as a map when exploring or extending the project. Update it whenever directories or responsibilities shift so the structure stays discoverable.
