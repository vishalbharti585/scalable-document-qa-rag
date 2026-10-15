# Implementation Plan: 15-Phase Execution Roadmap

## Phase Overview

| Phase | Title | Key Deliverables | Verification Gate |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Workspace & Planning | Docs: requirements, architecture, DB design, security, deployment, plan | Documentation complete |
| **Phase 2** | Project Structure & Flask Core | Directory hierarchy, `requirements.txt`, app factory, config validation, health routes | App starts, health endpoints return 200 |
| **Phase 3** | PostgreSQL & SQLAlchemy Models | User, Collection, Document, Chunk, Conversation, Message models, migrations | Models instantiate, SQLite/PG tests pass |
| **Phase 4** | Auth & Authorization | Registration, login, password hashing, JWT claims, protected route decorator | Unit & integration tests for auth & tenant isolation |
| **Phase 5** | Document Upload & Extraction | Upload validator, UUID storage, text extractors (PDF, TXT, DOCX), status tracking | Test files in 3 formats parse correctly |
| **Phase 6** | Chunking & Embedding Service | Recursive character splitter, metadata preservation, embedding provider interface | Chunking tests verify offset & metadata |
| **Phase 7** | FAISS Indexing & Persistence | IndexFlatIP/L2 manager, atomic file writing, JSON metadata mapping, manifest, delete/rebuild | Index survives restart, vector search verified |
| **Phase 8** | Retrieval Engine & Citations | Similarity search, top-k, threshold filter, ownership filter, citation validator | Retrieved chunks match source metadata |
| **Phase 9** | LLM Generation & Grounding | Strict system prompt, anti-hallucination guard, provider interface (Gemini/OpenAI/mock) | Real/mock answer generation produces citations |
| **Phase 10** | Conversations & Messages | Conversation session routes, message history persistence, collection filters | Full chat session cycle persists in DB |
| **Phase 11** | Frontend Design System & Auth UI | SaaS CSS framework, layout, landing page, login, registration, dashboard | Responsive UI renders, auth flows execute |
| **Phase 12** | Frontend App Integration | Document manager (drag-drop, status polling), collections view, chat UI with citations | End-to-end user journey works in browser |
| **Phase 13** | Automated Testing Suite | Unit tests, API tests, security tests, RAG evaluation script (`evaluate_rag.py`) | All pytest test cases pass |
| **Phase 14** | Docker & Deployment Setup | Dockerfile, docker-compose.yml, entrypoint migration runner, Gunicorn config | Container build & compose configuration validated |
| **Phase 15** | Verification & Documentation | Complete README.md with Mermaid diagrams, API reference, final checklist | All 25 criteria verified |

---

## Detailed Phase Milestones & Files

### Phase 1: Planning (Completed)
- `docs/requirements.md`
- `docs/architecture.md`
- `docs/database-design.md`
- `docs/security-design.md`
- `docs/deployment-plan.md`
- `docs/implementation-plan.md`

### Phase 2: Python Environment & Flask Application Factory
- `backend/requirements.txt`: Pin exact stable dependencies (`Flask`, `Flask-SQLAlchemy`, `Flask-Migrate`, `Flask-JWT-Extended`, `faiss-cpu`, `langchain`, `pypdf`, `docx2txt`, `argon2-cffi`, `python-dotenv`, `pytest`).
- `backend/app/config.py`: Environment-driven configuration with strict startup validation.
- `backend/app/extensions.py`: Initialized extensions (SQLAlchemy `db`, Migrate `migrate`, JWTManager `jwt`).
- `backend/app/__init__.py`: Application factory function `create_app(config_name)`.
- `backend/app/routes/health.py`: `/api/v1/health` and `/api/v1/ready`.
- `backend/run.py`: WSGI entrypoint.

### Phase 3: PostgreSQL Models & Database Layer
- `backend/app/models/user.py`
- `backend/app/models/collection.py`
- `backend/app/models/document.py`
- `backend/app/models/chunk.py`
- `backend/app/models/conversation.py`
- `backend/app/models/message.py`
- Migration script templates and initialization.

### Phase 4: Authentication & Security
- `backend/app/services/auth_service.py`
- `backend/app/routes/auth.py`
- Custom JWT unauthorized & expired handlers with uniform JSON response.
- Ownership verification helpers.

### Phase 5: Document Ingestion Service
- `backend/app/services/ingestion/extractor.py` (PyPDF, docx2txt, text extraction with page detection).
- `backend/app/services/ingestion/validator.py` (MIME sniffing, size limit, extension whitelist).
- `backend/app/routes/documents.py`.

### Phase 6: Text Chunking & Embeddings
- `backend/app/services/chunking/splitter.py` (Recursive character splitting with metadata).
- `backend/app/services/embeddings/provider.py` (Abstract interface + Gemini, OpenAI, and DeterministicMock providers).

### Phase 7: FAISS Index Manager
- `backend/app/services/vector_store/faiss_manager.py`:
  - Per-user directory isolation (`storage/faiss_indexes/user_{id}/`).
  - Native `faiss.write_index` / `faiss.read_index`.
  - JSON metadata mapping & manifest tracking.
  - Mutex file lock & atomic `.tmp` replacement.
  - Safe document deletion & index rebuild.

### Phase 8 & 9: Grounded Retrieval & Answer Generation
- `backend/app/services/retrieval/retriever.py`: Similarity search, thresholding, metadata filtering.
- `backend/app/services/generation/generator.py`: Strict grounding prompt, source validation, insufficient-context fallback.
- `backend/app/routes/chat.py`.

### Phase 10: Collections & Chat History
- `backend/app/routes/collections.py`.
- Message persistence and collection assignment endpoints.

### Phase 11 & 12: Professional Frontend UI & API Integration
- `frontend/index.html` (Landing page)
- `frontend/login.html` & `frontend/register.html`
- `frontend/dashboard.html`
- `frontend/documents.html`
- `frontend/collections.html`
- `frontend/chat.html`
- `frontend/settings.html`
- `frontend/css/style.css` (Clean SaaS design system, responsive flex/grid)
- `frontend/js/api.js` (Centralized fetch wrapper, token refresh, error handling)
- `frontend/js/app.js` (UI state, drag-drop upload, chat streaming/citations)

### Phase 13: Testing & Quality Assurance
- `tests/test_extraction.py`
- `tests/test_chunking.py`
- `tests/test_faiss_manager.py`
- `tests/test_auth_api.py`
- `tests/test_documents_api.py`
- `tests/test_security_isolation.py`
- `tests/test_rag_pipeline.py`
- `scripts/evaluate_rag.py`

### Phase 14 & 15: Docker, Deployment & GitHub Readiness
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `.gitignore`
- `README.md`
