# Testing & Evaluation Guide

## 1. Test Architecture

The testing strategy encompasses unit tests, multi-tenant security verification, integration tests, and repeatable RAG benchmark evaluations.

```
tests/
├── conftest.py                   # Pytest fixtures (testing app, mock clients, user tokens)
├── test_extraction.py            # PDF/TXT/DOCX extraction & whitespace cleaning
├── test_chunking.py              # Recursive splitter & metadata preservation
├── test_faiss_manager.py         # FAISS persistence, atomic saves, search & rebuilds
├── test_auth_api.py              # Registration, login, password hashes, JWT validation
├── test_security_isolation.py    # Cross-tenant document & vector search boundary tests
└── test_rag_pipeline.py          # Grounded answering, citations & prompt injection defense
```

---

## 2. Running Automated Tests

Run the full pytest suite from PowerShell:
```powershell
py -m pytest -v
```

Run tests with test coverage reporting:
```powershell
py -m pytest --cov=backend/app tests/
```

Run specific test files:
```powershell
py -m pytest tests/test_security_isolation.py -v
py -m pytest tests/test_rag_pipeline.py -v
```

---

## 3. RAG Evaluation Benchmark

Execute the standalone evaluation script:
```powershell
py scripts/evaluate_rag.py
```

### Metrics Measured:
1. **Retrieval Recall@K:** Percentage of test queries where the target document chunk appears in the top-$k$ FAISS search results.
2. **Citation Accuracy:** Percentage of generated answers containing accurate source filenames and valid page numbers.
3. **Hallucination Guard / Refusal Accuracy:** Verifies that out-of-domain queries correctly output `"The requested information could not be found in the available documents."` rather than hallucinating.
4. **Latency Timings:** Measured breakdown for query embedding, FAISS index similarity search, and LLM text generation.
