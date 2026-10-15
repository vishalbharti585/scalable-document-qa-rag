import pytest
from backend.app.services.chunking.splitter import TextSplitter
from backend.app.services.vector_store.faiss_manager import FAISSIndexManager
from backend.app.services.embeddings.provider import DeterministicMockEmbeddingProvider
from backend.app.services.generation.llm_provider import DeterministicMockLLMProvider
from backend.app.services.retrieval.rag_service import RAGService


class TestConfig:
    TOP_K = 6
    SIMILARITY_THRESHOLD = 0.15
    FAISS_INDEX_DIR = None  # Will be set in fixture
    EMBEDDING_PROVIDER = "mock"
    EMBEDDING_API_KEY = ""
    EMBEDDING_MODEL = ""
    LLM_PROVIDER = "mock"
    LLM_API_KEY = ""
    LLM_MODEL = ""
    LLM_TEMPERATURE = 0.0


@pytest.fixture
def test_rag_env(tmp_path):
    cfg = TestConfig()
    cfg.FAISS_INDEX_DIR = tmp_path / "test_faiss"
    cfg.FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)

    splitter = TextSplitter(chunk_size=400, chunk_overlap=80)
    embedder = DeterministicMockEmbeddingProvider(dimension=768)
    faiss_mgr = FAISSIndexManager(cfg.FAISS_INDEX_DIR)
    service = RAGService(cfg)
    return cfg, splitter, embedder, faiss_mgr, service


def test_abbreviation_and_number_protection(test_rag_env):
    """Verify sentence splitter does not split Q1., e.g., or numbers prematurely."""
    _, splitter, _, _, _ = test_rag_env
    text = "Q1. What is cut-in speed? e.g. for wind turbines it is typically 3.5 m/s. It defines initial generation."
    chunks = splitter._split_text(text, splitter.separators)
    assert len(chunks) >= 1
    # Check that 'Q1' was not orphaned
    assert any("Q1. What is cut-in speed?" in c for c in chunks)


def test_empty_collection_scope_isolation(test_rag_env):
    """Verify selecting an empty collection (empty document_filter_ids list) returns 0 results."""
    cfg, splitter, embedder, faiss_mgr, service = test_rag_env
    user_id = "test_user_empty_col"

    # Index a document
    doc_text = "Solar panels convert solar irradiance into direct current electricity using photovoltaic cells."
    pages = [{"page_number": 1, "text": doc_text}]
    chunks = splitter.split_pages(pages, "doc_101", user_id, "solar.txt", collection_id="col_solar")
    embs = embedder.embed_documents([c["content"] for c in chunks])
    faiss_mgr.add_vectors(user_id, chunks, embs, embedder.dimension)

    # Search with empty document_filter_ids (representing an empty collection)
    q_vec = embedder.embed_query("solar panels")
    hits = faiss_mgr.search(user_id, q_vec, "solar panels", top_k=4, document_filter_ids=[])
    assert hits == [], "Empty collection scope must yield exactly 0 hits"

    # When querying RAG service with empty document filter
    res = service.query(user_id, "solar panels", document_filter_ids=[])
    assert "could not be found in the available documents" in res["answer"].lower()
    assert len(res["citations"]) == 0


def test_calibrated_similarity_scores(test_rag_env):
    """Verify similarity scores are strictly within [0.0, 1.0]."""
    cfg, splitter, embedder, faiss_mgr, _ = test_rag_env
    user_id = "test_user_calib"

    doc_text = "Wind turbine rotor blades capture kinetic energy from ambient airflow."
    pages = [{"page_number": 1, "text": doc_text}]
    chunks = splitter.split_pages(pages, "doc_201", user_id, "wind.txt")
    embs = embedder.embed_documents([c["content"] for c in chunks])
    faiss_mgr.add_vectors(user_id, chunks, embs, embedder.dimension)

    # Exact query matching document to trigger maximum lexical boost
    q_vec = embedder.embed_query("Wind turbine rotor blades capture kinetic energy")
    hits = faiss_mgr.search(user_id, q_vec, "Wind turbine rotor blades capture kinetic energy", top_k=4)
    assert len(hits) >= 1
    for h in hits:
        assert 0.0 <= h["score"] <= 1.0, f"Score {h['score']} must be in [0.0, 1.0]"


