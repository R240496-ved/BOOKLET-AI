"""
RAG Engine - Retrieval Augmented Generation
Handles: chunking, embedding, FAISS indexing, and retrieval.
Designed to be replaceable with any vector DB in the future.
"""

import numpy as np

# Lazy imports to avoid startup overhead
_embedding_model = None
_faiss = None


def _get_faiss():
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss
    return _faiss


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        import os
        import logging
        
        # Suppress harmless "UNEXPECTED" and "MISSING" warnings from transformers
        logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
        
        # Suppress HF Hub unauthenticated request warnings if not provided
        if not os.getenv("HF_TOKEN"):
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        from sentence_transformers import SentenceTransformer
        
        # Load model using local cache to avoid constant downloading
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
    return _embedding_model


# ─────────────────────────────────────────────
# CHUNKING
# ─────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """
    Split text into overlapping chunks for embedding.
    Uses word-level splitting to preserve semantic boundaries.
    """
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap  # slide forward with overlap

    return chunks


# ─────────────────────────────────────────────
# EMBEDDING
# ─────────────────────────────────────────────

def embed_chunks(chunks: list[str]) -> np.ndarray:
    """
    Generate embeddings for a list of text chunks.
    Returns a numpy array of shape (n_chunks, embedding_dim).
    """
    model = _get_embedding_model()
    embeddings = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.astype("float32")


# ─────────────────────────────────────────────
# FAISS INDEX MANAGEMENT
# ─────────────────────────────────────────────

def build_faiss_index(embeddings: np.ndarray):
    """
    Build a FAISS flat L2 index from embeddings.
    Returns the index object.
    (Replaceable with IVF, HNSW, or remote vector DB later)
    """
    faiss = _get_faiss()
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


def retrieve_top_k(query: str, chunks: list[str], faiss_index, k: int = 5) -> list[str]:
    """
    Given a query, retrieve the top-k most relevant chunks.
    Returns a list of chunk strings.
    """
    model = _get_embedding_model()
    query_embedding = model.encode([query], convert_to_numpy=True).astype("float32")

    distances, indices = faiss_index.search(query_embedding, k)

    results = []
    for idx in indices[0]:
        if 0 <= idx < len(chunks):
            results.append(chunks[idx])

    return results


# ─────────────────────────────────────────────
# PIPELINE HELPER: Build full RAG store
# ─────────────────────────────────────────────

def build_rag_store(text: str) -> dict:
    """
    Full pipeline: text → chunks → embeddings → FAISS index.
    Returns a dict with all components for session state storage.
    """
    chunks = chunk_text(text)

    if not chunks:
        return {"chunks": [], "embeddings": None, "index": None}

    embeddings = embed_chunks(chunks)
    index = build_faiss_index(embeddings)

    return {
        "chunks": chunks,
        "embeddings": embeddings,
        "index": index,
    }
