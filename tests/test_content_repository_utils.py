"""
Basic safety checks for our local content storage code.

We make sure filenames are cleaned up, defaults kick in when needed, and
section/image data actually lands on disk with the paths we expect.
"""

import json
import os

os.environ.setdefault("SESSION_SECRET", "test-secret")

from app.services.content_repository import ContentRepository, _finalize_filename


def test_finalize_filename_uses_requested_name_when_valid():
    filename = _finalize_filename(" custom/path/name.json ", "fallback.json", required_suffix=".json")
    assert filename == "name.json"


def test_finalize_filename_applies_suffix_and_fallback():
    filename = _finalize_filename(None, "default", required_suffix=".png")
    assert filename == "default.png"


def test_finalize_filename_preserves_existing_suffix_case_insensitive():
    filename = _finalize_filename("IMAGE.PNG", "fallback", required_suffix=".png")
    assert filename == "IMAGE.PNG"


def test_finalize_filename_strips_path_components_before_use():
    filename = _finalize_filename("nested/dir/custom-name", "fallback.json", required_suffix=".json")
    assert filename == "custom-name.json"


def test_finalize_filename_uses_fallback_when_no_candidate_provided():
    filename = _finalize_filename("   ", "fallback.txt", required_suffix=".txt")
    assert filename == "fallback.txt"


def test_store_section_persists_json_and_respects_suggested_name(tmp_path):
    repo = ContentRepository(root=tmp_path)
    section = {"section_id": "sec-42", "suggested_name": "summary", "payload": {"title": "Doc"}}

    stored = repo.store_section("doc-123", section)

    assert stored.storage_path == "docs/doc-123/sections/summary.json"
    section_path = tmp_path / "doc-123" / "sections" / "summary.json"
    assert section_path.exists()
    with section_path.open("r", encoding="utf-8") as handle:
        assert json.load(handle)["payload"]["title"] == "Doc"


def test_store_image_writes_binary_and_enforces_extension(tmp_path):
    repo = ContentRepository(root=tmp_path)
    image = {
        "image_id": "img-1",
        "suggested_name": "diagram",
        "extension": ".png",
        "data": b"\x89PNG\r\n",
    }

    stored = repo.store_image("doc-456", image)

    assert stored.storage_path == "docs/doc-456/images/diagram.png"
    image_path = tmp_path / "doc-456" / "images" / "diagram.png"
    assert image_path.exists()
    assert image_path.read_bytes() == b"\x89PNG\r\n"


def test_store_images_returns_id_indexed_mapping(tmp_path):
    repo = ContentRepository(root=tmp_path)
    images = [
        {"image_id": "img-a", "extension": ".jpg", "data": b"a"},
        {"image_id": "img-b", "extension": ".jpg", "data": b"b"},
    ]

    stored = repo.store_images("doc-789", images)

    assert set(stored.keys()) == {"img-a", "img-b"}
    assert stored["img-a"].storage_path.endswith("img-a.jpg")
    assert (tmp_path / "doc-789" / "images" / "img-b.jpg").read_bytes() == b"b"