def test_chunk_diversity_and_deduplication(test_rag_env):
    """Verify that near-duplicate chunks are deduplicated in candidate selection."""
    cfg, splitter, embedder, faiss_mgr, _ = test_rag_env
    user_id = "test_user_dedup"

    # Ingest 3 chunks where 2 are almost identical
    c1 = "Geothermal heat pumps utilize constant subsurface earth temperatures for space conditioning."
    c2 = "Geothermal heat pumps utilize constant subsurface earth temperatures for space conditioning."
    c3 = "Biomass gasification converts organic matter into syngas comprising carbon monoxide and hydrogen."

    chunks = [
        {"id": "c1", "document_id": "d1", "chunk_index": 0, "page_number": 1, "content": c1, "source_filename": "geo.txt"},
        {"id": "c2", "document_id": "d1", "chunk_index": 1, "page_number": 1, "content": c2, "source_filename": "geo.txt"},
        {"id": "c3", "document_id": "d2", "chunk_index": 0, "page_number": 1, "content": c3, "source_filename": "bio.txt"},
    ]
    embs = embedder.embed_documents([c["content"] for c in chunks])
    faiss_mgr.add_vectors(user_id, chunks, embs, embedder.dimension)

    q_vec = embedder.embed_query("Geothermal heat pumps")
    hits = faiss_mgr.search(user_id, q_vec, "Geothermal heat pumps", top_k=2)
    # Duplicate chunk c2 should be suppressed by diversity Jaccard check
    retrieved_ids = [h["chunk_id"] for h in hits]
    assert not (("c1" in retrieved_ids) and ("c2" in retrieved_ids)), "Near-duplicate chunk should be deduplicated"


def test_active_citation_evidence_ranking(test_rag_env):
    """Verify active citation verification assigns evidence strength and sorts key evidence first."""
    cfg, splitter, embedder, faiss_mgr, service = test_rag_env
    user_id = "test_user_citations"

    c1 = "The Betz limit establishes that the theoretical maximum aerodynamic efficiency for any wind turbine is 59.3%."
    c2 = "Solar photovoltaic inverters convert direct current into alternating current."
    pages = [{"page_number": 1, "text": c1}, {"page_number": 2, "text": c2}]
    chunks = splitter.split_pages(pages, "doc_301", user_id, "wind_solar.txt")
    embs = embedder.embed_documents([c["content"] for c in chunks])
    faiss_mgr.add_vectors(user_id, chunks, embs, embedder.dimension)

    res = service.query(user_id, "What is the Betz limit aerodynamic efficiency?")
    assert len(res["citations"]) >= 1
    # Primary citation should be the Betz limit chunk
    top_cit = res["citations"][0]
    assert "Betz limit" in top_cit["supporting_excerpt"]
    assert top_cit["evidence_strength"] == "primary"


def test_filter_running_headers_and_footers():
    """Verify running headers, footers, and page numbers repeating across >=40% pages are stripped."""
    from backend.app.services.ingestion.extractor import TextExtractor

    raw_pages = [
        {"page_number": 1, "text": "COURSE 101: RENEWABLE ENERGY\nSolar photovoltaics absorb photons.\nPage 1 of 4"},
        {"page_number": 2, "text": "COURSE 101: RENEWABLE ENERGY\nWind turbines convert aerodynamic lift.\nPage 2 of 4"},
        {"page_number": 3, "text": "COURSE 101: RENEWABLE ENERGY\nHydroelectric dams exploit potential energy.\nPage 3 of 4"},
        {"page_number": 4, "text": "COURSE 101: RENEWABLE ENERGY\nGeothermal taps subterranean heat reservoirs.\nPage 4 of 4"},
    ]

    cleaned = TextExtractor.filter_running_headers_and_footers(raw_pages)
    assert len(cleaned) == 4
    for p in cleaned:
        assert "COURSE 101: RENEWABLE ENERGY" not in p["text"]
        assert "Page" not in p["text"]
    assert "Solar photovoltaics absorb photons." in cleaned[0]["text"]
    assert "Wind turbines convert aerodynamic lift." in cleaned[1]["text"]


