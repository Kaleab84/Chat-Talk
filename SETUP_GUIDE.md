# ⚙️ Setup Guide

Follow these steps and you’ll have the chatbot backend running in minutes.

## 1️⃣ Clone & Install
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```
Tip: keep the virtualenv around so future installs are instant. WE NEED THIS!

## 2️⃣ Configure Secrets
```bash
copy .env.example .env
```
Open `.env` and add:
- `PINECONE_API_KEY` – required for search.
- Optional: Supabase keys if you’re connecting cloud storage.
- Optional but recommended: `OPENAI_API_KEY` to enable GPT‑generated answers in the Ask chat.
- You can ask me (Nift) or check discord for the Pincone Key.

## 3️⃣ Start the API
```bash
uvicorn main:app --reload
```
Browse to [http://localhost:8000/docs](http://localhost:8000/docs) and try out the interactive endpoints.
Or visit the prettier web UI at [http://localhost:8000/ui](http://localhost:8000/ui) for drag‑and‑drop uploads and quick search/ask.

## 4️⃣ Ingest Docs
Upload and ingest in one step (single file or via UI):
- Use the upload endpoint; it automatically ingests after saving the file locally.
  ```bash
  curl -X POST "http://localhost:8000/files/upload" \
       -H "Content-Type: multipart/form-data" \
       -F "file=@your-file.docx"
  ```
 - Or open the web UI at `/ui` and drag & drop.

Bulk upload and ingest:
- Send multiple files in one request; each file is saved and ingested.
  ```bash
  curl -X POST "http://localhost:8000/files/bulk" \
       -H "Content-Type: multipart/form-data" \
       -F "files=@doc1.docx" \
       -F "files=@doc2.txt"
  ```

After the request completes, check `data/processed/content_repository/<doc-slug>/` for readable section JSON files and any extracted images.

## 5️⃣ Search & Ask
- `/search` returns the best chunks with section/image paths.
- `/ask` returns the same context plus a friendly answer stub.
- `/visibility/vector-store` shows how many vectors Pinecone currently stores.

## 🆘 Need Help?
- Conversion errors? Make sure Office/LibreOffice is installed for `.doc` conversions.
- Pinecone issues? Double-check the API key and region in `.env`.
- Looking ahead? Swap `content_repository.py` for Supabase when you’re ready for cloud storage.

## Attach Images to Chat Questions
- Use POST /ask-with-media (multipart/form-data).
- Fields: question (text), 	op_k (int, optional), images (png/jpg/jpeg/webp).
- Requires GEMINI_API_KEY for multimodal image support.

