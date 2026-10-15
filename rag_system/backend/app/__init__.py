import os
import logging
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from backend.app.config import config_by_name, Config
from backend.app.extensions import db, migrate, jwt, cors, register_jwt_handlers


def create_app(config_name: str = None) -> Flask:
    """Application factory for the Flask backend."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development").lower()

    # Avoid OneDrive lockouts by configuring a local instance_path
    instance_dir = (
        Path.home() / "rag_storage" / "instance"
        if "OneDrive" in str(Config.WORKSPACE_ROOT)
        else Config.WORKSPACE_ROOT / "instance"
    )
    instance_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(
        __name__,
        instance_path=str(instance_dir),
        static_folder=str(Config.WORKSPACE_ROOT / "frontend"),
        static_url_path=""
    )

    # Load configuration
    cfg = config_by_name.get(config_name, config_by_name["development"])
    app.config.from_object(cfg)

    # Validate configuration
    cfg.validate()

    # Logging setup
    logging.basicConfig(
        level=logging.DEBUG if app.config.get("DEBUG") else logging.INFO,
        format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    register_jwt_handlers(jwt)

    # Register blueprints
    from backend.app.routes.health import health_bp
    from backend.app.routes.auth import auth_bp
    from backend.app.routes.documents import documents_bp
    from backend.app.routes.collections import collections_bp
    from backend.app.routes.chat import chat_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(collections_bp)
    app.register_blueprint(chat_bp)

    # Register error handlers
    register_error_handlers(app)

    # Initialize tables if not existing
    with app.app_context():
        try:
            from backend.app.models import User, Collection, Document, DocumentChunk, Conversation, Message
            db.create_all()
        except Exception as e:
            logging.warning(f"Database table initialization notice: {e}")

    # Serve Frontend Single Page or Static Views
    @app.route("/", methods=["GET"])
    def index():
        return send_from_directory(app.static_folder, "index.html")

    return app


def register_error_handlers(app: Flask):
    """Register standard uniform JSON error handlers across the application."""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "success": False,
            "error": {
                "code": "BAD_REQUEST",
                "message": getattr(e, "description", "Invalid request parameters.")
            }
        }), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": getattr(e, "description", "The requested resource was not found.")
            }
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            "success": False,
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": "The HTTP method is not allowed for this endpoint."
            }
        }), 405

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({
            "success": False,
            "error": {
                "code": "PAYLOAD_TOO_LARGE",
                "message": f"File size exceeds the maximum permitted limit ({app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB)."
            }
        }), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        logging.error(f"Internal server error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred."
            }
        }), 500
