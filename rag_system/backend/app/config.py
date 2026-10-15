import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from workspace root or backend directory
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(WORKSPACE_ROOT / ".env")


class Config:
    """Base application configuration with validation."""

    WORKSPACE_ROOT = WORKSPACE_ROOT
    FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
    DEBUG = False
    TESTING = False

    # Security Keys
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-flask-secret-key-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-insecure-jwt-secret-key-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "120"))
    )

    # Database
    # Support postgresql:// and fallback or testing with sqlite:///
    _default_db_path = (
        (Path.home() / "rag_storage" / "rag_local.db").as_posix()
        if "OneDrive" in str(WORKSPACE_ROOT)
        else (WORKSPACE_ROOT / "rag_local.db").as_posix()
    )
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")
    # Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # Storage paths (resilient to cloud sync / OneDrive locks)
    _default_storage_base = (
        Path.home() / "rag_storage" if "OneDrive" in str(WORKSPACE_ROOT) else WORKSPACE_ROOT / "storage"
    )
    _upload_env = os.getenv("UPLOAD_FOLDER", "")
    UPLOAD_FOLDER = Path(_upload_env) if _upload_env and Path(_upload_env).is_absolute() else (_default_storage_base / "uploads" if not _upload_env else WORKSPACE_ROOT / _upload_env)

    _faiss_env = os.getenv("FAISS_INDEX_DIR", "")
    FAISS_INDEX_DIR = Path(_faiss_env) if _faiss_env and Path(_faiss_env).is_absolute() else (_default_storage_base / "faiss_indexes" if not _faiss_env else WORKSPACE_ROOT / _faiss_env)

    _manifest_env = os.getenv("MANIFEST_DIR", "")
    MANIFEST_DIR = Path(_manifest_env) if _manifest_env and Path(_manifest_env).is_absolute() else (_default_storage_base / "manifests" if not _manifest_env else WORKSPACE_ROOT / _manifest_env)

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(16 * 1024 * 1024)))  # 16 MB

    # AI / Model Providers
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.8-flash")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "mock").lower()
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")

    # Chunking & Retrieval Parameters
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K = int(os.getenv("TOP_K", "4"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.15"))

    @classmethod
    def validate(cls):
        """Validate critical configuration settings at startup."""
        errors = []
        if cls.CHUNK_OVERLAP >= cls.CHUNK_SIZE:
            errors.append(f"CHUNK_OVERLAP ({cls.CHUNK_OVERLAP}) must be less than CHUNK_SIZE ({cls.CHUNK_SIZE})")

        if cls.FLASK_ENV == "production":
            if cls.SECRET_KEY.startswith("dev-insecure"):
                errors.append("Production requires a strong, unique SECRET_KEY")
            if cls.JWT_SECRET_KEY.startswith("dev-insecure"):
                errors.append("Production requires a strong, unique JWT_SECRET_KEY")
            if cls.DATABASE_URL.startswith("sqlite"):
                errors.append("Production requires a PostgreSQL database, not SQLite")
            if cls.LLM_PROVIDER in ("gemini", "openai") and not cls.LLM_API_KEY:
                errors.append(f"Production LLM_PROVIDER '{cls.LLM_PROVIDER}' requires LLM_API_KEY")
            if cls.EMBEDDING_PROVIDER in ("gemini", "openai") and not cls.EMBEDDING_API_KEY:
                errors.append(f"Production EMBEDDING_PROVIDER '{cls.EMBEDDING_PROVIDER}' requires EMBEDDING_API_KEY")

        # Ensure directories exist
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        cls.FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
        cls.MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

        if errors:
            raise ValueError(f"Configuration Validation Failed:\n- " + "\n- ".join(errors))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATABASE_URL = "sqlite:///:memory:"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LLM_PROVIDER = "mock"
    EMBEDDING_PROVIDER = "mock"
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