def test_multi_document_comparison_retrieval(test_rag_env):
    """Verify multi-document query retrieves and attributes chunks across distinct documents."""
    cfg, splitter, embedder, faiss_mgr, service = test_rag_env
    user_id = "test_user_multidoc"

    doc1_text = "Solar PV systems use silicon semiconductors to convert photons into electrical voltage."
    doc2_text = "Wind power systems use aerodynamic airfoil blades to spin a synchronous generator shaft."

    chunks1 = splitter.split_pages([{"page_number": 1, "text": doc1_text}], "doc_solar", user_id, "solar_guide.pdf")
    chunks2 = splitter.split_pages([{"page_number": 1, "text": doc2_text}], "doc_wind", user_id, "wind_guide.pdf")

    all_chunks = chunks1 + chunks2
    embs = embedder.embed_documents([c["content"] for c in all_chunks])
    faiss_mgr.add_vectors(user_id, all_chunks, embs, embedder.dimension)

    res = service.query(user_id, "Compare solar PV and wind power mechanisms", top_k=6)
    assert len(res["citations"]) >= 2
    cited_docs = {c["source_filename"] for c in res["citations"]}
    assert "solar_guide.pdf" in cited_docs
    assert "wind_guide.pdf" in cited_docs


def test_faiss_persistence_across_restarts(test_rag_env):
    """Verify that vector indices and metadata manifests reload correctly in fresh manager instances."""
    cfg, splitter, embedder, faiss_mgr, _ = test_rag_env
    user_id = "test_user_restart"

    text = "Tidal barrage systems harness gravitational potential energy between high and low ocean tides."
    chunks = splitter.split_pages([{"page_number": 1, "text": text}], "doc_tidal", user_id, "tidal.txt")
    embs = embedder.embed_documents([c["content"] for c in chunks])
    faiss_mgr.add_vectors(user_id, chunks, embs, embedder.dimension)

    # Simulate restart by instantiating a completely new manager with the same index directory
    restarted_manager = FAISSIndexManager(cfg.FAISS_INDEX_DIR)
    q_vec = embedder.embed_query("tidal barrage systems")
    hits = restarted_manager.search(user_id, q_vec, "tidal barrage systems", top_k=2)

    assert len(hits) == 1
    assert hits[0]["document_id"] == "doc_tidal"
    assert "Tidal barrage systems" in hits[0]["content"]


def test_unsupported_question_grounding_refusal(test_rag_env):
    """Verify that an unsupported question with no relevant document grounding yields a graceful refusal."""
    cfg, splitter, embedder, faiss_mgr, service = test_rag_env
    user_id = "test_user_refusal"

    text = "Anaerobic digestion decomposes biodegradable waste in the absence of oxygen to produce biogas."
    chunks = splitter.split_pages([{"page_number": 1, "text": text}], "doc_bio", user_id, "biogas.txt")
    embs = embedder.embed_documents([c["content"] for c in chunks])
    faiss_mgr.add_vectors(user_id, chunks, embs, embedder.dimension)

    # Completely unrelated question with no lexical or semantic overlap
    res = service.query(user_id, "Explain quantum entanglement in superconducting qubits")
    # In strict grounding mode, either no chunks exceed the threshold or the answer acknowledges missing evidence
    assert ("could not be found" in res["answer"].lower() or 
            "does not contain" in res["answer"].lower() or 
            "not mentioned" in res["answer"].lower() or
            len(res["citations"]) == 0)


def test_scanned_pdf_detection_raises_informative_error(tmp_path):
    """Verify that a PDF without an extractable text layer raises a user-actionable OCR error."""
    from pypdf import PdfWriter
    from backend.app.services.ingestion.extractor import TextExtractor

    # Create an empty/image-only PDF with 1 blank page
    blank_pdf = tmp_path / "blank_scanned.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(blank_pdf, "wb") as f:
        writer.write(f)

    with pytest.raises(ValueError) as excinfo:
        TextExtractor.extract_from_file(blank_pdf, ".pdf")
    
    msg = str(excinfo.value)
    assert "scanned image-only" in msg
    assert "OCR" in msg


