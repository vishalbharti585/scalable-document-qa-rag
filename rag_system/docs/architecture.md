# System Architecture Specification

## 1. High-Level Architecture Overview

The **Scalable Document Question Answering System (RAG)** follows a modular, layered architecture decoupling presentation, REST APIs, domain services, persistence engines, and external AI providers.

```mermaid
flowchart TD
    subgraph Client ["Client Layer (Browser)"]
        UI["Modern Responsive Frontend\n(HTML5, CSS3, ES6 JavaScript)"]
    end

    subgraph API ["Application Gateway & API (Flask)"]
        Routes["Flask REST Blueprint Routes\n(/api/v1/auth, /documents, /collections, /chat)"]
        AuthMid["JWT Auth Middleware & User Context"]
        ValMid["Input Validation & Error Handler"]
    end

    subgraph Services ["Core Domain Services"]
        DocSvc["Document Ingestion Service\n(PDF/TXT/DOCX Extraction & Hash)"]
        ChunkSvc["Text Chunking & Metadata Service\n(Recursive Character Splitter)"]
        EmbedSvc["Embedding Service Interface\n(Gemini / OpenAI / Local HuggingFace)"]
        FAISSMgr["FAISS Index Lifecycle Manager\n(Atomic Writes, Manifests, Tenant Isolation)"]
        ChatSvc["Grounded Retrieval & Chat Service\n(Vector Search, Citations, Hallucination Guard)"]
        GenSvc["LLM Generation Interface\n(Strict Grounded Prompts, Source Verification)"]
    end

    subgraph Persistence ["Persistence Layer"]
        PG[("PostgreSQL Database\n(Users, Docs, Chunks, Convs, Messages)")]
        DiskStorage[("Persistent File Storage\nstorage/uploads/ (UUID Document Files)")]
        FAISSStorage[("FAISS Storage Engine\nstorage/faiss_indexes/user_{id}/ (index.faiss, index.pkl, manifest.json)")]
    end

    subgraph External ["External AI Services"]
        LLMAPI["LLM Provider API\n(Google Gemini / OpenAI)"]
        EmbAPI["Embedding Provider API"]
    end

    UI -->|HTTP / JSON + JWT| Routes
    Routes --> AuthMid --> ValMid
    ValMid --> DocSvc & ChatSvc
    DocSvc --> ChunkSvc --> EmbedSvc
    EmbedSvc --> EmbAPI
    ChunkSvc --> FAISSMgr
    FAISSMgr --> FAISSStorage
    DocSvc --> DiskStorage
    DocSvc & ChatSvc --> PG
    ChatSvc --> FAISSMgr
    ChatSvc --> GenSvc
    GenSvc --> LLMAPI
```

---

## 2. Request and Data Flows

### 2.1 Ingestion Flow (Document Upload to FAISS Indexing)
```mermaid
sequenceDiagram
    autonumber
    actor User as Client Browser
    participant API as Flask REST API
    participant DocSvc as Document Service
    participant Disk as File Storage
    participant DB as PostgreSQL
    participant ChunkSvc as Chunking Service
    participant EmbSvc as Embedding Service
    participant FAISS as FAISS Index Manager

    User->>API: POST /api/v1/documents (multipart/form-data + Bearer JWT)
    API->>API: Validate JWT & file headers (PDF/TXT/DOCX, size limit)
    API->>DocSvc: Process document(file, user_id, collection_id)
    DocSvc->>Disk: Save file under UUID filename (storage/uploads/user_{id}/...)
    DocSvc->>DB: INSERT into documents (status='uploaded', file_hash, size)
    DocSvc->>DocSvc: Extract text & page metadata (PyPDF / docx2txt)
    DocSvc->>DB: UPDATE documents (status='processing', page_count)
    DocSvc->>ChunkSvc: Split document text into chunks
    ChunkSvc-->>DocSvc: Chunks with chunk_index, page_number, offsets
    DocSvc->>DB: INSERT bulk into document_chunks
    DocSvc->>EmbSvc: Generate embeddings for chunks
    EmbSvc-->>DocSvc: List of normalized vector arrays [dim=N]
    DocSvc->>FAISS: Add vectors & metadata to user index (user_id)
    FAISS->>FAISS: Thread-safe write & atomic file replacement (.tmp -> .faiss)
    DocSvc->>DB: UPDATE documents (status='processed')
    DocSvc-->>API: Document summary & chunk count
    API-->>User: 201 Created (document metadata, status='processed')
```

