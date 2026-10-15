# RAG Codebase Audit Report: Retrieval Accuracy & Document Grounding

**Project:** Scalable Document Question Answering System (RAG)  
**Date:** October 2026  
**Auditor:** Senior AI/ML Engineer  

---

## 1. Executive Summary & Current Behavior

The application is a functional full-stack RAG system consisting of:
- **Backend:** Flask REST API with Flask-JWT-Extended, SQLAlchemy, SQLite/PostgreSQL.
- **Vector Search Engine:** FAISS (`IndexFlatIP` with unit-normalized vectors) operating on atomic disk-persisted indexes per user.
- **LLM Provider:** Google Gemini API (`gemini-3.5-flash-lite` / `gemini-3.1-flash-lite`) with dynamic fallback handling high-demand (`503`) spikes and rate-limits (`429`).
- **Embedding Provider:** Deterministic pseudo-semantic token-hash embedder (768-dim) by default in `.env` (`EMBEDDING_PROVIDER=mock`), with pluggable Gemini API (`gemini-embedding-001`, 3072-dim) and OpenAI embedders.
- **Document Ingestion:** Text extraction from PDF (`pypdf`), DOCX (`docx2txt`), and TXT with sentence stitching and character offset tracking.
- **Frontend:** Vanilla HTML5/CSS3/ES6 JavaScript single-page SaaS interface with session management, collections, and markdown rendering.

---

## 2. Confirmed Bugs

1. **Empty Collection Scope Bug (`chat.py` & `faiss_manager.py`):**
   - **Location:** `backend/app/routes/chat.py` (lines 134-137) and `backend/app/services/vector_store/faiss_manager.py` (line 192).
   - **Bug:** When a user selects a collection that contains zero documents, `document_ids = [d.id for d in docs]` evaluates to `[]`. In `faiss_manager.search()`, the filter check is `if document_filter_ids and item_meta.get("document_id") not in document_filter_ids:`. Because `[]` is falsy in Python, the filter was completely bypassed, causing FAISS to search across ALL user documents instead of returning an empty result set.
   - **Severity:** High (Security/Data Isolation defect).

2. **Uncalibrated Similarity Scores (`faiss_manager.py`):**
   - **Location:** `backend/app/services/vector_store/faiss_manager.py` (line 205).
   - **Bug:** `final_score = raw_score + boost`. With raw cosine similarity reaching up to 1.0 and lexical phrase boost adding up to 0.35, the resulting score can exceed 1.0 (e.g. 1.25), displaying `125%` similarity in the frontend citation cards.
   - **Severity:** Medium (Diagnostic/UI precision defect).

3. **Abbreviation/Number Over-splitting in Text Splitter:**
   - **Location:** `backend/app/services/chunking/splitter.py` (line 18).
   - **Bug:** Using basic string split on `". "` causes numbered questions (e.g., `Q1. `, `1. `), technical standards (e.g., `IEEE 802.11`), and abbreviations (e.g., `e.g. `, `i.e. `, `Fig. 2. `) to be fractured into partial tokens.
   - **Severity:** Medium (Chunk boundary integrity defect).

---

## 3. Retrieval Weaknesses

1. **Lack of Chunk Deduplication / Diversity (Redundant Chunks):**
   - High similarity search can return 3 or 4 virtually identical chunks (e.g. overlapping slices of the same exam questions or repeated header blocks), starving other relevant pages from entering the top-$k$ context.
2. **Missing Neighboring Chunk Context Expansion:**
   - When a technical definition or formula spans the boundary between Chunk $N$ and Chunk $N+1$, retrieving only Chunk $N$ leaves Gemini with an incomplete sentence or missing conclusion.
3. **Lexical Matching Weighting:**
   - The current keyword boost treats common stop words or high-frequency words identically. Rare technical terms (e.g. `MPPT`, `photovoltaic`, `pyranometer`, `HAWT`, `Betz`) need inverse document frequency (IDF) weighting.
4. **Lack of In-Depth Query Diagnostics:**
   - There was no structured telemetry returning retrieval candidates, raw FAISS distance, lexical boost breakdown, and filtering decisions for developer evaluation.

---

## 4. Answer-Generation Weaknesses

1. **Multipart and Incomplete Context Guidance:**
   - If a user asks a two-part question where Part A is in the document but Part B is absent, earlier prompts tended to either answer both with extrapolation or reject both. The prompt needs explicit instructions to answer the supported portion and clearly state what is absent.
2. **Technical Depth & Formula Preservation:**
   - Complex engineering queries (e.g., efficiency calculations, physical laws, units) require explicit instruction to preserve mathematical variables, formulas, and exact units without rounding or approximating.
3. **Contradiction and Ambiguity Handling:**
   - If multiple chunks discuss conflicting figures or estimates (e.g. varying cut-in speeds across turbine models), the system must explicitly present the comparison rather than choosing one arbitrarily.

---

## 5. Citation & Metadata Weaknesses

1. **Active Citation Verification:**
   - Currently, all top-$k$ retrieved chunks are displayed in the citation list even if the LLM only actually used 2 of them to answer the question.
   - Need an active verification filter: match key phrases/entities from the generated answer against retrieved chunk excerpts to highlight chunks that genuinely contributed evidence.

---

## 6. Proposed Fixes & Implementation Plan

| Component | Target File | Proposed Fix |
| :--- | :--- | :--- |
| **Search Scope Isolation** | `backend/app/routes/chat.py` & `faiss_manager.py` | Fix empty collection handling so `document_filter_ids = []` immediately yields 0 candidates. |
| **Score Calibration** | `backend/app/services/vector_store/faiss_manager.py` | Clamp and normalize hybrid scores into $[0.0, 1.0]$. |
| **Chunk Deduplication (MMR-style)** | `backend/app/services/vector_store/faiss_manager.py` | Add Jaccard/overlap deduplication to penalize near-duplicate chunks in top-$k$. |
| **Neighboring Context Expansion** | `backend/app/services/vector_store/faiss_manager.py` | If adjacent chunks are relevant, stitch contiguous chunk windows for unbroken context. |
| **Sentence-Aware Splitter** | `backend/app/services/chunking/splitter.py` | Protect numbered lists and abbreviations from premature `. ` splitting. |
| **Extraction Quality** | `backend/app/services/ingestion/extractor.py` | Add layout-aware extraction fallback and report page coverage / OCR warnings for scanned PDFs. |
| **Evidence-Grounded Prompt** | `backend/app/services/retrieval/rag_service.py` | Update prompt with multipart partial-evidence handling, formula grounding, and conflict reporting. |
| **Active Citation Verifier** | `backend/app/services/retrieval/rag_service.py` | Cross-verify which chunks actually supported the answer. |
| **Comprehensive Diagnostics** | `backend/app/services/retrieval/rag_service.py` | Add development-time retrieval tracing and telemetry. |
| **Evaluation Benchmark** | `tests/test_retrieval_grounding_suite.py` | Build a rigorous, multi-scenario evaluation suite testing all requirements. |
