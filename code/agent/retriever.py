import logging
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sentence_transformers import SentenceTransformer

from models.schemas import RetrievedChunk
from corpus.index import get_index
from config import settings

logger = logging.getLogger(__name__)

# Lazy-loaded — only instantiated once on first retrieve() call
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading sentence-transformer model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded.")
    return _model


def _semantic_rerank(
    query: str,
    candidates: list[RetrievedChunk],
    top_k: int,
) -> list[RetrievedChunk]:
    """
    Rerank candidates using cosine similarity of sentence embeddings.
    This catches semantic matches that TF-IDF misses due to vocabulary mismatch.
    E.g. 'card compromised' vs 'unauthorized access' — different words, same meaning.
    """
    if not candidates:
        return []

    model = _get_model()

    # Encode query and all candidate chunks
    texts = [c.content for c in candidates]
    query_emb = model.encode(query, normalize_embeddings=True)
    chunk_embs = model.encode(texts, normalize_embeddings=True, batch_size=32)

    # Cosine similarity (embeddings are normalized so dot product = cosine sim)
    scores = np.dot(chunk_embs, query_emb)

    # Attach scores and sort
    scored = []
    for chunk, score in zip(candidates, scores):
        reranked = chunk.model_copy()
        reranked.score = float(score)
        scored.append(reranked)

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


def retrieve(
    query: str,
    company: str | None = None,
    top_k_tfidf: int | None = None,
    top_k_final: int | None = None,
) -> list[RetrievedChunk]:
    """
    Two-stage retrieval pipeline:
      Stage 1: TF-IDF keyword match → broad candidates (top 20)
      Stage 2: Semantic rerank → precise results (top 3)

    Returns top_k_final chunks sorted by semantic score descending.
    Returns empty list if no relevant chunks found above threshold.
    """
    top_k_tfidf = top_k_tfidf or settings.TOP_K_TFIDF
    top_k_final = top_k_final or settings.TOP_K_FINAL

    # Stage 1: TF-IDF broad retrieval
    index = get_index()
    candidates = index.search(
        query=query,
        company_filter=company,
        top_k=top_k_tfidf,
    )

    if not candidates:
        logger.info(f"No TF-IDF candidates for query: {query[:50]}")
        return []

    # Stage 2: Semantic rerank
    reranked = _semantic_rerank(query, candidates, top_k=top_k_final)

    # Log top result for debugging
    if reranked:
        logger.debug(
            f"Top chunk: score={reranked[0].score:.3f} | {reranked[0].source[:50]}"
        )

    return reranked