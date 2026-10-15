import os
import uuid
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from werkzeug.datastructures import FileStorage
from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.collection import Collection
from backend.app.services.ingestion.validator import DocumentValidator
from backend.app.services.ingestion.extractor import TextExtractor
from backend.app.services.chunking.splitter import TextSplitter
from backend.app.services.embeddings.provider import get_embedding_provider
from backend.app.services.vector_store.faiss_manager import FAISSIndexManager


class DocumentService:
    """End-to-end document management service coordinating upload, extraction,
    chunking, embedding generation, FAISS indexing, and safe deletion.
    """

    def __init__(self, config: Any):
        def _cfg(key, default=None):
            if hasattr(config, "get"):
                val = config.get(key)
                if val is not None:
                    return val
            return getattr(config, key, default)

        self.config = config
        self.upload_dir = Path(_cfg("UPLOAD_FOLDER"))
        self.faiss_manager = FAISSIndexManager(_cfg("FAISS_INDEX_DIR"))
        self.embedding_provider = get_embedding_provider(
            _cfg("EMBEDDING_PROVIDER"),
            api_key=_cfg("EMBEDDING_API_KEY", ""),
            model_name=_cfg("EMBEDDING_MODEL", "")
        )
        self.text_splitter = TextSplitter(
            chunk_size=_cfg("CHUNK_SIZE", 1000),
            chunk_overlap=_cfg("CHUNK_OVERLAP", 200)
        )

    def _get_user_upload_dir(self, user_id: str) -> Path:
        """Create and return user-specific upload directory."""
        user_dir = self.upload_dir / f"user_{user_id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def upload_and_process(
        self,
        user_id: str,
        file: FileStorage,
        collection_id: Optional[str] = None
    ) -> Document:
        """Validate, store, extract, chunk, embed, and index a document."""
        # 1. Validate file
        max_len = self.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024) if hasattr(self.config, "get") else getattr(self.config, "MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
        validated = DocumentValidator.validate_file(file, max_len)
        
        # Check if collection belongs to user
        if collection_id:
            collection = Collection.query.filter_by(id=collection_id, user_id=user_id).first()
            if not collection:
                raise ValueError("Specified collection not found or does not belong to you.")

        # Check for duplicate document
        existing = Document.query.filter_by(user_id=user_id, content_hash=validated["content_hash"]).first()
        if existing and existing.processing_status == "processed":
            return existing

        # 2. Save physical file securely with UUID filename
        storage_uuid = str(uuid.uuid4())
        storage_filename = f"{storage_uuid}{validated['extension']}"
        user_upload_dir = self._get_user_upload_dir(user_id)
        saved_path = user_upload_dir / storage_filename

        with open(saved_path, "wb") as f:
            f.write(validated["raw_bytes"])

        # 3. Create document record in PostgreSQL
        document = Document(
            user_id=user_id,
            collection_id=collection_id,
            original_filename=validated["original_filename"],
            storage_filename=storage_filename,
            mime_type=validated["mime_type"],
            file_size=validated["file_size"],
            content_hash=validated["content_hash"],
            processing_status="processing"
        )
        db.session.add(document)
        db.session.commit()

        # 4. Extract text
        try:
            pages = TextExtractor.extract_from_file(saved_path, validated["extension"])
            document.page_count = len(pages)

            # 5. Split into chunks
            raw_chunks = self.text_splitter.split_pages(
                pages=pages,
                document_id=document.id,
                user_id=user_id,
                source_filename=document.original_filename,
                collection_id=document.collection_id
            )

            if not raw_chunks:
                raise ValueError("Document yielded no searchable text chunks.")

            # 6. Bulk insert chunks into PostgreSQL
            db_chunks = []
            chunk_dicts = []
            for c in raw_chunks:
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    user_id=user_id,
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    page_number=c["page_number"],
                    start_char_idx=c["start_char_idx"],
                    end_char_idx=c["end_char_idx"],
                    metadata_json=c["metadata"]
                )
                db_chunks.append(db_chunk)
                chunk_dicts.append({
                    "id": db_chunk.id,
                    "document_id": document.id,
                    "chunk_index": c["chunk_index"],
                    "page_number": c["page_number"],
                    "content": c["content"],
                    "source_filename": document.original_filename,
                    "metadata": c["metadata"]
                })

            db.session.bulk_save_objects(db_chunks)
            db.session.commit()

            # 7. Generate embeddings
            texts_to_embed = [c["content"] for c in chunk_dicts]
            embeddings = self.embedding_provider.embed_documents(texts_to_embed)

            # 8. Add to user's FAISS index
            self.faiss_manager.add_vectors(
                user_id=user_id,
                chunks=chunk_dicts,
                embeddings=embeddings,
                embedding_dim=self.embedding_provider.dimension
            )

            # 9. Update document status to processed
            document.processing_status = "processed"
            document.processing_error = None
            db.session.commit()

            return document

        except Exception as e:
            db.session.rollback()
            document.processing_status = "failed"
            document.processing_error = str(e)
            db.session.commit()
            raise RuntimeError(f"Document ingestion failed: {str(e)}")

    def delete_document(self, user_id: str, document_id: str) -> bool:
        """Safely delete document, database chunks, physical file, and rebuild user's FAISS index."""
        document = Document.query.filter_by(id=document_id, user_id=user_id).first()
        if not document:
            return False

        # Remove physical file
        user_upload_dir = self._get_user_upload_dir(user_id)
        physical_path = user_upload_dir / document.storage_filename
        if physical_path.exists():
            try:
                physical_path.unlink()
            except Exception:
                pass

        # Delete from PostgreSQL (cascades to document_chunks)
        db.session.delete(document)
        db.session.commit()

        # Rebuild user FAISS index with remaining active chunks
        remaining_chunks = DocumentChunk.query.filter_by(user_id=user_id).order_by(DocumentChunk.created_at).all()
        active_chunk_dicts = [
            {
                "id": c.id,
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "content": c.content,
                "source_filename": c.document.original_filename if c.document else "unknown"
            }
            for c in remaining_chunks
        ]

        self.faiss_manager.rebuild_index(
            user_id=user_id,
            active_chunks=active_chunk_dicts,
            embedding_func=self.embedding_provider.embed_documents,
            embedding_dim=self.embedding_provider.dimension
        )

        return True