### 2.2 Retrieval & Grounded Generation Flow (Chat Query)
```mermaid
sequenceDiagram
    autonumber
    actor User as Client Browser
    participant API as Flask REST API
    participant ChatSvc as Chat Service
    participant EmbSvc as Embedding Service
    participant FAISS as FAISS Index Manager
    participant DB as PostgreSQL
    participant LLM as LLM Generation Service

    User->>API: POST /api/v1/conversations/{id}/messages (question, filters)
    API->>ChatSvc: Ask question (query, conversation_id, user_id, collection_filter)
    ChatSvc->>DB: Save user message in messages table
    ChatSvc->>EmbSvc: Generate query embedding
    EmbSvc-->>ChatSvc: Query vector [dim=N]
    ChatSvc->>FAISS: Similarity search (user_id, query_vector, top_k, threshold)
    FAISS-->>ChatSvc: Relevant chunk candidates (chunk_ids, distances)
    ChatSvc->>DB: Verify chunk ownership & active status from PostgreSQL
    alt No chunks pass similarity threshold
        ChatSvc-->>User: Insufficient context ("Information not found in available documents.")
    else Chunks retrieved
        ChatSvc->>LLM: Generate answer with strictly grounded system prompt & context
        LLM-->>ChatSvc: Grounded response + raw source references
        ChatSvc->>ChatSvc: Validate and cross-reference citations against actual chunks
        ChatSvc->>DB: Save assistant response + validated citations JSON in messages
        ChatSvc-->>API: Answer + validated citations
        API-->>User: 200 OK (answer, citations, latency_metrics)
    end
```

---

## 3. FAISS Vector Indexing & Persistence Strategy

### 3.1 Strict Vector Engine Mandate
In strict compliance with requirements:
- **FAISS is the exclusive vector indexing engine.**
- **PostgreSQL does NOT use `pgvector`.** PostgreSQL is solely responsible for relational metadata (users, documents, chunks, conversations, messages).
- Vectors are stored exclusively in serialized FAISS index files on the persistent filesystem.

### 3.2 Directory Structure & Multi-Tenant Isolation
Multi-user data isolation is enforced at the storage and memory layers:
```
storage/
├── uploads/
│   └── user_{user_id}/
│       └── {document_uuid}.{ext}
└── faiss_indexes/
    └── user_{user_id}/
        ├── index.faiss        # Serialized FAISS binary index (IndexFlatIP or IndexHNSW)
        ├── metadata.json      # Mapping: vector_id -> chunk_id, document_id, page
        ├── manifest.json      # Metadata: version, total_vectors, checksum, updated_at
        └── index.faiss.lock   # Mutex file lock during mutations
```

Each user has an isolated physical directory. User queries can **only** load and search the FAISS index resident within their own authenticated user directory (`storage/faiss_indexes/user_{user_id}/`). Cross-tenant vector leakage is architecturally impossible.

### 3.3 Atomic Index Persistence and Safe Mutation
To prevent file corruption during writes or system crashes:
1. When adding vectors:
   - Acquire file lock on `index.faiss.lock`.
   - Update in-memory index copy or load existing.
   - Write updated index to temporary file `index.faiss.tmp`.
   - Perform atomic replacement via `os.replace("index.faiss.tmp", "index.faiss")`.
   - Update `metadata.json` and `manifest.json`.
   - Release lock.
2. In-memory Index Cache:
   - An LRU index cache caches deserialized FAISS instances in memory.
   - Cache invalidation occurs automatically if `manifest.json` timestamp changes.

### 3.4 Vector Deletion Strategy
Standard flat FAISS indexes (`IndexFlatIP` / `IndexFlatL2`) do not support arbitrary deletion of vectors by ID without re-indexing.
- When a document is deleted:
  1. The document and its chunks are deleted from PostgreSQL within a database transaction.
  2. The `FAISSIndexManager` is instructed to remove the document's vectors.
  3. The index manager performs an atomic rebuild for the user: it loads all remaining active chunks for that user from PostgreSQL, batches their pre-stored or newly generated vectors, constructs a fresh index, and writes it atomically.
  4. This guarantees that deleted documents leave zero stale vectors or orphaned citations.

---

## 4. PostgreSQL and FAISS Interaction

| Entity / Concern | PostgreSQL Database | FAISS Vector Store |
| :--- | :--- | :--- |
| **Authentication & Users** | Credentials, password hash, user state | None |
| **Document Metadata** | Filename, UUID, size, MIME, hash, status | None |
| **Chunk Text & Offsets** | Text content, character offsets, page number | None |
| **Vector Embeddings** | No vectors stored (`pgvector` forbidden) | High-dimensional dense float32 arrays |
| **Index Search** | SQL relational filtering, foreign keys | Sub-millisecond similarity search (Cosine/Dot) |
| **Mapping Key** | Primary key `chunk_id` (UUID or Integer) | Vector ordinal ID mapped to `chunk_id` in manifest |
| **Integrity & Cascade** | Strict foreign keys (`ON DELETE CASCADE`) | Synchronized rebuild/update on document lifecycle |

---

## 5. Security & Boundary Protection

1. **Authentication:** Stateless JWT issued upon bcrypt/Argon2 verification, validated via HTTP `Authorization: Bearer <token>` header.
2. **Tenant Scoping:** Every SQL query includes `WHERE user_id = :current_user_id`. Every FAISS operation resolves to `storage/faiss_indexes/user_{current_user_id}`.
3. **No Untrusted Deserialization:**
   - Standard LangChain FAISS loaders that rely on unrestricted `pickle.load` present deserialization vulnerabilities.
   - Our `FAISSIndexManager` uses native `faiss.write_index` / `faiss.read_index` for the binary vector index, and strict `json` format for `metadata.json` and `manifest.json`.
4. **Prompt Injection Mitigation:**
   - Document context chunks are clearly bounded within XML/delimiters in the prompt.
   - System instructions explicitly forbid the LLM from obeying user/document overrides or leaking system instructions.
