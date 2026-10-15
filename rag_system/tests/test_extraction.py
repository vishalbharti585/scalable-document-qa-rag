import tempfile
from pathlib import Path
import pytest
from backend.app.services.ingestion.extractor import TextExtractor


def test_txt_extraction_and_cleaning():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Line 1 with \t extra   spaces.\n\n\n\nLine 2 after gaps.")
        temp_path = f.name

    try:
        pages = TextExtractor.extract_from_file(temp_path, ".txt")
        assert len(pages) == 1
        assert pages[0]["page_number"] == 1
        assert "Line 1 with extra spaces." in pages[0]["text"]
        assert "\n\nLine 2 after gaps." in pages[0]["text"]
        assert "\n\n\n\n" not in pages[0]["text"]
    finally:
        Path(temp_path).unlink()


def test_empty_file_extraction_error():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="empty"):
            TextExtractor.extract_from_file(temp_path, ".txt")
    finally:
        Path(temp_path).unlink()


def test_missing_file_raises_not_found():
    with pytest.raises(FileNotFoundError):
        TextExtractor.extract_from_file("non_existent_file_path.pdf", ".pdf")
