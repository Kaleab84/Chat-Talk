from fastapi import APIRouter, UploadFile, File, HTTPException
from supabase import create_client
import os
from pathlib import Path
from dotenv import load_dotenv

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
bucket = os.getenv("SUPABASE_BUCKET")

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not url or not key or not bucket:
        raise HTTPException(
            status_code=503,
            detail="Supabase storage is not configured. Please set SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_BUCKET."
        )

    try:
        supabase = create_client(url, key)
        contents = await file.read()
        res = supabase.storage.from_(bucket).upload(file.filename, contents)
        return {"message": "File uploaded successfully", "path": res.path}
    except Exception as e:
        return {"error": str(e)}
