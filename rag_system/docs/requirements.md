# Requirements Specification

## 1. Project Overview & Objective
**System Name:** Scalable Document Question Answering System (RAG)  
**Target Domain:** Enterprise & Academic Document Question-Answering  
**Purpose:** A secure, multi-user web application allowing users to upload diverse documents (PDF, TXT, DOCX), process and index them into persistent vector storage using FAISS, and perform grounded natural language question answering with source citations, strict tenant data isolation, and conversation history.

---

## 2. Functional Requirements (FR)

### 2.1 User Management & Authentication
- **FR-AUTH-1:** The system shall allow users to register with a unique email and secure password.
- **FR-AUTH-2:** Passwords must be hashed using Argon2 or Werkzeug secure password hashing (PBKDF2/SHA-256).
- **FR-AUTH-3:** The system shall issue JSON Web Tokens (JWT) upon successful authentication.
- **FR-AUTH-4:** All protected API endpoints must validate JWT claims and extract authenticated user identity (`user_id`).
- **FR-AUTH-5:** The system shall provide an endpoint to inspect current user profile (`/api/v1/auth/me`).

### 2.2 Document Management & Ingestion
- **FR-DOC-1:** The system shall accept document uploads in PDF (`.pdf`), plain text (`.txt`), and Microsoft Word (`.docx`).
- **FR-DOC-2:** The system shall validate file size against a configurable threshold (`MAX_CONTENT_LENGTH`, default 16MB) and enforce MIME/extension verification.
- **FR-DOC-3:** Uploaded files must be saved with server-generated UUID-based storage filenames to prevent path traversal or overwrites.
- **FR-DOC-4:** The system shall extract text while preserving page number metadata where the file format supports it (PDF).
- **FR-DOC-5:** Text extraction must gracefully detect empty, unreadable, or corrupted files, marking status as `failed` with diagnostic error messages.
- **FR-DOC-6:** Document processing states shall transition through `uploaded` -> `processing` -> `processed` (or `failed`).
- **FR-DOC-7:** Duplicate document upload detection shall use SHA-256 content hashing to avoid redundant indexing.
- **FR-DOC-8:** Users shall be able to reprocess failed or updated documents via a dedicated API endpoint (`POST /api/v1/documents/{id}/reprocess`).
- **FR-DOC-9:** Users shall be able to delete documents, which must trigger cascading removal of metadata, chunks in PostgreSQL, and corresponding vectors in FAISS.

### 2.3 Collections & Categorization
- **FR-COL-1:** Users shall be able to create, rename, and delete document collections.
- **FR-COL-2:** Documents can be assigned to a collection (or remain in the default global collection).
- **FR-COL-3:** Deleting a collection must not orphan documents or indexes; documents are either reassigned to default or explicitly cleaned up.

### 2.4 Text Chunking & Embedding Generation
- **FR-CHUNK-1:** Text must be split into configurable chunk sizes (`CHUNK_SIZE`, default 1000 characters) with overlap (`CHUNK_OVERLAP`, default 200 characters) using recursive character splitting.
- **FR-CHUNK-2:** Each chunk must maintain structured metadata: `chunk_id`, `document_id`, `user_id`, `collection_id`, `chunk_index`, `page_number`, `source_filename`, and character start/end offsets.
- **FR-EMB-1:** Embeddings must be generated through a configurable provider interface supporting Google Gemini, OpenAI, or local HuggingFace/deterministic models.

### 2.5 FAISS Vector Indexing & Persistence
- **FR-FAISS-1:** Vector indexes must use FAISS (Facebook AI Similarity Search) and strictly forbid replacement by pgvector or cloud vector databases.
- **FR-FAISS-2:** Indexes must persist on disk under `storage/faiss_indexes/` and remain recoverable across application restarts.
- **FR-FAISS-3:** Multi-user isolation must be enforced: each user (or user-collection pair) has dedicated FAISS index directories, preventing any cross-tenant data leakage.
- **FR-FAISS-4:** Atomic index file replacement must prevent index corruption during concurrent write/update operations.
- **FR-FAISS-5:** The system shall maintain an index manifest file recording index version, dimension, total vector count, document IDs, and checksums.
- **FR-FAISS-6:** Vector deletion: If the underlying FAISS index type does not support arbitrary ID removal, the system shall safely rebuild the user index from remaining active database chunks.

### 2.6 Retrieval Engine
- **FR-RET-1:** Similarity search shall return top-$k$ most relevant chunks using normalized cosine similarity / inner product distance.
- **FR-RET-2:** Chunks below a configurable `SIMILARITY_THRESHOLD` shall be filtered out.
- **FR-RET-3:** Queries can optionally be filtered by specific collection or document IDs, while always strictly scoped to the authenticated user.
- **FR-RET-4:** Empty retrieval results must trigger an explicit insufficient-context response without LLM hallucination.

### 2.7 Grounded Answer Generation & Citations
- **FR-GEN-1:** The LLM prompt must strictly instruct the model to answer exclusively from retrieved context and refuse to invent facts.
- **FR-GEN-2:** Answers must include traceable citations containing: document name, page number, chunk identifier, and exact supporting excerpt.
- **FR-GEN-3:** The system must validate citations against actually retrieved chunks before returning to the client.
- **FR-GEN-4:** Injected instructions or jailbreak attempts in document text must be treated as untrusted text and neutralized.

### 2.8 Conversations & Chat History
- **FR-CHAT-1:** Users can create multiple conversation sessions.
- **FR-CHAT-2:** Chat messages (user queries and assistant responses with citations) must be persisted in PostgreSQL.
- **FR-CHAT-3:** Previous conversations can be reviewed, resumed, or deleted.

---

## 3. Non-Functional Requirements (NFR)

### 3.1 Security & Privacy
- **NFR-SEC-1:** Authentication via JWT with expiration and token validation on every protected route.
- **NFR-SEC-2:** Strict Multi-Tenant Isolation: At no point shall a query from User A retrieve chunks or documents owned by User B.
- **NFR-SEC-3:** No API keys or secrets hardcoded or transmitted to client browser.
- **NFR-SEC-4:** Path traversal protection: file uploads stripped of dangerous characters; stored under secure generated UUID paths.
- **NFR-SEC-5:** Untrusted text escaping: Frontend must render content safely using `textContent` / DOM escaping rather than `innerHTML`.
- **NFR-SEC-6:** SQL injection prevention via SQLAlchemy ORM parameterized queries.

### 3.2 Performance & Scalability
- **NFR-PERF-1:** FAISS similarity search latency under 50ms for collections up to 50,000 vectors.
- **NFR-PERF-2:** Lazy index loading: FAISS indexes loaded on demand into memory cache and refreshed when disk manifest updates.
- **NFR-PERF-3:** Thread-safe file locks (`portalocker` or mutex lock) during index writes to prevent race conditions.

### 3.3 Reliability & Availability
- **NFR-REL-1:** Graceful degradation: A failure in one document's processing must not block or crash the application.
- **NFR-REL-2:** Health & Readiness probes (`/api/v1/health` and `/api/v1/ready`) checking process state, database connectivity, and index directory integrity.
- **NFR-REL-3:** Database transactions with rollback on failure to prevent orphaned records.

### 3.4 Usability & Accessibility
- **NFR-UX-1:** Modern, responsive SaaS user interface with consistent typography, cards, badges, and modals.
- **NFR-UX-2:** Clear upload feedback, real-time status polling, active loading spinners, and actionable error messages.
- **NFR-UX-3:** Keyboard accessibility and mobile responsiveness.
