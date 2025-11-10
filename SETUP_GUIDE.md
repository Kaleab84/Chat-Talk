# ⚙️ Setup Guide

Follow these steps and you’ll have the chatbot backend running in minutes.

## 1️⃣ Clone & Install
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```
Tip: keep the virtualenv around so future installs are instant. WE NEED THIS!

Also if you get: "cannot be loaded because running scripts is disabled on this system"
```bash
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force #windows
```


## 2️⃣ Configure Secrets
```bash
cp .env.example .env
```
Open `.env` and add:
- `PINECONE_API_KEY` – required for search.
- Optional: Supabase + OpenAI keys if you’re connecting cloud storage or GPT later.
- You can ask me (Nift) or check discord for the Pinconce Key.

## 3️⃣ Start the API
```bash
uvicorn main:app --reload
```
Browse to [http://localhost:8000/docs](http://localhost:8000/docs) and try out the interactive endpoints.

## 4️⃣ Ingest Docs
1. Drop `.doc`, `.docx`, or `.txt` files into `data/documents/`.
2. Call:
   ```bash
   curl -X POST http://localhost:8000/ingest/document \
     -H "Content-Type: application/json" \
     -d '{"filename": "your-file.docx"}'
   ```
3. Peek at `data/processed/content_repository/<doc-slug>/` – you’ll see readable section JSON files plus any extracted images.

## 5️⃣ Search & Ask
- `/search` returns the best chunks with section/image paths.
- `/ask` returns the same context plus a friendly answer stub.
- `/visibility/vector-store` shows how many vectors Pinecone currently stores.

## 🆘 Need Help?
- Conversion errors? Make sure Office/LibreOffice is installed for `.doc` conversions.
- Pinecone issues? Double-check the API key and region in `.env`.
- Looking ahead? Swap `content_repository.py` for Supabase when you’re ready for cloud storage.
