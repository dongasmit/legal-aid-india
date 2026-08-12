"""
retrieval.py — Phase 3: Hybrid Retrieval & FlashRank Reranking
===============================================================
Combines Qdrant dense vector search (MiniLM) and sparse BM25 search
with RRF (Reciprocal Rank Fusion) and cross-encoder reranking (FlashRank).

Functions:
    hybrid_retrieve(query, top_k=20) -> list[dict]
    rerank(query, chunks, top_n=5) -> list[dict]
    retrieve_and_rerank(query, top_k=20, top_n=5) -> list[dict]

Standalone test:
    python3 retrieval.py "bail application IPC 302 grounds"
"""

import os
import sys
import time
import pickle
import logging
from typing import Optional

import bm25s
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from flashrank import Ranker, RerankRequest
from qdrant_client import QdrantClient
from qdrant_client.models import NamedSparseVector, SparseVector

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "jurisone_legal")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Load Models (Global Singletons) ───────────────────────────────────────────
log.info("Initializing Hybrid Retrieval Stack...")

_embedder: Optional[SentenceTransformer] = None
_reranker: Optional[Ranker] = None
_bm25_retriever: Optional[bm25s.BM25] = None
_qdrant_client: Optional[QdrantClient] = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        log.info("Loading SentenceTransformer (all-MiniLM-L6-v2)...")
        _embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _embedder


def get_reranker() -> Ranker:
    global _reranker
    if _reranker is None:
        log.info("Loading FlashRank cross-encoder model...")
        try:
            _reranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2")
        except Exception as e:
            log.warning(f"Defaulting FlashRank Ranker without model_name: {e}")
            _reranker = Ranker()
    return _reranker


def get_bm25_retriever() -> bm25s.BM25:
    global _bm25_retriever
    if _bm25_retriever is None:
        log.info("Loading BM25 model...")
        if os.path.exists("bm25_model"):
            try:
                _bm25_retriever = bm25s.BM25.load("bm25_model", load_corpus=False)
                log.info("Loaded BM25 model from directory 'bm25_model'.")
                return _bm25_retriever
            except Exception as e:
                log.warning(f"Could not load bm25_model directory: {e}")
        if os.path.exists("bm25_model.pkl"):
            try:
                with open("bm25_model.pkl", "rb") as f:
                    _bm25_retriever = pickle.load(f)
                log.info("Loaded BM25 model from pickle file 'bm25_model.pkl'.")
                return _bm25_retriever
            except Exception as e:
                log.warning(f"Could not load bm25_model.pkl: {e}")
        log.warning("BM25 model not found. Sparse retrieval will use exact-term fallback.")
    return _bm25_retriever


def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=QDRANT_URL, timeout=30)
    return _qdrant_client


# ── Query Sparse Vector Generator ──────────────────────────────────────────────

def get_query_sparse_vector(query: str) -> SparseVector:
    """Generate a sparse BM25 query vector for Qdrant using fitted BM25 vocab."""
    retriever = get_bm25_retriever()
    words = query.lower().split()
    
    indices = []
    values = []
    
    if retriever and hasattr(retriever, "vocab_dict"):
        vocab = retriever.vocab_dict  # id -> word
        word_to_id = {v: k for k, v in vocab.items()}
        from collections import Counter
        tf = Counter(words)
        for word, count in tf.items():
            if word in word_to_id:
                indices.append(word_to_id[word])
                values.append(float(count))
    else:
        # Fallback hash if no vocab model loaded
        from collections import Counter
        tf = Counter(words)
        for word, count in tf.items():
            idx = abs(hash(word)) % 100000
            indices.append(idx)
            values.append(float(count))

    return SparseVector(indices=indices, values=values)


# ── Hybrid Retrieval ───────────────────────────────────────────────────────────

