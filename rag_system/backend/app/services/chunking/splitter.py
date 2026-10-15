import re
from typing import List, Dict, Any, Optional


class TextSplitter:
    """Configurable recursive text splitter preserving sentence, paragraph, and page boundaries."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError(f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text by separators until pieces fit within chunk_size."""
        final_chunks = []
        separator = separators[-1]
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        if separator == ". ":
            # Avoid splitting on abbreviations like e.g., i.e., vs., Q1., Fig. 1.
            raw_splits = text.split(". ")
            splits = []
            buf = []
            for part in raw_splits:
                buf.append(part)
                words = part.strip().split()
                last_word = words[-1].lower() if words else ""
                # If the segment ends in a known abbreviation or single identifier, buffer it
                if last_word in ("e.g", "i.e", "fig", "vol", "no", "vs", "dr", "mr", "etc") or re.match(r"^[a-z]\d*$", last_word):
                    continue
                splits.append(". ".join(buf))
                buf = []
            if buf:
                if splits:
                    splits[-1] += ". " + ". ".join(buf)
                else:
                    splits.append(". ".join(buf))
        elif separator != "":
            splits = text.split(separator)
        else:
            splits = list(text)

        good_splits = []
        for s in splits:
            if not s:
                continue
            if len(s) <= self.chunk_size:
                good_splits.append(s)
            else:
                if new_separators:
                    sub_splits = self._split_text(s, new_separators)
                    good_splits.extend(sub_splits)
                else:
                    # Hard split if no more separators
                    for j in range(0, len(s), self.chunk_size - self.chunk_overlap):
                        good_splits.append(s[j:j + self.chunk_size])

        # Merge good splits into chunks respecting chunk_size and chunk_overlap
        current_chunk = []
        current_len = 0

        for piece in good_splits:
            piece_len = len(piece) + (len(separator) if current_chunk else 0)
            if current_len + piece_len > self.chunk_size and current_chunk:
                merged = separator.join(current_chunk)
                final_chunks.append(merged)
                # Keep overlap from the end
                overlap_len = 0
                overlap_chunk = []
                for p in reversed(current_chunk):
                    if overlap_len + len(p) <= self.chunk_overlap:
                        overlap_chunk.insert(0, p)
                        overlap_len += len(p)
                    else:
                        break
                current_chunk = overlap_chunk
                current_len = sum(len(p) for p in current_chunk) + (len(separator) * max(0, len(current_chunk) - 1))

            current_chunk.append(piece)
            current_len += len(piece) + (len(separator) if len(current_chunk) > 1 else 0)

        if current_chunk:
            final_chunks.append(separator.join(current_chunk))

        return [c.strip() for c in final_chunks if c.strip()]

    def split_pages(
        self,
        pages: List[Dict[str, Any]],
        document_id: str,
        user_id: str,
        source_filename: str,
        collection_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Split a list of extracted pages into chunks while preserving page numbers and offsets.
        
        Returns:
            list of dicts matching DocumentChunk attributes.
        """
        all_chunks = []
        global_chunk_idx = 0

        for page in pages:
            page_num = page.get("page_number", 1)
            page_text = page.get("text", "")
            if not page_text.strip():
                continue

            raw_chunks = self._split_text(page_text, self.separators)

            search_start = 0
            for chunk_content in raw_chunks:
                # Find character offsets within the page
                start_idx = page_text.find(chunk_content, search_start)
                if start_idx == -1:
                    start_idx = search_start
                end_idx = start_idx + len(chunk_content)
                search_start = max(0, end_idx - self.chunk_overlap)

                all_chunks.append({
                    "id": f"{document_id}_{global_chunk_idx}",
                    "document_id": document_id,
                    "collection_id": collection_id,
                    "user_id": user_id,
                    "source_filename": source_filename,
                    "chunk_index": global_chunk_idx,
                    "content": chunk_content,
                    "page_number": page_num,
                    "start_char_idx": start_idx,
                    "end_char_idx": end_idx,
                    "metadata": {
                        "document_id": document_id,
                        "collection_id": collection_id,
                        "user_id": user_id,
                        "source_filename": source_filename,
                        "page_number": page_num,
                        "chunk_index": global_chunk_idx,
                        "char_count": len(chunk_content),
                    }
                })
                global_chunk_idx += 1

        return all_chunks
