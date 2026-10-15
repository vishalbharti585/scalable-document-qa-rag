import uuid
from datetime import datetime, timezone
from backend.app.extensions import db


class Document(db.Model):
    __tablename__ = "documents"
    __table_args__ = (
        db.Index("idx_documents_user_hash", "user_id", "content_hash"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = db.Column(db.String(36), db.ForeignKey("collections.id", ondelete="SET NULL"), nullable=True, index=True)
    
    original_filename = db.Column(db.String(255), nullable=False)
    storage_filename = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    page_count = db.Column(db.Integer, nullable=True)
    
    # Status: 'uploaded' | 'processing' | 'processed' | 'failed'
    processing_status = db.Column(db.String(20), default="uploaded", nullable=False)
    processing_error = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = db.relationship("User", back_populates="documents")
    collection = db.relationship("Collection", back_populates="documents")
    chunks = db.relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "collection_id": self.collection_id,
            "collection_name": self.collection.name if self.collection else None,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "chunk_count": len(self.chunks) if self.chunks else 0,
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
