#!/bin/sh
set -e

echo "Starting Scalable Document QA System (RAG)..."

# Ensure storage directories exist
mkdir -p /app/storage/uploads /app/storage/faiss_indexes /app/storage/manifests

# Apply database migrations if migrations directory exists
if [ -d "/app/migrations" ]; then
    echo "Applying PostgreSQL database migrations..."
    flask db upgrade || echo "Migration upgrade bypassed; tables initialized via SQLAlchemy."
fi

# Execute main process (Gunicorn)
exec "$@"
