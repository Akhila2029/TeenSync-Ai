"""
app/services/rag_service.py
Retrieval-Augmented Generation (RAG) Service for TeenSync.

Pipeline:
1. load_documents()     → Read all .txt files from data/mental_health_docs/
2. create_embeddings()  → Encode documents using sentence-transformers (all-MiniLM-L6-v2)
3. build_faiss_index()  → Build + persist FAISS index (runs once at startup)
4. retrieve_context()   → Given user query, find top-k relevant document chunks

The FAISS index is cached in-memory as a module-level singleton so it is
never rebuilt per request — only the lightweight query encoding runs each time.

Graceful degradation:
- If sentence-transformers is not installed → RAG is disabled, returns []
- If faiss-cpu is not installed             → RAG is disabled, returns []
- If no documents found                     → RAG is disabled, returns []
"""
import logging
import os
import re
from pathlib import Path
from typing import Optional

import numpy as np

from app.utils.vector_store import VectorStore

logger = logging.getLogger(__name__)

# ── sentence-transformers import with graceful fallback ───────────────────────
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning(
        "sentence-transformers not installed. RAG will be disabled. "
        "Install with: pip install sentence-transformers"
    )

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent.parent  # teensync-backend/
_DOCS_DIR = _BASE_DIR / "data" / "mental_health_docs"
_INDEX_PATH = str(_BASE_DIR / "data" / "faiss_index.bin")
_META_PATH = str(_BASE_DIR / "data" / "faiss_meta.npy")

# ── Model configuration ───────────────────────────────────────────────────────
_MODEL_NAME = "all-MiniLM-L6-v2"   # ~80MB, fast, runs fully offline after first download
_EMBEDDING_DIM = 384               # Output dimension of all-MiniLM-L6-v2
_CHUNK_SIZE = 400                  # Max words per document chunk
_CHUNK_OVERLAP = 50                # Words of overlap between consecutive chunks

# ── Module-level singletons (load once, reuse forever) ───────────────────────
_encoder: Optional[object] = None   # SentenceTransformer model
_vector_store: Optional[VectorStore] = None  # FAISS index wrapper
_rag_ready: bool = False            # Set to True once index is built/loaded


# ── Document Loading ──────────────────────────────────────────────────────────

def load_documents() -> list[dict]:
    """
    Read all .txt files from the mental_health_docs folder.

    Returns a list of document dicts:
        {"source": filename, "content": full_text, "category": str}
    """
    documents = []

    if not _DOCS_DIR.exists():
        logger.warning("Documents directory not found: %s", _DOCS_DIR)
        return []

    for txt_file in sorted(_DOCS_DIR.glob("*.txt")):
        try:
            content = txt_file.read_text(encoding="utf-8").strip()
            if not content:
                continue

            # Extract CATEGORY line if present (first or second line)
            category = _extract_field(content, "CATEGORY")
            topic = _extract_field(content, "TOPIC")

            documents.append({
                "source": txt_file.name,
                "topic": topic or txt_file.stem.replace("_", " ").title(),
                "category": category or "",
                "content": content,
            })
            logger.debug("Loaded document: %s (%d chars)", txt_file.name, len(content))

        except Exception as exc:
            logger.error("Failed to read %s: %s", txt_file.name, exc)

    logger.info("Loaded %d mental health documents.", len(documents))
    return documents


