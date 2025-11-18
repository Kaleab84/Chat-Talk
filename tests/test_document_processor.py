"""
Quick spot checks for DocumentProcessor helper methods.

We verify tables turn into readable text and chunking keeps sections,
text, images, and max-length limits in line.
"""

import os

os.environ.setdefault("SESSION_SECRET", "test-secret")

from app.services.document_processor import DocumentProcessor


def test_table_to_text_renders_rows_with_separators():
    rows = [["Header 1", "Header 2"], ["Value A", "Value B"]]
    processor = DocumentProcessor()

    rendered = processor._table_to_text(rows)

    expected = "Header 1 | Header 2\nValue A | Value B"
    assert rendered == expected


def test_table_to_text_returns_empty_string_for_no_rows():
    processor = DocumentProcessor()
    assert processor._table_to_text([]) == ""


def test_build_chunks_aggregates_text_and_images():
    sections = [
        {
            "section_id": "sec-1",
            "blocks": [
                {"type": "text", "text": "First block of text."},
                {"type": "image", "path": "images/img-1.png"},
                {"type": "text", "text": "Second block adds more detail."},
            ],
        }
    ]

    processor = DocumentProcessor()
    chunks = processor._build_chunks(sections, max_chars=200)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["section_id"] == "sec-1"
    assert "First block of text." in chunk["text"]
    assert "Second block adds more detail." in chunk["text"]
    assert chunk["image_paths"] == ["images/img-1.png"]


def test_build_chunks_respects_max_chars_and_creates_multiple_chunks():
    sections = [
        {
            "section_id": "sec-2",
            "blocks": [
                {"type": "text", "text": "A" * 90},
                {"type": "text", "text": "B" * 90},
                {"type": "text", "text": "C" * 90},
            ],
        }
    ]
    processor = DocumentProcessor()

    chunks = processor._build_chunks(sections, max_chars=120)

    assert len(chunks) == 3
    assert all(chunk["section_id"] == "sec-2" for chunk in chunks)
    assert chunks[0]["text"].startswith("A")
    assert chunks[1]["text"].startswith("B")
    assert chunks[2]["text"].startswith("C")


def test_build_chunks_creates_table_only_chunk_when_table_is_large():
    sections = [
        {
            "section_id": "sec-3",
            "blocks": [
                {"type": "text", "text": "Intro paragraph."},
                {"type": "table", "rows": [["Col1", "Col2"]] + [["x" * 200, "y" * 200]]},
            ],
        }
    ]
    processor = DocumentProcessor()

    chunks = processor._build_chunks(sections, max_chars=150)

    assert len(chunks) == 2
    assert "Intro paragraph." in chunks[0]["text"]
    assert "Col1" in chunks[1]["text"]
    assert chunks[1]["image_paths"] == []
