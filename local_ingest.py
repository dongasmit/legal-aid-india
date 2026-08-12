"""
local_ingest.py — Phase 2: Contextual Re-Ingestion Pipeline
============================================================
Replaces the old Pinecone ingestion with a Qdrant dual-vector pipeline:

  For each PDF in source_docs/:
    1. Extract full doc text + split into chunks (PyMuPDF + LangChain splitter)
    2. Contextual Enrichment: call Groq (Llama-3.3) once per chunk to generate
       a 2-3 sentence situating summary using whole-document context
    3. Embed with all-MiniLM-L6-v2 (dense, 384-dim)
    4. Fit/update BM25 sparse model on the full corpus text
    5. Upsert both vectors + payload into Qdrant collection 'jurisone_legal'
    6. Persist the fitted BM25 model to bm25_model.pkl for query-time use

Usage:
    python local_ingest.py [--skip-context] [--batch-size 10] [--limit 0]

Flags:
    --skip-context   Skip Groq contextual enrichment (pure chunk embeddings)
    --batch-size N   Qdrant upsert batch size (default: 32)
    --limit N        Only process first N PDFs (0 = all, useful for testing)
    --dry-run        Extract + embed but do NOT upsert (for debugging)
"""

import os
import sys
import gc
import glob
import time
import uuid
import pickle
import argparse
import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import bm25s
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "jurisone_legal")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SOURCE_DOCS_DIR = "source_docs"
BM25_MODEL_PATH = "bm25_model.pkl"

CHUNK_SIZE = 1000       # chars per chunk
CHUNK_OVERLAP = 200     # overlap between chunks
MAX_DOC_CONTEXT_CHARS = 6000  # chars of full doc sent to Groq for context
GROQ_RATE_DELAY = 0.3   # seconds between Groq calls (free tier safety)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Models (loaded once) ──────────────────────────────────────────────────────
log.info("Loading MiniLM embedding model...")
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

llm: Optional[ChatGroq] = None
context_chain = None

if GROQ_API_KEY:
    llm = ChatGroq(
        temperature=0.1,
        model_name="llama-3.3-70b-versatile",
        api_key=GROQ_API_KEY,
        max_tokens=256,
    )
    context_prompt = ChatPromptTemplate.from_template(
        """You are a legal research assistant. Your task is to write a concise 2-3 sentence
summary that situates the following CHUNK within the context of the full legal document.
Focus on what this chunk establishes, which law/section/case it relates to,
and why it is legally significant.

DOCUMENT CONTEXT (first {context_chars} chars):
{doc_context}

CHUNK TO SITUATE:
{chunk}

Write ONLY the 2-3 sentence situating summary. No preamble."""
    )
    context_chain = context_prompt | llm | StrOutputParser()
else:
    log.warning("GROQ_API_KEY not set — running without contextual enrichment.")


# ── PDF Utilities ─────────────────────────────────────────────────────────────

def extract_pdf_text(pdf_path: str) -> str:
    """Extract full text from a PDF using PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        pages = []
        for page in doc:
            pages.append(page.get_text("text"))
        doc.close()
        return "\n".join(pages)
    except Exception as e:
        log.error(f"Failed to extract text from {pdf_path}: {e}")
        return ""


def split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[dict]:
    """
    Splits text into overlapping chunks.
    Returns list of dicts with 'text' and 'char_start'.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        if len(chunk_text) > 50:  # skip tiny trailing fragments
            chunks.append({"text": chunk_text, "char_start": start})
        start += chunk_size - overlap
    return chunks


def get_page_number(char_start: int, page_boundaries: list[int]) -> int:
    """Map character offset to page number (0-indexed)."""
    for i, boundary in enumerate(page_boundaries):
        if char_start < boundary:
            return i
    return len(page_boundaries) - 1


def build_page_boundaries(pdf_path: str) -> list[int]:
    """Returns cumulative char counts per page (for page number mapping)."""
    boundaries = []
    cumulative = 0
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            cumulative += len(page.get_text("text"))
            boundaries.append(cumulative)
        doc.close()
    except Exception:
        pass
    return boundaries


# ── Contextual Enrichment ─────────────────────────────────────────────────────

def enrich_chunk_with_context(chunk_text: str, doc_context: str, retries: int = 3) -> str:
    """Call Groq to generate a situating summary for the chunk."""
    if context_chain is None:
        return ""
    for attempt in range(retries):
        try:
            summary = context_chain.invoke({
                "doc_context": doc_context[:MAX_DOC_CONTEXT_CHARS],
                "context_chars": MAX_DOC_CONTEXT_CHARS,
                "chunk": chunk_text[:800],  # don't send massive chunks
            })
            time.sleep(GROQ_RATE_DELAY)
            return summary.strip()
        except Exception as e:
            wait = 2 ** attempt
            log.warning(f"Groq API error (attempt {attempt+1}/{retries}): {e}. Retrying in {wait}s...")
            time.sleep(wait)
    log.error("Groq enrichment failed after all retries — using empty context.")
    return ""