def hybrid_retrieve(query: str, top_k: int = 20) -> list[dict]:
    """
    Executes hybrid search on Qdrant:
      1. Dense similarity search via MiniLM
      2. Sparse keyword search via BM25
      3. Combines & deduplicates top candidates
    Returns a list of chunk payload dicts with score metadata.
    """
    client = get_qdrant_client()
    embedder = get_embedder()

    # 1. Encode dense query
    dense_vec = embedder.encode(query, normalize_embeddings=True).tolist()

    # 2. Query Qdrant dense vector index
    dense_results = []
    try:
        dense_res_obj = client.query_points(
            collection_name=COLLECTION_NAME,
            query=dense_vec,
            using="dense",
            limit=top_k,
            with_payload=True,
        )
        dense_results = dense_res_obj.points
    except Exception as e:
        log.error(f"Dense vector search failed: {e}")

    # 3. Encode sparse query & query Qdrant sparse BM25 index
    sparse_vec = get_query_sparse_vector(query)
    sparse_results = []
    if sparse_vec.indices:
        try:
            sparse_res_obj = client.query_points(
                collection_name=COLLECTION_NAME,
                query=sparse_vec,
                using="bm25",
                limit=top_k,
                with_payload=True,
            )
            sparse_results = sparse_res_obj.points
        except Exception as e:
            log.warning(f"Sparse search error (continuing with dense results): {e}")

    # 4. RRF (Reciprocal Rank Fusion) Merging
    rrf_scores: dict[str, float] = {}
    point_map: dict[str, dict] = {}
    k_rrf = 60  # RRF constant

    for rank, point in enumerate(dense_results):
        point_id = str(point.id)
        rrf_scores[point_id] = rrf_scores.get(point_id, 0.0) + (1.0 / (k_rrf + rank + 1))
        point_map[point_id] = {
            "id": point_id,
            "text": point.payload.get("original_text", ""),
            "source": point.payload.get("source", "Unknown"),
            "page": point.payload.get("page", 0),
            "context_summary": point.payload.get("context_summary", ""),
            "dense_score": float(point.score),
            "sparse_score": 0.0,
            "source_type": "rag",
        }

    for rank, point in enumerate(sparse_results):
        point_id = str(point.id)
        rrf_scores[point_id] = rrf_scores.get(point_id, 0.0) + (1.0 / (k_rrf + rank + 1))
        if point_id in point_map:
            point_map[point_id]["sparse_score"] = float(point.score)
        else:
            point_map[point_id] = {
                "id": point_id,
                "text": point.payload.get("original_text", ""),
                "source": point.payload.get("source", "Unknown"),
                "page": point.payload.get("page", 0),
                "context_summary": point.payload.get("context_summary", ""),
                "dense_score": 0.0,
                "sparse_score": float(point.score),
                "source_type": "rag",
            }

    # Sort merged points by RRF score
    sorted_ids = sorted(rrf_scores.keys(), key=lambda pid: rrf_scores[pid], reverse=True)
    merged_results = []
    for pid in sorted_ids[:top_k]:
        item = point_map[pid]
        item["rrf_score"] = rrf_scores[pid]
        merged_results.append(item)

    log.info(f"Hybrid retrieval fetched {len(merged_results)} merged chunks for query: '{query[:50]}...'")
    return merged_results


# ── FlashRank Cross-Encoder Reranker ──────────────────────────────────────────

def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """
    Reranks candidate chunks using FlashRank cross-encoder.
    Returns top_n highest scoring chunks.
    """
    if not chunks:
        return []

    ranker = get_reranker()

    # Format input for FlashRank
    passages = [
        {"id": c["id"], "text": f"{c.get('source', '')} (Page {c.get('page', 0)}): {c['text']}"}
        for c in chunks
    ]

    rerank_request = RerankRequest(query=query, passages=passages)
    rerank_results = ranker.rerank(rerank_request)

    # Map scores back to original chunk dicts
    chunk_dict = {c["id"]: c for c in chunks}
    reranked_chunks = []

    for item in rerank_results[:top_n]:
        chunk_id = item["id"]
        if chunk_id in chunk_dict:
            c = chunk_dict[chunk_id].copy()
            c["rerank_score"] = float(item["score"])
            reranked_chunks.append(c)

    log.info(f"Reranked {len(chunks)} candidate chunks down to top {len(reranked_chunks)}.")
    return reranked_chunks


def retrieve_and_rerank(query: str, top_k: int = 20, top_n: int = 5) -> list[dict]:
    """Combined single call: Hybrid Retrieve + Rerank."""
    candidates = hybrid_retrieve(query, top_k=top_k)
    return rerank(query, candidates, top_n=top_n)


# ── Standalone CLI Test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_query = sys.argv[1] if len(sys.argv) > 1 else "bail application IPC 302 grounds for grant"
    print(f"\n🔍 Testing Hybrid Retrieval + FlashRank Reranking")
    print(f"   Query: '{test_query}'\n")

    t0 = time.time()
    results = retrieve_and_rerank(test_query, top_k=15, top_n=5)
    t1 = time.time()

    print(f"⏱  Retrieval + Rerank completed in {t1-t0:.2f}s\n")
    print("=" * 70)
    for i, res in enumerate(results):
        print(f"[{i+1}] Source: {res['source']} (Page {res['page']})")
        print(f"    RRF Score: {res.get('rrf_score', 0):.4f} | Rerank Score: {res.get('rerank_score', 0):.4f}")
        print(f"    Snippet  : {res['text'][:180]}...")
        print("-" * 70)
