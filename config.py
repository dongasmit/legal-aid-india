import logging

# --- Vector Store / AI Configuration ---
INDEX_NAME = "jurisone-index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.3-70b-versatile"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# --- File Paths ---
DATA_FOLDER = "source_docs"
DB_PATH = "vector_db"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured with the project-wide settings."""
    return logging.getLogger(name)
