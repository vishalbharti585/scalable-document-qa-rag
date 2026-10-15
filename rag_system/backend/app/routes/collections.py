from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from backend.app.models.collection import Collection

collections_bp = Blueprint("collections", __name__, url_prefix="/api/v1/collections")


@collections_bp.route("", methods=["POST"])
@jwt_required()
def create_collection():
    """Create a new collection for organizing documents."""
    current_user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()

    if not name:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Collection name is required."
            }
        }), 400

    existing = Collection.query.filter_by(user_id=current_user_id, name=name).first()
    if existing:
        return jsonify({
            "success": False,
            "error": {
                "code": "DUPLICATE_COLLECTION",
                "message": f"A collection named '{name}' already exists."
            }
        }), 409

    col = Collection(user_id=current_user_id, name=name, description=description or None)
    db.session.add(col)
    db.session.commit()

    return jsonify({
        "success": True,
        "data": {
            "collection": col.to_dict()
        },
        "message": "Collection created successfully."
    }), 201


@collections_bp.route("", methods=["GET"])
@jwt_required()
def list_collections():
    """List all collections owned by the authenticated user."""
    current_user_id = get_jwt_identity()
    collections = Collection.query.filter_by(user_id=current_user_id).order_by(Collection.created_at.desc()).all()

    return jsonify({
        "success": True,
        "data": {
            "collections": [c.to_dict() for c in collections]
        },
        "message": "Collections retrieved successfully."
    }), 200


@collections_bp.route("/<string:collection_id>", methods=["PATCH"])
@jwt_required()
def update_collection(collection_id: str):
    """Rename or update description of a collection."""
    current_user_id = get_jwt_identity()
    col = Collection.query.filter_by(id=collection_id, user_id=current_user_id).first()
    if not col:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Collection not found."
            }
        }), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Collection name cannot be empty."
                }
            }), 400
        col.name = name

    if "description" in data:
        col.description = data["description"].strip()

    db.session.commit()
    return jsonify({
        "success": True,
        "data": {
            "collection": col.to_dict()
        },
        "message": "Collection updated successfully."
    }), 200


@collections_bp.route("/<string:collection_id>", methods=["DELETE"])
@jwt_required()
def delete_collection(collection_id: str):
    """Delete a collection safely (unassigns documents without losing them)."""
    current_user_id = get_jwt_identity()
    col = Collection.query.filter_by(id=collection_id, user_id=current_user_id).first()
    if not col:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "Collection not found."
            }
        }), 404

    db.session.delete(col)
    db.session.commit()

    return jsonify({
        "success": True,
        "data": None,
        "message": "Collection deleted successfully."
    }), 200
