import urllib.request
import json
import os
import sys
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv
load_dotenv()

from backend.app import create_app
from backend.app.services.retrieval.rag_service import RAGService

app = create_app()
with app.app_context():
    service = RAGService(app.config)
    raw_hits = service.faiss_manager.search(
        user_id="8d3af7ad-684d-4189-8a13-bace1898b741",
        query_vector=service.embedding_provider.embed_query("wind energy"),
        query_text="wind energy",
        top_k=8,
        threshold=0.15
    )
    context_blocks = [
        f'<chunk id="source-{i+1}" source="{h["source_filename"]}" page="{h["page_number"]}">\n{h["content"]}\n</chunk>'
        for i, h in enumerate(raw_hits)
    ]
    
    new_system_prompt = """You are an intelligent, expert technical document assistant.
Your task is to answer the user's question or explain the requested topic thoroughly using ONLY the provided document context enclosed within the <document_context> tags.

Adhere strictly to the following instructions:
1. Provide a comprehensive, detailed, and well-structured answer that synthesizes ALL relevant facts, definitions, working principles, mechanisms, classifications, components, and practical considerations present across the provided context chunks.
2. Structure your answer using clear Markdown formatting with descriptive headings (###), organized bullet points, and bold key terms to explain concepts clearly.
3. When answering broad topic queries or concepts, provide a complete technical explanation covering all related points discussed in the document rather than a short 1-2 sentence summary.
4. Every factual statement must be grounded strictly in the provided document context. Do not invent or assume outside facts.
5. If the context does not contain enough information to address the query, state: "The requested information could not be found in the available documents."
6. The user interface automatically displays a separate verified sources panel with page numbers, so you do not need to append a raw references list at the end."""
    
    user_prompt = f"<document_context>\n" + "\n".join(context_blocks) + f"\n</document_context>\n\nTopic / Question: wind energy"
    
    key = os.getenv("LLM_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={key}"
    payload = {
        "system_instruction": {"parts": [{"text": new_system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode("utf-8"))
    print(data["candidates"][0]["content"]["parts"][0]["text"])
