import os
import pickle
import logging
from pathlib import Path
from sys import path as sys_path

sys_path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models.schemas import RetrievedChunk
from corpus.loader import load_corpus
from config import settings

logger = logging.getLogger(__name__)


class CorpusIndex:
    """
    TF-IDF index over all corpus chunks.
    Built once at startup, cached to disk, reused for all queries.
    This is the Flyweight Pattern — expensive object built once, shared everywhere.
    """

    def __init__(self):
        self.chunks: list[RetrievedChunk] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.tfidf_matrix = None  # sparse matrix (n_chunks x n_terms)
        self._loaded = False

    def build(self, data_dir: str, cache_path: str) -> None:
        """Load corpus and build TF-IDF index. Uses cache if available."""
        cache_file = Path(cache_path)

        # Try loading from cache first
        if cache_file.exists():
            try:
                logger.info(f"Loading TF-IDF index from cache: {cache_file}")
                with open(cache_file, 'rb') as f:
                    cached = pickle.load(f)
                self.chunks = cached['chunks']
                self.vectorizer = cached['vectorizer']
                self.tfidf_matrix = cached['tfidf_matrix']
                self._loaded = True
                logger.info(f"Cache loaded: {len(self.chunks)} chunks")
                return
            except Exception as e:
                logger.warning(f"Cache load failed, rebuilding: {e}")

        # Build from scratch
        logger.info("Building TF-IDF index from corpus...")
        self.chunks = load_corpus(data_dir)

        if not self.chunks:
            raise RuntimeError(f"No chunks loaded from {data_dir}")

        texts = [chunk.content for chunk in self.chunks]

        self.vectorizer = TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 2),      # unigrams + bigrams for better matching
            stop_words='english',
            min_df=1,
            sublinear_tf=True,       # log normalization — better for long docs
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        self._loaded = True

        logger.info(f"Index built: {len(self.chunks)} chunks, "
                    f"{self.tfidf_matrix.shape[1]} terms")

        # Save to cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'chunks': self.chunks,
                    'vectorizer': self.vectorizer,
                    'tfidf_matrix': self.tfidf_matrix,
                }, f)
            logger.info(f"Index cached to {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to cache index: {e}")

    def search(
        self,
        query: str,
        company_filter: str | None = None,
        top_k: int = 20,
    ) -> list[RetrievedChunk]:
        """
        TF-IDF search with optional company filter.
        Returns top_k chunks sorted by score descending.
        """
        if not self._loaded:
            raise RuntimeError("Index not built. Call build() first.")

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Apply company filter — only search relevant company's docs
        if company_filter:
            for i, chunk in enumerate(self.chunks):
                if chunk.company != company_filter:
                    scores[i] = 0.0

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                chunk = self.chunks[idx].model_copy()
                chunk.score = float(scores[idx])
                results.append(chunk)

        return results


# Singleton — built once, used everywhere
_index: CorpusIndex | None = None


def get_index() -> CorpusIndex:
    """Get or build the global corpus index."""
    global _index
    if _index is None:
        _index = CorpusIndex()
        _index.build(
            data_dir=settings.CORPUS_DIR,
            cache_path=settings.INDEX_CACHE,
        )
    return _index