from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.models.document import Document
from backend.app.services.documents.document_service import DocumentService

documents_bp = Blueprint("documents", __name__, url_prefix="/api/v1/documents")


@documents_bp.route("", methods=["POST"])
@jwt_required()
def upload_document():
    """Upload and process a document file (PDF, TXT, DOCX)."""
    current_user_id = get_jwt_identity()
    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_FILE",
                "message": "Multipart form must include 'file' field."
            }
        }), 400

    file = request.files["file"]
    collection_id = request.form.get("collection_id") or None

    svc = DocumentService(current_app.config)
    try:
        doc = svc.upload_and_process(
            user_id=current_user_id,
            file=file,
            collection_id=collection_id
        )
        return jsonify({
            "success": True,
            "data": {
                "document": doc.to_dict()
            },
            "message": "Document uploaded and indexed successfully."
        }), 201
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }), 400
    except RuntimeError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "PROCESSING_FAILED",
                "message": str(e)
            }
        }), 422


@documents_bp.route("", methods=["GET"])
@jwt_required()
def list_documents():
    """List documents owned by the authenticated user with optional collection filtering and pagination."""
    current_user_id = get_jwt_identity()
    collection_id = request.args.get("collection_id")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = Document.query.filter_by(user_id=current_user_id)
    if collection_id:
        query = query.filter_by(collection_id=collection_id)

    paginated = query.order_by(Document.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "success": True,
        "data": {
            "documents": [d.to_dict() for d in paginated.items],
            "pagination": {
                "total": paginated.total,
                "page": paginated.page,
                "pages": paginated.pages,
                "per_page": paginated.per_page,
            }
        },
        "message": "Documents retrieved successfully."
    }), 200


@documents_bp.route("/<string:document_id>", methods=["GET"])
@jwt_required()
def get_document(document_id: str):
    """Retrieve details for a single document owned by the user."""
    current_user_id = get_jwt_identity()
    doc = Document.query.filter_by(id=document_id, user_id=current_user_id).first()
    if not doc:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Document not found."
            }
        }), 404

    return jsonify({
        "success": True,
        "data": {
            "document": doc.to_dict()
        },
        "message": "Document retrieved successfully."
    }), 200


@documents_bp.route("/<string:document_id>", methods=["DELETE"])
@jwt_required()
def delete_document(document_id: str):
    """Delete a document and rebuild user's FAISS index."""
    current_user_id = get_jwt_identity()
    svc = DocumentService(current_app.config)
    deleted = svc.delete_document(user_id=current_user_id, document_id=document_id)

    if not deleted:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Document not found or does not belong to you."
            }
        }), 404

    return jsonify({
        "success": True,
        "data": None,
        "message": "Document, database chunks, and vector indexes deleted successfully."
    }), 200


@documents_bp.route("/<string:document_id>/reprocess", methods=["POST"])
@jwt_required()
def reprocess_document(document_id: str):
    """Reprocess a failed or updated document."""
    current_user_id = get_jwt_identity()
    doc = Document.query.filter_by(id=document_id, user_id=current_user_id).first()
    if not doc:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Document not found."
            }
        }), 404

    # Load stored file and re-ingest
    user_upload_dir = current_app.config["UPLOAD_FOLDER"] / f"user_{current_user_id}"
    file_path = user_upload_dir / doc.storage_filename
    if not file_path.exists():
        return jsonify({
            "success": False,
            "error": {
                "code": "FILE_NOT_FOUND",
                "message": "Physical file is missing from storage."
            }
        }), 404

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    from io import BytesIO
    mock_file = FileStorage(
        stream=BytesIO(file_bytes),
        filename=doc.original_filename,
        content_type=doc.mime_type
    )

    svc = DocumentService(current_app.config)
    # Remove old record chunks and index vectors
    svc.delete_document(current_user_id, document_id)
    new_doc = svc.upload_and_process(current_user_id, mock_file, doc.collection_id)

    return jsonify({
        "success": True,
        "data": {
            "document": new_doc.to_dict()
        },
        "message": "Document reprocessed successfully."
    }), 200
