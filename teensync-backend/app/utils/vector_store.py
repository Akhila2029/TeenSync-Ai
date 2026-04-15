"""
app/utils/vector_store.py
FAISS Vector Store — handles index persistence and similarity search.

This module provides a lightweight wrapper around FAISS to:
- Save the built index to disk (avoids recomputing embeddings on restart)
- Load a previously saved index from disk
- Expose a VectorStore class that the RAG service can own as a singleton
"""
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── FAISS import with graceful fallback ──────────────────────────────────────
try:
    import faiss  # type: ignore
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning(
        "faiss-cpu not installed. RAG retrieval will be disabled. "
        "Install with: pip install faiss-cpu"
    )


class VectorStore:
    """
    A thin FAISS wrapper for storing and searching document embeddings.

    Usage:
        store = VectorStore(dim=384)
        store.add(embeddings, metadata_list)
        results = store.search(query_vector, top_k=4)
        store.save(path)
        store.load(path)
    """

    def __init__(self, dim: int = 384):
        """
        Args:
            dim: Embedding dimensionality. Default 384 matches all-MiniLM-L6-v2.
        """
        self.dim = dim
        self.index: Optional[object] = None       # FAISS index
        self.metadata: list[dict] = []            # Parallel list of doc metadata

        if FAISS_AVAILABLE:
            # IndexFlatL2 performs exact nearest-neighbor search using L2 distance.
            # For our small corpus (~10–50 docs), this is fast enough and needs no training.
            self.index = faiss.IndexFlatL2(dim)
            logger.info("FAISS IndexFlatL2 initialized (dim=%d).", dim)

    # ── Adding documents ────────────────────────────────────────────────────────

    def add(self, embeddings: np.ndarray, metadata: list[dict]) -> None:
        """
        Add document embeddings and their metadata to the store.

        Args:
            embeddings: 2D numpy array of shape (n_docs, dim), dtype float32
            metadata: Parallel list of dicts — each dict should have at least
                      {"source": str, "content": str, "chunk_id": int}
        """
        if not FAISS_AVAILABLE or self.index is None:
            return

        if len(embeddings) != len(metadata):
            raise ValueError("embeddings and metadata must have the same length.")

        # FAISS expects float32
        vecs = np.array(embeddings, dtype=np.float32)
        self.index.add(vecs)  # type: ignore[attr-defined]
        self.metadata.extend(metadata)
        logger.info("Added %d vectors. Total in index: %d.", len(embeddings), self.index.ntotal)  # type: ignore[attr-defined]

    # ── Searching ───────────────────────────────────────────────────────────────

    def search(self, query_vector: np.ndarray, top_k: int = 4) -> list[dict]:
        """
        Return the top-k most similar documents for a query embedding.

        Args:
            query_vector: 1D numpy array of shape (dim,), dtype float32
            top_k: Number of results to return

        Returns:
            List of metadata dicts with an additional "score" (L2 distance) key.
            Lower score = more similar.
        """
        if not FAISS_AVAILABLE or self.index is None or self.index.ntotal == 0:  # type: ignore[attr-defined]
            return []

        # FAISS requires a 2D query matrix
        query = np.array([query_vector], dtype=np.float32)
        k = min(top_k, self.index.ntotal)  # type: ignore[attr-defined]

        distances, indices = self.index.search(query, k)  # type: ignore[attr-defined]

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue  # FAISS returns -1 for unfilled slots
            result = dict(self.metadata[idx])
            result["score"] = float(dist)
            results.append(result)

        return results

    # ── Persistence ─────────────────────────────────────────────────────────────

    def save(self, index_path: str, meta_path: Optional[str] = None) -> None:
        """
        Persist the FAISS index to disk.

        Args:
            index_path: Path to write the FAISS binary (.bin file)
            meta_path:  Path to write metadata as numpy .npy file (optional)
        """
        if not FAISS_AVAILABLE or self.index is None:
            return

        Path(index_path).parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, index_path)  # type: ignore[attr-defined]
        logger.info("FAISS index saved to %s.", index_path)

        if meta_path:
            np.save(meta_path, np.array(self.metadata, dtype=object))
            logger.info("Metadata saved to %s.", meta_path)

    def load(self, index_path: str, meta_path: Optional[str] = None) -> bool:
        """
        Load a FAISS index from disk.

        Returns:
            True if loaded successfully, False otherwise.
        """
        if not FAISS_AVAILABLE:
            return False

        if not os.path.exists(index_path):
            logger.warning("FAISS index not found at %s.", index_path)
            return False

        try:
            self.index = faiss.read_index(index_path)  # type: ignore[attr-defined]
            logger.info(
                "FAISS index loaded from %s. Contains %d vectors.",
                index_path, self.index.ntotal,  # type: ignore[attr-defined]
            )

            if meta_path and os.path.exists(meta_path):
                self.metadata = list(np.load(meta_path, allow_pickle=True))
                logger.info("Metadata loaded: %d entries.", len(self.metadata))

            return True
        except Exception as exc:
            logger.error("Failed to load FAISS index: %s", exc)
            return False

    @property
    def is_ready(self) -> bool:
        """True if the index is initialized and loaded with at least one vector."""
        if not FAISS_AVAILABLE or self.index is None:
            return False
        return self.index.ntotal > 0  # type: ignore[attr-defined]

    @property
    def total_vectors(self) -> int:
        """Number of vectors currently stored."""
        if not FAISS_AVAILABLE or self.index is None:
            return 0
        return self.index.ntotal  # type: ignore[attr-defined]
