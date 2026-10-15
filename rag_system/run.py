import os
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app import create_app

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print("\n" + "=" * 60)
    print("   SCALABLE DOCUMENT QUESTION ANSWERING SYSTEM (RAG)")
    print(f"   Server active at: http://localhost:{port}")
    print("   Open your browser to start uploading & asking questions!")
    print("   Press CTRL+C to stop.")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
