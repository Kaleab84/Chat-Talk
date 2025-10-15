from fastapi import APIRouter, UploadFile, File
from supabase import create_client
import os
from dotenv import load_dotenv

router = APIRouter()

load_dotenv("app/.env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
bucket = os.getenv("SUPABASE_BUCKET")

supabase = create_client(url, key)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        res = supabase.storage.from_(bucket).upload(file.filename, contents)
        return {"message": "File uploaded successfully", "path": res.path}
    except Exception as e:
        return {"error": str(e)}
