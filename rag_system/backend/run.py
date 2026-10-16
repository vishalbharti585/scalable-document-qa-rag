
import os
import sys
from pathlib import Path

# Repository root: .../scalable-document-qa-rag

ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent

for directory in (str(ROOT_DIR), str(PROJECT_DIR), str(BACKEND_DIR)):
    if directory not in sys.path:
        sys.path.insert(0, directory)


from app import create_app

app = create_app(os.getenv("FLASK_ENV", "production"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=app.config.get("DEBUG", False),
    )
