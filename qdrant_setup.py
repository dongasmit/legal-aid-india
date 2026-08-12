"""
qdrant_setup.py — One-time collection initializer for JurisOne Agentic RAG.

Creates the 'jurisone_legal' collection with:
  - Dense vector  : 384-dim (all-MiniLM-L6-v2), Cosine distance
  - Sparse vector : "bm25" named vector for hybrid search

Run once after starting Qdrant:
    python qdrant_setup.py
"""

import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    HnswConfigDiff,
    OptimizersConfigDiff,
)

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "jurisone_legal")

# Dense vector dimension for all-MiniLM-L6-v2
DENSE_DIM = 384


def wait_for_qdrant(client: QdrantClient, retries: int = 10) -> bool:
    """Wait until Qdrant is ready to accept connections."""
    import time
    for attempt in range(1, retries + 1):
        try:
            client.get_collections()
            return True
        except Exception as e:
            print(f"  Attempt {attempt}/{retries}: Qdrant not ready ({e}), retrying in 2s...")
            time.sleep(2)
    return False


def create_collection(client: QdrantClient) -> None:
    """Create the jurisone_legal collection with dense + sparse vectors."""

    # Check if already exists
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"✅ Collection '{COLLECTION_NAME}' already exists — skipping creation.")
        info = client.get_collection(COLLECTION_NAME)
        print(f"   Points count : {info.points_count}")
        print(f"   Status       : {info.status}")
        return

    print(f"🔧 Creating collection '{COLLECTION_NAME}'...")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        # Dense vectors (MiniLM)
        vectors_config={
            "dense": VectorParams(
                size=DENSE_DIM,
                distance=Distance.COSINE,
                hnsw_config=HnswConfigDiff(
                    m=16,               # HNSW connections per node
                    ef_construct=200,   # Build-time accuracy (higher = better index, slower build)
                ),
            )
        },
        # Sparse vectors (BM25 / keyword)
        sparse_vectors_config={
            "bm25": SparseVectorParams(
                index=SparseIndexParams(
                    on_disk=True,       # Keeps RAM usage low for large legal corpora
                )
            )
        },
        # Optimizer config — tuned for large legal document corpus
        optimizers_config=OptimizersConfigDiff(
            indexing_threshold=20_000,  # Build HNSW index after 20k vectors
            memmap_threshold=50_000,    # Use mmap for segments above 50k vectors
        ),
        # Store all payload on disk to save RAM
        on_disk_payload=True,
    )

    print(f"✅ Collection '{COLLECTION_NAME}' created successfully!")
    print(f"   Dense vector  : {DENSE_DIM}-dim, Cosine, HNSW(m=16, ef=200)")
    print(f"   Sparse vector : 'bm25', on-disk index")
    print(f"   Payload       : on-disk")


def verify_collection(client: QdrantClient) -> None:
    """Print collection info to verify setup."""
    print(f"\n📋 Collection info for '{COLLECTION_NAME}':")
    info = client.get_collection(COLLECTION_NAME)
    print(f"   Status         : {info.status}")
    print(f"   Points count   : {info.points_count}")
    print(f"   Vectors config :")
    for name, cfg in (info.config.params.vectors or {}).items():
        print(f"     [{name}] size={cfg.size}, distance={cfg.distance}")
    if info.config.params.sparse_vectors:
        for name in info.config.params.sparse_vectors:
            print(f"     [{name}] sparse BM25 (on-disk)")


def main() -> None:
    print(f"🔌 Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL, timeout=30)

    if not wait_for_qdrant(client):
        print("❌ Qdrant is not responding. Is the Podman container running?")
        print("   Run:  bash qdrant-podman.sh start")
        sys.exit(1)

    print(f"✅ Connected to Qdrant.")
    create_collection(client)
    verify_collection(client)

    print("\n🎉 Setup complete! Next steps:")
    print("   1. python local_ingest.py   ← ingest all PDFs into Qdrant")
    print("   2. python retrieval.py      ← test hybrid search")


if __name__ == "__main__":
    main()
