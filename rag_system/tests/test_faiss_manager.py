import tempfile
from pathlib import Path
from backend.app.services.vector_store.faiss_manager import FAISSIndexManager
from backend.app.services.embeddings.provider import DeterministicMockEmbeddingProvider


def test_faiss_lifecycle_and_persistence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        mgr = FAISSIndexManager(tmp_dir)
        embedder = DeterministicMockEmbeddingProvider(dimension=64)

        chunks = [
            {"id": "c1", "document_id": "d1", "chunk_index": 0, "page_number": 1, "content": "Alpha text for testing FAISS."},
            {"id": "c2", "document_id": "d2", "chunk_index": 0, "page_number": 1, "content": "Beta text for testing FAISS search."}
        ]
        embs = embedder.embed_documents([c["content"] for c in chunks])
        mgr.add_vectors("u1", chunks, embs, embedding_dim=64)

        # Verify disk files exist
        paths = mgr._get_paths("u1")
        assert paths["index"].exists()
        assert paths["metadata"].exists()
        assert paths["manifest"].exists()

        # Simulate fresh application restart: instantiate new manager instance
        fresh_mgr = FAISSIndexManager(tmp_dir)
        index, meta, manifest = fresh_mgr.load_index("u1")
        assert index is not None
        assert index.ntotal == 2
        assert manifest["total_vectors"] == 2
        assert "c1" == meta["vectors"]["0"]["chunk_id"]

        # Exact query search
        q_vec = embedder.embed_query("Alpha text for testing FAISS.")
        hits = fresh_mgr.search("u1", q_vec, top_k=1, threshold=0.5)
        assert len(hits) == 1
        assert hits[0]["chunk_id"] == "c1"
        assert hits[0]["score"] > 0.99

        # Document deletion rebuild test
        remaining_chunks = [chunks[1]]  # Keep only d2
        fresh_mgr.rebuild_index("u1", remaining_chunks, embedder.embed_documents, embedding_dim=64)
        rebuilt_index, rebuilt_meta, rebuilt_manifest = fresh_mgr.load_index("u1")
        assert rebuilt_index.ntotal == 1
        assert rebuilt_manifest["total_vectors"] == 1
        assert rebuilt_meta["vectors"]["0"]["chunk_id"] == "c2"