def _extract_field(text: str, field: str) -> str:
    """Extract a metadata field like 'TOPIC: <value>' from document header."""
    match = re.search(rf"^{field}:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """
    Split a long document into overlapping word-based chunks.

    Overlap ensures that a relevant sentence near a chunk boundary
    still appears in at least one retrieved chunk.
    """
    words = text.split()
    if len(words) <= chunk_size:
        return [text]  # Document small enough to be one chunk

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap  # Step forward with overlap

    return chunks


# ── Embeddings ────────────────────────────────────────────────────────────────

def create_embeddings(chunks: list[str]) -> np.ndarray:
    """
    Encode a list of text chunks into dense embeddings.

    Args:
        chunks: List of strings to embed

    Returns:
        numpy array of shape (len(chunks), 384), dtype float32
    """
    global _encoder

    if not ST_AVAILABLE:
        return np.array([], dtype=np.float32)

    # Load model on first call — cached in module-level variable
    if _encoder is None:
        logger.info("Loading sentence-transformers model: %s ...", _MODEL_NAME)
        _encoder = SentenceTransformer(_MODEL_NAME)
        logger.info("Model loaded successfully.")

    embeddings = _encoder.encode(  # type: ignore[attr-defined]
        chunks,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,   # L2-normalize for cosine similarity
        convert_to_numpy=True,
    )
    return embeddings.astype(np.float32)


# ── FAISS Index Building ──────────────────────────────────────────────────────

def build_faiss_index(force_rebuild: bool = False) -> bool:
    """
    Build the FAISS index from documents and persist it to disk.

    - If a cached index already exists on disk and force_rebuild=False,
      load the cached version (fast startup).
    - Otherwise, load documents → chunk → embed → index → save.

    Returns:
        True if the index is ready for queries, False otherwise.
    """
    global _vector_store, _rag_ready

    if not ST_AVAILABLE:
        logger.warning("RAG disabled: sentence-transformers not available.")
        return False

    _vector_store = VectorStore(dim=_EMBEDDING_DIM)

    # ── Try loading from disk first (cache) ──────────────────────────────────
    if not force_rebuild and _vector_store.load(_INDEX_PATH, _META_PATH):
        logger.info(
            "RAG index loaded from cache (%d vectors). RAG is ready.",
            _vector_store.total_vectors,
        )
        _rag_ready = True
        return True

    # ── Build from scratch ────────────────────────────────────────────────────
    logger.info("Building FAISS index from documents...")

    documents = load_documents()
    if not documents:
        logger.warning("No documents found. RAG disabled.")
        return False

    all_chunks: list[str] = []
    all_metadata: list[dict] = []

    for doc in documents:
        chunks = _chunk_text(doc["content"])
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append({
                "source": doc["source"],
                "topic": doc["topic"],
                "category": doc["category"],
                "content": chunk,
                "chunk_id": i,
            })

    logger.info("Total chunks to embed: %d", len(all_chunks))

    embeddings = create_embeddings(all_chunks)
    if embeddings.size == 0:
        logger.error("Embedding failed. RAG disabled.")
        return False

    _vector_store.add(embeddings, all_metadata)

    # Persist to disk for fast future startups
    _vector_store.save(_INDEX_PATH, _META_PATH)
    logger.info("FAISS index built and saved. RAG is ready.")

    _rag_ready = True
    return True


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve_context(query: str, top_k: int = 4) -> list[dict]:
    """
    Retrieve the top-k most relevant document chunks for a user query.

    Args:
        query:  The user's message (will be embedded and searched against index)
        top_k:  Number of chunks to retrieve (default 4)

    Returns:
        List of dicts with: source, topic, content, score (L2 distance)
        Returns [] if RAG is not available or index is empty.
    """
    global _vector_store, _rag_ready

    if not _rag_ready or _vector_store is None or not _vector_store.is_ready:
        return []

    if not ST_AVAILABLE or _encoder is None:
        return []

    # Embed the user query (single vector, very fast ~5ms)
    query_embedding = _encoder.encode(  # type: ignore[attr-defined]
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype(np.float32)[0]

    results = _vector_store.search(query_embedding, top_k=top_k)

    # Deduplicate by source (keep best chunk per source file)
    seen_sources: set[str] = set()
    deduplicated: list[dict] = []
    for r in results:
        src = r.get("source", "")
        if src not in seen_sources:
            seen_sources.add(src)
            deduplicated.append(r)

    logger.debug(
        "Retrieved %d chunks for query: %.50s...",
        len(deduplicated), query
    )
    return deduplicated


# ── Status ────────────────────────────────────────────────────────────────────

def get_rag_status() -> dict:
    """Return a status dict for health checks and debug endpoints."""
    return {
        "rag_ready": _rag_ready,
        "sentence_transformers_available": ST_AVAILABLE,
        "faiss_available": _vector_store is not None,
        "total_vectors": _vector_store.total_vectors if _vector_store else 0,
        "model": _MODEL_NAME if ST_AVAILABLE else None,
        "docs_dir": str(_DOCS_DIR),
        "index_path": _INDEX_PATH,
    }


# ── Startup initializer (called from main.py) ─────────────────────────────────

def initialize_rag() -> None:
    """
    Initialize the RAG system at application startup.
    Blocks briefly while building/loading the FAISS index.
    Should be called once inside the FastAPI lifespan event.
    """
    logger.info("Initializing RAG pipeline...")
    success = build_faiss_index(force_rebuild=False)
    if success:
        logger.info("✅ RAG pipeline ready.")
    else:
        logger.warning(
            "⚠️  RAG pipeline unavailable. Chatbot will fall back to rule-based responses."
        )
