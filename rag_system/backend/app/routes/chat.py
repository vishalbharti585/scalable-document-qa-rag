from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
from backend.app.models.document import Document
from backend.app.services.retrieval.rag_service import RAGService

chat_bp = Blueprint("chat", __name__, url_prefix="/api/v1/conversations")


@chat_bp.route("", methods=["POST"])
@jwt_required()
def create_conversation():
    """Create a new chat conversation session."""
    current_user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "New Conversation").strip()

    conv = Conversation(user_id=current_user_id, title=title)
    db.session.add(conv)
    db.session.commit()

    return jsonify({
        "success": True,
        "data": {
            "conversation": conv.to_dict()
        },
        "message": "Conversation session created."
    }), 201


@chat_bp.route("", methods=["GET"])
@jwt_required()
def list_conversations():
    """List all conversations for the authenticated user."""
    current_user_id = get_jwt_identity()
    conversations = (
        Conversation.query.filter_by(user_id=current_user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    return jsonify({
        "success": True,
        "data": {
            "conversations": [c.to_dict() for c in conversations]
        },
        "message": "Conversations retrieved successfully."
    }), 200


@chat_bp.route("/<string:conversation_id>", methods=["GET"])
@jwt_required()
def get_conversation(conversation_id: str):
    """Get conversation details with complete historical messages and citations."""
    current_user_id = get_jwt_identity()
    conv = Conversation.query.filter_by(id=conversation_id, user_id=current_user_id).first()
    if not conv:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Conversation not found."
            }
        }), 404

    messages = [m.to_dict() for m in conv.messages]
    return jsonify({
        "success": True,
        "data": {
            "conversation": conv.to_dict(),
            "messages": messages
        },
        "message": "Conversation history retrieved."
    }), 200


@chat_bp.route("/<string:conversation_id>", methods=["DELETE"])
@jwt_required()
def delete_conversation(conversation_id: str):
    """Delete a conversation and its messages."""
    current_user_id = get_jwt_identity()
    conv = Conversation.query.filter_by(id=conversation_id, user_id=current_user_id).first()
    if not conv:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Conversation not found."
            }
        }), 404

    db.session.delete(conv)
    db.session.commit()

    return jsonify({
        "success": True,
        "data": None,
        "message": "Conversation deleted successfully."
    }), 200


@chat_bp.route("/<string:conversation_id>/messages", methods=["POST"])
@jwt_required()
def send_message(conversation_id: str):
    """Post a user query, run grounded RAG generation, persist messages, and return answer with citations."""
    current_user_id = get_jwt_identity()
    conv = Conversation.query.filter_by(id=conversation_id, user_id=current_user_id).first()
    if not conv:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Conversation not found."
            }
        }), 404

    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Message content cannot be empty."
            }
        }), 400

    collection_id = data.get("collection_id")
    document_ids = data.get("document_ids")

    # If collection_id provided, resolve document IDs in that collection
    if collection_id and not document_ids:
        docs = Document.query.filter_by(user_id=current_user_id, collection_id=collection_id).all()
        document_ids = [d.id for d in docs]

    # Save user message turn
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=question
    )
    db.session.add(user_msg)

    # Automatically set conversation title from first question if default
    if conv.title == "New Conversation":
        conv.title = question[:45] + ("..." if len(question) > 45 else "")

    # Execute Grounded RAG Query
    try:
        top_k = data.get("top_k")
        if top_k is not None:
            try:
                top_k = int(top_k)
            except (ValueError, TypeError):
                top_k = None

        rag_svc = RAGService(current_app.config)
        rag_result = rag_svc.query(
            user_id=current_user_id,
            question=question,
            document_filter_ids=document_ids,
            top_k=top_k
        )
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "GENERATION_ERROR",
                "message": f"LLM Generation Error: {str(e)}"
            }
        }), 500

    # Save assistant response turn with citations and metrics
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=rag_result["answer"],
        source_references=rag_result["citations"],
        retrieval_metadata=rag_result["metrics"]
    )
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({
        "success": True,
        "data": {
            "answer": rag_result["answer"],
            "citations": rag_result["citations"],
            "metrics": rag_result["metrics"],
            "user_message": user_msg.to_dict(),
            "assistant_message": assistant_msg.to_dict()
        },
        "message": "Message processed and answered."
    }), 200
