from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.services.auth.auth_service import AuthService
from backend.app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    full_name = data.get("full_name")

    if not email or not password:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Email and password are required fields."
            }
        }), 400

    try:
        user = AuthService.register_user(email=email, password=password, full_name=full_name)
        token, _ = AuthService.authenticate_user(email=email, password=password)
        return jsonify({
            "success": True,
            "data": {
                "user": user.to_dict(),
                "access_token": token,
                "token_type": "Bearer"
            },
            "message": "User registered successfully."
        }), 201
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "REGISTRATION_FAILED",
                "message": str(e)
            }
        }), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate credentials and return JWT token."""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Email and password are required."
            }
        }), 400

    try:
        token, user = AuthService.authenticate_user(email=email, password=password)
        return jsonify({
            "success": True,
            "data": {
                "user": user.to_dict(),
                "access_token": token,
                "token_type": "Bearer"
            },
            "message": "Authentication successful."
        }), 200
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": str(e)
            }
        }), 401


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get profile of currently authenticated user."""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "USER_NOT_FOUND",
                "message": "Authenticated user profile could not be located."
            }
        }), 404

    return jsonify({
        "success": True,
        "data": {
            "user": user.to_dict()
        },
        "message": "User profile retrieved successfully."
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Stateless logout confirmation."""
    return jsonify({
        "success": True,
        "data": None,
        "message": "Successfully logged out. Client should discard stored token."
    }), 200
