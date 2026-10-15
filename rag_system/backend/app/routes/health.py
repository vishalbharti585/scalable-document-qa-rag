import time
from datetime import datetime, timezone
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from backend.app.extensions import db

health_bp = Blueprint("health", __name__, url_prefix="/api/v1")
START_TIME = time.time()


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Liveness probe: verifies the application process is running."""
    uptime_seconds = int(time.time() - START_TIME)
    return jsonify({
        "success": True,
        "data": {
            "status": "healthy",
            "uptime_seconds": uptime_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": current_app.config.get("FLASK_ENV", "unknown")
        },
        "message": "Service is healthy and active."
    }), 200


@health_bp.route("/ready", methods=["GET"])
def readiness_check():
    """Readiness probe: verifies database connectivity and storage directory access."""
    checks = {
        "database": False,
        "storage_uploads": False,
        "storage_faiss": False,
    }
    errors = []

    # Database connectivity check
    try:
        db.session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        errors.append(f"Database unavailable: {str(e)}")

    # Storage uploads writable
    try:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        test_file = upload_folder / ".write_test"
        test_file.touch()
        test_file.unlink()
        checks["storage_uploads"] = True
    except Exception as e:
        errors.append(f"Uploads storage not writable: {str(e)}")

    # Storage FAISS writable
    try:
        faiss_folder = current_app.config["FAISS_INDEX_DIR"]
        test_file = faiss_folder / ".write_test"
        test_file.touch()
        test_file.unlink()
        checks["storage_faiss"] = True
    except Exception as e:
        errors.append(f"FAISS storage not writable: {str(e)}")

    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503

    return jsonify({
        "success": all_ready,
        "data": {
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
            "errors": errors if errors else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "message": "Service readiness evaluated."
    }), status_code
