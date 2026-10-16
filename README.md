# Scalable Document Question Answering System (RAG)

An AI-powered document question-answering system that uses **Retrieval-Augmented Generation (RAG)** to retrieve relevant information from uploaded documents and generate context-aware answers using a Large Language Model (LLM).

The project combines semantic search, vector embeddings, and Google's Gemini API to help users interact with their documents through natural-language questions.

## 🌐 Live Demo

**Live Application:** https://scalable-document-qa-rag-frontend.onrender.com


## 📌 Project Overview

Traditional document reading and searching can be time-consuming, especially when working with lengthy technical documents. This project simplifies the process by allowing users to upload documents and ask questions in natural language.

The system retrieves relevant document chunks using a FAISS vector index and passes the retrieved context to Gemini to generate answers based on the available information.

## ✨ Key Features

- **Document-Based Question Answering:** Ask natural-language questions about uploaded documents.
- **Retrieval-Augmented Generation:** Combines document retrieval with LLM-based answer generation.
- **Semantic Search:** Retrieves relevant content based on the meaning of a query.
- **FAISS Vector Search:** Uses a vector index for similarity-based retrieval.
- **Context-Aware Responses:** Generates answers using retrieved document content.
- **Source References:** Supports displaying retrieved sources and associated metadata, where available.
- **Configurable Retrieval Depth:** Supports different context-depth options if enabled in the application.
- **Web Interface:** Provides a user interface for interacting with the document QA system.

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Backend | Flask |
| AI Framework | LangChain |
| Vector Search | FAISS |
| Language Model | Google Gemini API |
| Frontend | HTML, CSS, JavaScript |
| Database | PostgreSQL, if configured |
| Version Control | Git and GitHub |

## 🏗️ System Architecture

```text
             User
               |
               v
        Web Application
         (HTML/CSS/JS)
               |
               v
        Flask Backend
               |
        Document Upload
               |
               v
       Text Extraction
               |
               v
      Text Chunking
               |
               v
       Embedding Model
               |
               v
         FAISS Index
               |
     User Question Received
               |
               v
      Query Embedding
               |
               v
     Similarity Retrieval
               |
               v
      Relevant Document
            Chunks
               |
               v
     Gemini API + Context
               |
               v
      Generated Answer
               |
               v
       Answer to User
```

## 🔄 How It Works

1. **Document Upload:** The user uploads a supported document through the web interface.
2. **Text Extraction:** The backend extracts readable text from the document.
3. **Text Chunking:** The extracted text is divided into smaller chunks for retrieval.
4. **Embedding Generation:** Text chunks are converted into vector embeddings using the configured embedding model.
5. **Indexing:** The embeddings are stored in a FAISS vector index.
6. **Question Processing:** The user's question is converted into an embedding using the compatible embedding model.
7. **Similarity Search:** FAISS retrieves document chunks relevant to the question.
8. **Answer Generation:** The retrieved context is passed to Gemini through the configured LangChain pipeline.
9. **Response Display:** The generated answer is returned to the user through the web interface.

## 📂 Project Structure

The following is an illustrative structure. Update it to match the actual files in your repository.

```text
scalable-document-qa-rag/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── uploads/
├── vector_store/
└── utils/
```

## ⚙️ Installation and Setup

### Prerequisites

- Python 3.10 or another version supported by your dependencies
- pip
- Git
- A Google Gemini API key
- PostgreSQL, if required by your application configuration

### 1. Clone the Repository

```bash
git clone https://github.com/vishalbharti585/scalable-document-qa-rag.git
cd scalable-document-qa-rag
```

### 2. Create a Virtual Environment

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root if your application uses environment variables.

Example:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Add database configuration only if your application requires it:

```env
DATABASE_URL=your_database_connection_string
```

Use the exact environment variable names expected by your code. Never commit your actual API key, database credentials, or other secrets to GitHub.

### 5. Run the Application

If your Flask entry point is `app.py`:

```bash
python app.py
```

Alternatively, if your project uses Flask's command-line interface:

```bash
flask --app app run --debug
```

Open the local URL printed in your terminal, commonly `http://127.0.0.1:5000`, if that is the port configured by your application.

## 🧪 Example Usage

1. Open the application.
2. Upload a supported document.
3. Wait for document processing and indexing to finish.
4. Enter a question related to the uploaded content.
5. Review the generated answer and any available source references.

**Example questions:**

- What is solar energy?
- Explain the working principle of wind energy.
- What are the main advantages of renewable energy?
- Summarize the important concepts discussed in this document.

Answers depend on the content of the uploaded document and the retrieval quality.

## 🎯 Project Objectives

- Build a practical application using Retrieval-Augmented Generation.
- Enable semantic retrieval from document content.
- Integrate a Large Language Model with a vector-search pipeline.
- Explore document processing, embeddings, chunking, and similarity search.
- Develop a full-stack AI application with a web interface.
- Improve the reliability of document-grounded question answering.

## 🔐 Security Considerations

- Store API keys and database credentials in environment variables.
- Exclude `.env` and other secret files from version control.
- Validate uploaded files and restrict unsupported file types.
- Apply appropriate file-size limits and error handling.
- Avoid storing confidential documents in a public repository.
- Configure authentication and access controls if the application is publicly deployed.
- Review hosting-provider storage and logging policies before deploying user documents.

## ⚠️ Limitations

- Answer quality depends on document extraction, chunking, retrieval, and the language model.
- Relevant information may be missed if the correct document chunks are not retrieved.
- The language model may generate inaccurate information if the retrieved context is insufficient.
- Processing time depends on document size, embedding generation, and API response times.
- Availability and usage may depend on the configured hosting provider and Gemini API limits.

## 🚀 Future Enhancements

- Improve retrieval quality through chunking and embedding evaluation.
- Add document-level filtering and more advanced metadata search.
- Expand support for document formats.
- Improve answer-grounding checks and handling of questions with insufficient evidence.
- Add automated tests for retrieval accuracy and answer faithfulness.
- Enhance document and conversation management.
- Add production monitoring, authentication, and deployment automation.

## 👨‍💻 Author

**Vishal Bharti**

B.Tech — Computer Science and Engineering

Interested in Software Engineering, Generative AI, Backend Development, and Retrieval-Augmented Generation.

## 📄 License

Choose and add a license before publishing if you intend to permit others to reuse or modify this project. For example, you can use the MIT License by adding a `LICENSE` file with its full text.

---

⭐ If you find this project interesting, consider starring the repository on GitHub.
