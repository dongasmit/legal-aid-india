# DEPRECATED: This script used a local Chroma vector database and is kept
# for reference only.  The application now uses Pinecone as its vector store.
# Use ingest_data.py or local_ingest.py to populate the Pinecone index.

import os
from langchain_community.document_loaders import CSVLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from config import EMBEDDING_MODEL, DB_PATH, get_logger

logger = get_logger(__name__)

DATA_PATH = "data/bns_cleaned.csv"

def create_vector_db():
    if not os.path.exists(DATA_PATH):
        logger.error("Error: Data file not found. Run ingest_data.py first!")
        return

    logger.info("Loading data from CSV...")
    loader = CSVLoader(file_path=DATA_PATH, source_column="full_legal_text", encoding="utf-8")
    documents = loader.load()

    logger.info("Loaded %d legal sections.", len(documents))

    logger.info("Initialising Embedding Model...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    logger.info("Creating Vector Database...")

    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=DB_PATH
    )

    logger.info("Success! Vector Database created at '%s'", DB_PATH)
    logger.info("NOTE: This local Chroma DB is deprecated. Use Pinecone in production.")

if __name__ == "__main__":
    create_vector_db()