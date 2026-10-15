import pytest
from backend.app.services.chunking.splitter import TextSplitter


def test_chunking_invalid_overlap():
    with pytest.raises(ValueError, match="must be strictly less than"):
        TextSplitter(chunk_size=500, chunk_overlap=500)


def test_chunking_metadata_preservation():
    splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
    pages = [
        {"page_number": 1, "text": "Sentence A is here. Sentence B is right here. Sentence C follows closely."},
        {"page_number": 2, "text": "Page 2 has separate information that should be segmented into new chunks."}
    ]

    chunks = splitter.split_pages(
        pages=pages,
        document_id="doc-123",
        user_id="user-456",
        source_filename="test_doc.txt"
    )

    assert len(chunks) >= 2
    for i, c in enumerate(chunks):
        assert c["chunk_index"] == i
        assert c["content"]
        assert c["page_number"] in (1, 2)
        assert c["start_char_idx"] >= 0
        assert c["end_char_idx"] > c["start_char_idx"]
        assert c["metadata"]["document_id"] == "doc-123"
        assert c["metadata"]["user_id"] == "user-456"
        assert c["metadata"]["source_filename"] == "test_doc.txt"
