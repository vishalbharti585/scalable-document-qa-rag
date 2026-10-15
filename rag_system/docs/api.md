# REST API Reference Specification

All endpoints are versioned under `/api/v1` and use standard JSON response formats.

### Standard Response Envelope
```json
{
  "success": true,
  "data": { ... },
  "message": "Human-readable status summary"
}
```

### Standard Error Envelope
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Actionable description of the error"
  }
}
```

---

## 1. Authentication Endpoints

### `POST /api/v1/auth/register`
Register a new user account.
- **Headers:** `Content-Type: application/json`
- **Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "Password123!",
    "full_name": "Jane Doe"
  }
  ```
- **Response:** `201 Created` with JWT access token and user profile.

### `POST /api/v1/auth/login`
Authenticate user credentials and receive a JWT token.
- **Headers:** `Content-Type: application/json`
- **Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "Password123!"
  }
  ```
- **Response:** `200 OK` with `access_token` and `user` object.

### `GET /api/v1/auth/me`
Retrieve currently authenticated user's profile.
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK`

---

## 2. Document Ingestion Endpoints

### `POST /api/v1/documents`
Upload and index a document (PDF, TXT, DOCX).
- **Headers:**
  - `Authorization: Bearer <token>`
  - `Content-Type: multipart/form-data`
- **Body:**
  - `file`: binary file stream
  - `collection_id`: (optional) string UUID
- **Response:** `201 Created`

### `GET /api/v1/documents`
List user documents with pagination and optional collection filter.
- **Headers:** `Authorization: Bearer <token>`
- **Query Params:**
  - `page`: int (default 1)
  - `per_page`: int (default 20)
  - `collection_id`: (optional) filter by collection
- **Response:** `200 OK`

### `DELETE /api/v1/documents/{id}`
Delete a document and rebuild the user's FAISS index.
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK`

### `POST /api/v1/documents/{id}/reprocess`
Reprocess a document from original stored file.
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK`

---

## 3. Collections Endpoints

### `POST /api/v1/collections`
Create a document collection.
- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Body:** `{"name": "Finance Q3", "description": "Audited balance sheets"}`
- **Response:** `201 Created`

### `GET /api/v1/collections`
List user collections with document counts.
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK`

### `DELETE /api/v1/collections/{id}`
Delete collection without deleting associated documents.
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK`

---

## 4. Grounded Chat & Conversation Endpoints

### `POST /api/v1/conversations`
Create a new conversation session.
- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Body:** `{"title": "Mars Rover Queries"}`
- **Response:** `201 Created`

### `GET /api/v1/conversations`
List all user conversations.
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK`

### `GET /api/v1/conversations/{id}`
Retrieve a conversation with complete turn history and citations.
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK`

### `POST /api/v1/conversations/{id}/messages`
Send user query, run grounded RAG generation, persist turns, and return answer with citations.
- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Body:**
  ```json
  {
    "message": "When did Perseverance land on Mars?",
    "collection_id": "optional-uuid",
    "document_ids": ["optional-uuid-list"]
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "answer": "Based on the provided documents: NASA Perseverance rover landed in Jezero crater in February 2021.",
      "citations": [
        {
          "source_id": "source-1",
          "document_id": "...",
          "document_name": "mars_mission.txt",
          "page_number": 1,
          "similarity_score": 0.88,
          "supporting_excerpt": "NASA Perseverance rover landed in Jezero crater in February 2021."
        }
      ],
      "metrics": {
        "retrieval_ms": 12,
        "llm_ms": 320,
        "total_ms": 332
      }
    }
  }
  ```