# ── Qdrant Upsert ─────────────────────────────────────────────────────────────

def upsert_batch(
    client: QdrantClient,
    points: list[PointStruct],
    collection: str,
) -> None:
    """Upsert a batch of PointStructs into Qdrant."""
    client.upsert(collection_name=collection, points=points, wait=True)


def save_bm25_model(retriever) -> None:
    """Persist the fitted BM25 model to disk."""
    try:
        retriever.save("bm25_model")
    except Exception:
        with open(BM25_MODEL_PATH, "wb") as f:
            pickle.dump(retriever, f)
    log.info("✅ BM25 model saved.")


def get_sparse_vector(retriever, tokens: list[str]) -> SparseVector:
    """
    Generate a sparse BM25 vector for a single document's tokens.
    Returns a Qdrant SparseVector with indices and values.
    """
    # bm25s scores a single doc against its own vocab
    query_tokens = bm25s.tokenize([" ".join(tokens)], stopwords="en")
    results, scores = retriever.retrieve(query_tokens, k=min(len(retriever.vocab_dict), 512))
    
    # Build sparse indices/values from the scored results
    indices = []
    values = []
    if results is not None and len(results) > 0:
        for idx, score in zip(results[0], scores[0]):
            if score > 0:
                word = retriever.vocab_dict.get(idx, "")
                if word and word in retriever.word_to_id:
                    indices.append(retriever.word_to_id[word])
                    values.append(float(score))
    
    if not indices:
        # Fallback: use term frequency directly from tokens
        from collections import Counter
        tf = Counter(tokens)
        vocab = retriever.vocab_dict
        for word, count in tf.items():
            if word in retriever.word_to_id:
                indices.append(retriever.word_to_id[word])
                values.append(float(count))

    return SparseVector(indices=indices, values=values)


# ── Main Ingestion Pipeline ───────────────────────────────────────────────────

