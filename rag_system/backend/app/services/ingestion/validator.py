import os
import hashlib
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAGIC_PDF = b"%PDF-"
MAGIC_ZIP_DOCX = b"PK\x03\x04"


class DocumentValidator:
    """Validates file extensions, size, content headers, and computes content hash."""

    @staticmethod
    def validate_file(file: FileStorage, max_length: int) -> dict:
        """Validate uploaded file stream and compute content metadata.
        
        Returns:
            dict containing original_filename, extension, mime_type, file_size, content_hash
        """
        if not file or not file.filename:
            raise ValueError("No file was provided.")

        original_filename = secure_filename(file.filename)
        if not original_filename:
            raise ValueError("Filename is invalid or contains forbidden characters.")

        ext = Path(original_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

        # Read content to compute hash and verify magic headers
        content = file.read()
        file.seek(0)  # Reset pointer for subsequent storage writing
        file_size = len(content)

        if file_size == 0:
            raise ValueError("The uploaded file is empty (0 bytes).")

        if file_size > max_length:
            max_mb = max_length // (1024 * 1024)
            raise ValueError(f"File size ({file_size / (1024*1024):.2f}MB) exceeds limit of {max_mb}MB.")

        # Magic number inspection
        mime_type = "application/octet-stream"
        if ext == ".pdf":
            if not content.startswith(MAGIC_PDF):
                raise ValueError("File corrupted: Invalid PDF header signature.")
            mime_type = "application/pdf"
        elif ext == ".docx":
            if not content.startswith(MAGIC_ZIP_DOCX):
                raise ValueError("File corrupted: Invalid DOCX header signature.")
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == ".txt":
            try:
                content.decode("utf-8")
                mime_type = "text/plain"
            except UnicodeDecodeError:
                try:
                    content.decode("latin-1")
                    mime_type = "text/plain; charset=latin-1"
                except Exception:
                    raise ValueError("Text file contains unreadable binary data or invalid encoding.")

        content_hash = hashlib.sha256(content).hexdigest()

        return {
            "original_filename": original_filename,
            "extension": ext,
            "mime_type": mime_type,
            "file_size": file_size,
            "content_hash": content_hash,
            "raw_bytes": content
        }