def test_markdown_parser_sanitization_rules():
    """Verify frontend/js/markdown.js exists and enforces HTML escaping before Markdown rendering."""
    from pathlib import Path
    markdown_js_path = Path("frontend/js/markdown.js")
    assert markdown_js_path.exists(), "frontend/js/markdown.js must exist"

    content = markdown_js_path.read_text(encoding="utf-8")
    assert "escapeHtml" in content, "MarkdownRenderer must have escapeHtml"
    assert "&lt;" in content and "&gt;" in content, "Must escape tag brackets to prevent XSS"
    assert "markdown-table" in content, "Must render styled markdown tables"
    assert "code-block-wrapper" in content, "Must render fenced code blocks"


def test_context_depth_control_8_12_16_20(test_rag_env):
    """Verify that Context Depth settings of 8, 12, 16, and 20 chunks strictly control retrieved chunk limits."""
    cfg, splitter, embedder, faiss_mgr, service = test_rag_env
    user_id = "test_user_depth"

    # Create 25 distinct chunks on renewable energy to test top_k boundaries
    pages = []
    for i in range(25):
        pages.append({
            "page_number": i + 1,
            "text": f"Section {i+1}: Renewable energy source #{i+1} operates with specific technical characteristics and conversion efficiency."
        })
    chunks = splitter.split_pages(pages, "doc_depth", user_id, "depth_test.txt")
    embs = embedder.embed_documents([c["content"] for c in chunks])
    faiss_mgr.add_vectors(user_id, chunks, embs, embedder.dimension)

    for requested_k in [8, 12, 16, 20]:
        res = service.query(user_id, "Renewable energy source technical characteristics", top_k=requested_k)
        retrieved_count = len(res["citations"])
        assert retrieved_count == requested_k, f"Requested {requested_k} chunks, but got {retrieved_count}"
        assert res["retrieved_chunks_count"] == requested_k
        assert res["metrics"]["chunks_retrieved"] == requested_k


def test_node_nested_markdown_rendering_execution():
    """Verify frontend/js/markdown.js executes in Node.js and renders nested lists with zero asterisks leaking."""
    import subprocess
    import shutil

    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js not installed in environment")

    # Run scratch/test_node_markdown.js which tests nested lists, headings, tables, and code blocks
    proc = subprocess.run([node_bin, "scratch/test_node_markdown.js"], capture_output=True, text=True)
    assert proc.returncode == 0, f"Node markdown tests failed with output:\n{proc.stdout}\n{proc.stderr}"
    assert "ALL MARKDOWN TESTS PASSED!" in proc.stdout
    assert "[PASS] No literal asterisks in bullet list" in proc.stdout
    assert "[PASS] Nested unordered list inside ordered list" in proc.stdout


def test_citation_metadata_alignment(test_rag_env):
    """Verify that citation filenames, page numbers, and excerpts correspond exactly to the source chunks."""
    cfg, splitter, embedder, faiss_mgr, service = test_rag_env
    user_id = "test_user_align"

    p1 = "Cut-in speed is the minimum wind speed at which wind turbine blades overcome inertia and begin producing power."
    p2 = "Rated speed is the wind speed at which the wind turbine reaches its maximum design electrical output capacity."
    pages = [{"page_number": 5, "text": p1}, {"page_number": 12, "text": p2}]
    chunks = splitter.split_pages(pages, "doc_align", user_id, "wind_spec.pdf")
    embs = embedder.embed_documents([c["content"] for c in chunks])
    faiss_mgr.add_vectors(user_id, chunks, embs, embedder.dimension)

    res = service.query(user_id, "What is cut-in speed?", top_k=2)
    assert len(res["citations"]) >= 1
    cit = res["citations"][0]

    assert cit["document_name"] == "wind_spec.pdf"
    assert cit["source_filename"] == "wind_spec.pdf"
    assert cit["page_number"] in [5, 12]
    assert "minimum wind speed" in cit["supporting_excerpt"]



