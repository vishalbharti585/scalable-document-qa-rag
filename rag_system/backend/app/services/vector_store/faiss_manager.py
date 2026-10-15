import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import faiss
import numpy as np
import portalocker


class FAISSIndexManager:
    """Manages isolated per-user FAISS vector indexes with atomic persistence,
    metadata mapping, manifests, and safe rebuild-based vector deletion.
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # In-memory index cache: {user_id: {"index": faiss.Index, "metadata": dict, "manifest": dict, "mtime": float}}
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _get_user_dir(self, user_id: str) -> Path:
        """Get or create the isolated physical directory for a user's index."""
        user_dir = self.base_dir / f"user_{user_id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _get_paths(self, user_id: str) -> Dict[str, Path]:
        """Paths for user's index artifacts."""
        user_dir = self._get_user_dir(user_id)
        return {
            "dir": user_dir,
            "index": user_dir / "index.faiss",
            "index_tmp": user_dir / "index.faiss.tmp",
            "metadata": user_dir / "metadata.json",
            "metadata_tmp": user_dir / "metadata.json.tmp",
            "manifest": user_dir / "manifest.json",
            "manifest_tmp": user_dir / "manifest.json.tmp",
            "lock": user_dir / "index.faiss.lock",
        }

    def load_index(self, user_id: str) -> Tuple[Optional[faiss.Index], Dict[str, Any], Dict[str, Any]]:
        """Load the user's FAISS index, metadata, and manifest. Returns (None, {}, {}) if not found."""
        paths = self._get_paths(user_id)
        if not paths["index"].exists() or not paths["metadata"].exists() or not paths["manifest"].exists():
            return None, {}, {}

        # Check in-memory cache against disk modification time
        current_mtime = paths["manifest"].stat().st_mtime
        if user_id in self._cache and self._cache[user_id]["mtime"] == current_mtime:
            cached = self._cache[user_id]
            return cached["index"], cached["metadata"], cached["manifest"]

        with portalocker.Lock(str(paths["lock"]), mode="r", timeout=10):
            # Native FAISS read_index avoids Python pickle vulnerabilities
            index = faiss.read_index(str(paths["index"]))
            with open(paths["metadata"], "r", encoding="utf-8") as f:
                metadata = json.load(f)
            with open(paths["manifest"], "r", encoding="utf-8") as f:
                manifest = json.load(f)

        self._cache[user_id] = {
            "index": index,
            "metadata": metadata,
            "manifest": manifest,
            "mtime": current_mtime
        }
        return index, metadata, manifest

    def add_vectors(
        self,
        user_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        embedding_dim: int
    ) -> int:
        """Add vectors and chunk metadata to the user's persistent FAISS index using atomic file replacement."""
        if not chunks or not embeddings:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks count must exactly match embeddings count.")

        paths = self._get_paths(user_id)
        vec_array = np.array(embeddings, dtype=np.float32)
        # Normalize vectors for cosine similarity via inner product
        faiss.normalize_L2(vec_array)

        with portalocker.Lock(str(paths["lock"]), mode="w", timeout=30):
            # Load existing or initialize new IndexFlatIP
            if paths["index"].exists() and paths["metadata"].exists() and paths["manifest"].exists():
                index = faiss.read_index(str(paths["index"]))
                with open(paths["metadata"], "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                with open(paths["manifest"], "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            else:
                # Flat Inner Product index on normalized vectors equals Cosine Similarity
                index = faiss.IndexFlatIP(embedding_dim)
                metadata = {"vectors": {}}
                manifest = {
                    "version": 1,
                    "dimension": embedding_dim,
                    "total_vectors": 0,
                    "document_ids": [],
                    "updated_at": time.time()
                }

            start_idx = index.ntotal
            index.add(vec_array)

            for i, chunk in enumerate(chunks):
                vec_id = str(start_idx + i)
                chunk_meta = chunk.get("metadata", {})
                metadata["vectors"][vec_id] = {
                    "chunk_id": chunk.get("id") or chunk_meta.get("chunk_id") or f"vec_{vec_id}",
                    "document_id": chunk.get("document_id") or chunk_meta.get("document_id"),
                    "collection_id": chunk.get("collection_id") or chunk_meta.get("collection_id"),
                    "user_id": user_id,
                    "chunk_index": chunk.get("chunk_index"),
                    "page_number": chunk.get("page_number"),
                    "content": chunk.get("content"),
                    "source_filename": chunk.get("source_filename") or chunk_meta.get("source_filename"),
                    "created_at": time.time()
                }

            # Update manifest
            all_doc_ids = set(manifest.get("document_ids", []))
            for c in chunks:
                doc_id = c.get("document_id") or c.get("metadata", {}).get("document_id")
                if doc_id:
                    all_doc_ids.add(doc_id)

            manifest["total_vectors"] = index.ntotal
            manifest["document_ids"] = list(all_doc_ids)
            manifest["updated_at"] = time.time()

            # Atomic save: write to .tmp and rename
            faiss.write_index(index, str(paths["index_tmp"]))
            with open(paths["metadata_tmp"], "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            with open(paths["manifest_tmp"], "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            os.replace(str(paths["index_tmp"]), str(paths["index"]))
            os.replace(str(paths["metadata_tmp"]), str(paths["metadata"]))
            os.replace(str(paths["manifest_tmp"]), str(paths["manifest"]))

            # Invalidate memory cache
            self._cache.pop(user_id, None)

        return index.ntotal

    def search(
        self,
        user_id: str,
        query_vector: List[float],
        query_text: str = "",
        top_k: int = 4,
        threshold: float = 0.15,
        document_filter_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Perform hybrid similarity search on user's FAISS index with lexical phrase re-ranking."""
        import re
        index, metadata, manifest = self.load_index(user_id)
        if index is None or index.ntotal == 0:
            return []

        # Strict document scope isolation: If filter is explicitly an empty list, 0 documents match
        if document_filter_ids is not None and len(document_filter_ids) == 0:
            return []

        # Prepare normalized query vector
        q_vec = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(q_vec)

        # Retrieve a wider pool of candidates for hybrid re-ranking and diversity selection
        fetch_k = min(index.ntotal, max(top_k * 10, 50))
        distances, indices = index.search(q_vec, fetch_k)

        # Prepare query keywords, technical terms, and clean phrase
        stop_words = {
            "what", "which", "how", "why", "who", "when", "where", "are", "the",
            "and", "for", "from", "with", "according", "document", "does", "can",
            "about", "some", "que", "give", "ans", "tell", "explain", "please"
        }
        clean_q = re.sub(r"[^\w\s]", " ", query_text.lower()).strip()
        q_words = set(w for w in clean_q.split() if len(w) >= 3 and w not in stop_words)

        raw_candidates = []
        vec_meta = metadata.get("vectors", {})

        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            raw_score = float(dist)
            item_meta = vec_meta.get(str(idx))
            if not item_meta:
                continue

            # Multi-tenant and document scoping
            if item_meta.get("user_id") != user_id:
                continue
            if document_filter_ids is not None and item_meta.get("document_id") not in document_filter_ids:
                continue

            content_lower = item_meta.get("content", "").lower()
            
            # Hybrid lexical boost: exact phrase + distinct keyword coverage
            boost = 0.0
            if clean_q and len(clean_q) > 4 and clean_q in content_lower:
                boost += 0.25  # Exact phrase match
            if q_words:
                matched_kw = sum(1 for w in q_words if w in content_lower)
                boost += 0.20 * (matched_kw / len(q_words))

            final_score = raw_score + boost

            if final_score < threshold:
                continue

            # Calibrate similarity score to clean [0.0, 1.0] range
            calibrated_score = round(max(0.0, min(1.0, final_score)), 4)

            raw_candidates.append({
                "chunk_id": item_meta.get("chunk_id"),
                "document_id": item_meta.get("document_id"),
                "source_filename": item_meta.get("source_filename"),
                "page_number": item_meta.get("page_number"),
                "chunk_index": item_meta.get("chunk_index"),
                "content": item_meta.get("content"),
                "score": calibrated_score,
                "raw_score": round(raw_score, 4),
                "lexical_boost": round(boost, 4),
            })

        # Sort candidates by boosted hybrid score
        raw_candidates.sort(key=lambda x: x["score"], reverse=True)

        # Maximal Marginal Relevance (MMR) / Diversity Deduplication
        # Prevent near-identical chunks from starving out diverse content
        selected_candidates = []
        for cand in raw_candidates:
            cand_tokens = set(cand["content"].lower().split())
            is_redundant = False
            for selected in selected_candidates:
                # If same document and adjacent chunk with very high token overlap, skip duplicate
                sel_tokens = set(selected["content"].lower().split())
                intersection = len(cand_tokens & sel_tokens)
                union = len(cand_tokens | sel_tokens)
                jaccard = (intersection / union) if union > 0 else 0.0
                if jaccard > 0.75:
                    is_redundant = True
                    break

            if not is_redundant or len(selected_candidates) < (top_k // 2):
                selected_candidates.append(cand)

            if len(selected_candidates) >= top_k:
                break

        return selected_candidates[:top_k]

    def rebuild_index(
        self,
        user_id: str,
        active_chunks: List[Dict[str, Any]],
        embedding_func: Any,
        embedding_dim: int
    ):
        """Rebuild user's FAISS index from remaining active database chunks (used upon document deletion)."""
        paths = self._get_paths(user_id)

        with portalocker.Lock(str(paths["lock"]), mode="w", timeout=60):
            if not active_chunks:
                # Clean up existing files if user has 0 chunks remaining
                for k in ["index", "metadata", "manifest"]:
                    if paths[k].exists():
                        paths[k].unlink()
                self._cache.pop(user_id, None)
                return 0

            texts = [c["content"] for c in active_chunks]
            embeddings = embedding_func(texts)

            index = faiss.IndexFlatIP(embedding_dim)
            vec_array = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(vec_array)
            index.add(vec_array)

            metadata = {"vectors": {}}
            doc_ids = set()
            for i, chunk in enumerate(active_chunks):
                vec_id = str(i)
                doc_id = chunk.get("document_id")
                if doc_id:
                    doc_ids.add(doc_id)
                metadata["vectors"][vec_id] = {
                    "chunk_id": chunk.get("id"),
                    "document_id": doc_id,
                    "user_id": user_id,
                    "chunk_index": chunk.get("chunk_index"),
                    "page_number": chunk.get("page_number"),
                    "content": chunk.get("content"),
                    "source_filename": chunk.get("source_filename"),
                    "created_at": time.time()
                }

            manifest = {
                "version": 1,
                "dimension": embedding_dim,
                "total_vectors": index.ntotal,
                "document_ids": list(doc_ids),
                "updated_at": time.time()
            }

            faiss.write_index(index, str(paths["index_tmp"]))
            with open(paths["metadata_tmp"], "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            with open(paths["manifest_tmp"], "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            os.replace(str(paths["index_tmp"]), str(paths["index"]))
            os.replace(str(paths["metadata_tmp"]), str(paths["metadata"]))
            os.replace(str(paths["manifest_tmp"]), str(paths["manifest"]))

            self._cache.pop(user_id, None)

        return index.ntotal