def run_ingestion(
    skip_context: bool = False,
    batch_size: int = 32,
    limit: int = 0,
    dry_run: bool = False,
) -> None:
    log.info("=" * 60)
    log.info("JurisOne — Phase 2 Contextual Ingestion Pipeline")
    log.info("=" * 60)

    # Connect to Qdrant
    client = QdrantClient(url=QDRANT_URL, timeout=60)
    try:
        client.get_collection(COLLECTION_NAME)
        log.info(f"Connected to Qdrant: collection '{COLLECTION_NAME}' found.")
    except Exception as e:
        log.error(f"Cannot connect to Qdrant or collection missing: {e}")
        log.error("Run: python3 qdrant_setup.py  first.")
        sys.exit(1)

    # Discover all PDFs
    pdf_files = sorted(
        glob.glob(f"{SOURCE_DOCS_DIR}/**/*.pdf", recursive=True)
        + glob.glob(f"{SOURCE_DOCS_DIR}/*.pdf")
    )
    # Deduplicate
    pdf_files = list(dict.fromkeys(pdf_files))
    
    if limit > 0:
        pdf_files = pdf_files[:limit]
        log.info(f"[--limit] Processing first {limit} PDFs only.")

    log.info(f"📚 Found {len(pdf_files)} PDFs to ingest.")
    if not pdf_files:
        log.error(f"No PDFs found in '{SOURCE_DOCS_DIR}/'.")
        sys.exit(1)

    # Phase A: Collect ALL chunk texts for BM25 corpus fitting
    log.info("\n─── Phase A: Extracting text from all PDFs ───")
    all_chunk_texts: list[str] = []
    pdf_chunk_map: list[dict] = []  # stores per-pdf chunk metadata

    for i, pdf_path in enumerate(pdf_files):
        pdf_name = Path(pdf_path).name
        log.info(f"  [{i+1}/{len(pdf_files)}] Extracting: {pdf_name}")

        full_text = extract_pdf_text(pdf_path)
        if not full_text.strip():
            log.warning(f"    ⚠️  No text extracted — skipping.")
            continue

        page_boundaries = build_page_boundaries(pdf_path)
        chunks = split_into_chunks(full_text, CHUNK_SIZE, CHUNK_OVERLAP)

        doc_context = full_text[:MAX_DOC_CONTEXT_CHARS]

        for chunk in chunks:
            chunk["source"] = pdf_name
            chunk["pdf_path"] = pdf_path
            chunk["doc_context"] = doc_context
            chunk["page"] = get_page_number(chunk["char_start"], page_boundaries)
            all_chunk_texts.append(chunk["text"])
            pdf_chunk_map.append(chunk)

        gc.collect()

    log.info(f"\n📊 Total chunks across corpus: {len(all_chunk_texts)}")

    # Phase B: Fit BM25 on full corpus
    log.info("\n─── Phase B: Fitting BM25 model on full corpus ───")
    corpus_tokens = bm25s.tokenize(all_chunk_texts, stopwords="en", show_progress=False)
    bm25_retriever = bm25s.BM25()
    bm25_retriever.index(corpus_tokens)
    log.info(f"✅ BM25 model fitted. Vocabulary size: {len(bm25_retriever.vocab_dict)}")

    if not dry_run:
        save_bm25_model(bm25_retriever)

    # Phase C: Embed + Enrich + Upsert
    log.info("\n─── Phase C: Embedding + Enrichment + Qdrant Upsert ───")
    points_buffer: list[PointStruct] = []
    total_upserted = 0
    failed = 0

    for idx, chunk in enumerate(pdf_chunk_map):
        pdf_name = chunk["source"]
        chunk_text = chunk["text"]
        doc_context = chunk["doc_context"]
        page = chunk["page"]

        try:
            # 1. Contextual enrichment (optional)
            context_summary = ""
            if not skip_context and context_chain is not None:
                context_summary = enrich_chunk_with_context(chunk_text, doc_context)

            # 2. Contextualized chunk = summary + raw chunk
            if context_summary:
                contextualized_text = f"{context_summary}\n\n{chunk_text}"
            else:
                contextualized_text = chunk_text

            # 3. Dense embedding (MiniLM)
            dense_vec = embedder.encode(
                contextualized_text,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

            # 4. Sparse BM25 vector
            chunk_tokens_obj = bm25s.tokenize([chunk_text], stopwords="en", show_progress=False)
            chunk_token_list = chunk_tokens_obj.vocab if hasattr(chunk_tokens_obj, 'vocab') else []
            
            # Get BM25 scores for this chunk against the corpus
            results, scores = bm25_retriever.retrieve(chunk_tokens_obj, k=1)
            
            # Build sparse vector using vocab indices + BM25 scores
            from collections import Counter
            raw_tokens = chunk_text.lower().split()
            tf = Counter(raw_tokens)
            sparse_indices = []
            sparse_values = []
            vocab = bm25_retriever.vocab_dict  # id -> word
            word_to_id = {v: k for k, v in vocab.items()}
            
            for word, count in tf.items():
                if word in word_to_id:
                    sparse_indices.append(word_to_id[word])
                    sparse_values.append(float(count))

            sparse_vec = SparseVector(
                indices=sparse_indices,
                values=sparse_values,
            )

            # 5. Build Qdrant point
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "dense": dense_vec,
                    "bm25": sparse_vec,
                },
                payload={
                    "source": pdf_name,
                    "page": page,
                    "char_start": chunk["char_start"],
                    "original_text": chunk_text,
                    "context_summary": context_summary,
                    "contextualized_text": contextualized_text,
                    "source_type": "rag",
                },
            )
            points_buffer.append(point)

            # Upsert when buffer is full
            if len(points_buffer) >= batch_size:
                if not dry_run:
                    upsert_batch(client, points_buffer, COLLECTION_NAME)
                total_upserted += len(points_buffer)
                log.info(
                    f"  ✅ Upserted batch ({total_upserted}/{len(pdf_chunk_map)} chunks) "
                    f"| {pdf_name} page {page}"
                )
                points_buffer.clear()

        except Exception as e:
            log.error(f"  ⚠️  Chunk {idx} from '{pdf_name}' failed: {e}")
            failed += 1
            continue

    # Flush remaining points
    if points_buffer and not dry_run:
        upsert_batch(client, points_buffer, COLLECTION_NAME)
        total_upserted += len(points_buffer)

    # Final summary
    log.info("\n" + "=" * 60)
    if dry_run:
        log.info(f"🧪 DRY RUN complete. Would have upserted {len(pdf_chunk_map)} chunks.")
    else:
        log.info(f"🎉 Ingestion complete!")
        log.info(f"   Total chunks upserted : {total_upserted}")
        log.info(f"   Failed chunks         : {failed}")
        log.info(f"   BM25 model saved to   : {BM25_MODEL_PATH}")
        
        # Verify count in Qdrant
        info = client.get_collection(COLLECTION_NAME)
        log.info(f"   Qdrant point count    : {info.points_count}")
    log.info("=" * 60)
    log.info("\nNext step: python3 retrieval.py")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JurisOne Phase 2 Ingestion")
    parser.add_argument(
        "--skip-context",
        action="store_true",
        help="Skip Groq contextual enrichment (faster, no API calls)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Qdrant upsert batch size (default: 32)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process first N PDFs (0 = all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and embed but do NOT write to Qdrant",
    )
    args = parser.parse_args()

    run_ingestion(
        skip_context=args.skip_context,
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
    )