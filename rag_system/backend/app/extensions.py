from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()


def register_jwt_handlers(jwt_mgr: JWTManager):
    """Register uniform JSON responses for authentication failures."""

    @jwt_mgr.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Authorization header missing or invalid token provided."
            }
        }), 401

    @jwt_mgr.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "error": {
                "code": "TOKEN_EXPIRED",
                "message": "The access token has expired. Please log in again."
            }
        }), 401

    @jwt_mgr.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_TOKEN",
                "message": "The access token signature or format is invalid."
            }
        }), 401
