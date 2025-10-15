from __future__ import annotations
import os
import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


@dataclass
class StoredSection:
    section_id: str
    storage_path: str
    public_url: str


@dataclass
class StoredImage:
    image_id: str
    storage_path: str
    public_url: str


class SupabaseContentRepository:
    """Handles persistence of section JSON and images on Supabase."""

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY")
        self.bucket = os.getenv("SUPABASE_BUCKET", "cfc-docs")
        self.client = create_client(self.url, self.key)

    def store_section(self, doc_id: str, section: Dict) -> StoredSection:
        section_id = section["section_id"]
        filename = f"{section_id}.json"
        storage_path = f"docs/{doc_id}/sections/{filename}"

        data = json.dumps(section, ensure_ascii=False, indent=2).encode("utf-8")
        self.client.storage.from_(self.bucket).upload(storage_path, data, {"upsert": "true"})

        public_url = self.client.storage.from_(self.bucket).get_public_url(storage_path)
        return StoredSection(section_id=section_id, storage_path=storage_path, public_url=public_url)

    def store_image(self, doc_id: str, image: Dict) -> StoredImage:
        image_id = image["image_id"]
        filename = image.get("suggested_name") or image.get("filename") or f"{image_id}.png"
        storage_path = f"docs/{doc_id}/images/{filename}"

        data: bytes = image["data"]
        self.client.storage.from_(self.bucket).upload(storage_path, data, {"upsert": "true"})

        public_url = self.client.storage.from_(self.bucket).get_public_url(storage_path)
        return StoredImage(image_id=image_id, storage_path=storage_path, public_url=public_url)

    def store_images(self, doc_id: str, images: List[Dict]) -> Dict[str, StoredImage]:
        stored: Dict[str, StoredImage] = {}
        for image in images:
            stored_image = self.store_image(doc_id, image)
            stored[stored_image.image_id] = stored_image
        return stored
