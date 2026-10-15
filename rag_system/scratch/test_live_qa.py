import sys
import os
sys.path.insert(0, os.path.abspath("."))

from backend.app import create_app
from backend.app.services.retrieval.rag_service import RAGService
import subprocess

app = create_app("development")
with app.app_context():
    rag = RAGService(app.config)
    res = rag.query(
        user_id="8d3af7ad-684d-4189-8a13-bace1898b741",
        question="What are the installation environments and deployment types for solar photovoltaic systems? List them with details.",
        top_k=12
    )
    print("=== RAW LLM ANSWER ===")
    print(res["answer"])
    print("\n=== CITATIONS ===")
    for c in res["citations"][:4]:
        print(f"- {c['document_name']} (Page {c['page_number']}) [{c['evidence_strength']}]: {c['similarity_score']*100:.1f}%")

    with open("scratch/temp_answer.md", "w", encoding="utf-8") as f:
        f.write(res["answer"])

# Run node parser to test actual HTML rendered
test_js = """
const fs = require('fs');
const MarkdownRenderer = require('./frontend/js/markdown.js');
const md = fs.readFileSync('scratch/temp_answer.md', 'utf8');
const html = MarkdownRenderer.render(md);
console.log('\\n=== RENDERED HTML ===');
console.log(html);
"""
with open("scratch/run_parse.js", "w", encoding="utf-8") as f:
    f.write(test_js)

proc = subprocess.run(["node", "scratch/run_parse.js"], capture_output=True, text=True)
print(proc.stdout)
if proc.stderr:
    print("STDERR:", proc.stderr)
