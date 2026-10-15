import io
import re
from pathlib import Path
from pypdf import PdfReader
import docx2txt


class TextExtractor:
    """Extracts, normalizes, and segments text from PDF, DOCX, and TXT files."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize whitespace and remove unprintable control characters while preserving paragraph breaks."""
        if not text:
            return ""
        # Remove null bytes and non-printable control characters (keeping \n, \r, \t)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        text = text.replace("\u00a0", " ")
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Check if text has fragmented single-word per line formatting (common in PDF table/exam exports)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        avg_words_per_line = sum(len(line.split()) for line in lines) / max(1, len(lines))
        if avg_words_per_line < 2.5 and len(lines) > 5:
            # 3 or more breaks represent a section break
            text = re.sub(r"(\n\s*){3,}", "\n\n", text)
            # 1 or 2 breaks represent words wrapped onto individual lines
            text = re.sub(r"(\n\s*){1,2}", " ", text)
        else:
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text)

        return re.sub(r" +", " ", text).strip()

    @classmethod
    def filter_running_headers_and_footers(cls, pages: list[dict]) -> list[dict]:
        """Detect and strip recurring running headers and footers across multi-page documents.

        Preserves genuine content while stripping identical repeating artifacts (e.g. course codes,
        running page headers/footers) that repeat across >= 40% of the pages (minimum 3 pages).
        """
        if len(pages) < 3:
            return pages

        top_candidates = []
        bottom_candidates = []
        for p in pages:
            lines = [l.strip() for l in p["text"].split("\n") if l.strip()]
            if lines:
                top_candidates.append(lines[0])
            if len(lines) > 1:
                bottom_candidates.append(lines[-1])

        from collections import Counter
        threshold = max(3, int(len(pages) * 0.4))

        top_counts = Counter(top_candidates)
        bottom_counts = Counter(bottom_candidates)

        repeating_headers = {line for line, cnt in top_counts.items() if cnt >= threshold and len(line) > 3}
        repeating_footers = {line for line, cnt in bottom_counts.items() if cnt >= threshold and len(line) > 3}
        page_num_pattern = re.compile(r"^(?:page\s+\d+(?:\s+of\s+\d+)?|\d+(?:\s+/\s+\d+)?|\d+)$", re.IGNORECASE)

        cleaned_pages = []
        for p in pages:
            lines = [l.strip() for l in p["text"].split("\n") if l.strip()]
            if not lines:
                continue

            # Strip repeating header or page number at top
            if lines and (lines[0] in repeating_headers or page_num_pattern.match(lines[0])):
                lines.pop(0)

            # Strip repeating footer or page number at bottom
            if lines and (lines[-1] in repeating_footers or page_num_pattern.match(lines[-1])):
                lines.pop(-1)

            if lines:
                cleaned_pages.append({
                    "page_number": p["page_number"],
                    "text": "\n".join(lines)
                })
            else:
                cleaned_pages.append(p)

        return cleaned_pages

    @classmethod
    def extract_from_file(cls, file_path: str | Path, extension: str) -> list[dict]:
        """Extract text with page-level metadata.
        
        Returns:
            list of dicts: [{"page_number": int, "text": str}]
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found on storage: {path}")

        ext = extension.lower()
        pages = []

        if ext == ".pdf":
            try:
                reader = PdfReader(str(path))
                total_page_count = len(reader.pages)
                if total_page_count == 0:
                    raise ValueError("PDF contains no pages.")

                total_extracted_words = 0
                for idx, page in enumerate(reader.pages):
                    raw = ""
                    try:
                        # Attempt layout-aware extraction if supported to preserve column/table structures
                        raw = page.extract_text(extraction_mode="layout") or ""
                    except Exception:
                        raw = page.extract_text() or ""

                    cleaned = cls.clean_text(raw)
                    if cleaned:
                        word_count = len(cleaned.split())
                        total_extracted_words += word_count
                        pages.append({
                            "page_number": idx + 1,
                            "text": cleaned
                        })

                if not pages or total_extracted_words < 15:
                    raise ValueError(
                        f"PDF contains {total_page_count} page(s) but no readable text was found. "
                        "The file appears to be a scanned image-only PDF without an embedded text layer. "
                        "Please upload a searchable/text-based document or apply OCR before uploading."
                    )
                
                # Strip recurring running headers and footers across multi-page documents
                pages = cls.filter_running_headers_and_footers(pages)
            except ValueError:
                raise
            except Exception as e:
                raise ValueError(f"Failed to extract PDF content: {str(e)}")

        elif ext == ".docx":
            try:
                raw = docx2txt.process(str(path))
                cleaned = cls.clean_text(raw)
                if not cleaned:
                    raise ValueError("DOCX document is empty or contains no extractable text.")
                pages.append({
                    "page_number": 1,
                    "text": cleaned
                })
            except Exception as e:
                raise ValueError(f"Failed to extract DOCX content: {str(e)}")

        elif ext == ".txt":
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read()
            except UnicodeDecodeError:
                with open(path, "r", encoding="latin-1") as f:
                    raw = f.read()
            except Exception as e:
                raise ValueError(f"Failed to read TXT content: {str(e)}")

            cleaned = cls.clean_text(raw)
            if not cleaned:
                raise ValueError("Text document is empty.")
            pages.append({
                "page_number": 1,
                "text": cleaned
            })

        else:
            raise ValueError(f"Unsupported file format for extraction: {ext}")

        return pages
