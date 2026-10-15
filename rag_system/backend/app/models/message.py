import uuid
from datetime import datetime, timezone
from backend.app.extensions import db


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # role: 'user' | 'assistant' | 'system'
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    source_references = db.Column(db.JSON, nullable=True)
    retrieval_metadata = db.Column(db.JSON, nullable=True)
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    conversation = db.relationship("Conversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "source_references": self.source_references or [],
            "retrieval_metadata": self.retrieval_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
