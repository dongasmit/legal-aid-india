import os
import glob
import gc
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from config import INDEX_NAME, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, DATA_FOLDER, get_logger

logger = get_logger(__name__)

# Load API keys from your .env file
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError("❌ PINECONE_API_KEY is missing in your .env file!")

logger.info("Initialising Local Ingestion Engine...")
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

# Find all PDFs in your local folder
pdf_files = glob.glob(f"{DATA_FOLDER}/**/*.pdf", recursive=True)
logger.info("Found %d PDFs in local folder.", len(pdf_files))

if len(pdf_files) == 0:
    logger.warning("No PDFs found! Make sure you unzipped the Kaggle data into the '%s' folder.", DATA_FOLDER)
    exit()

# The Local Tank Loop (Processing first 500 for testing, change to process all later)
for i, pdf in enumerate(pdf_files[:500]):
    logger.info("Processing [%d/500]: %s", i + 1, os.path.basename(pdf))
    try:
        loader = PyMuPDFLoader(pdf)
        docs = loader.load()
        chunks = text_splitter.split_documents(docs)

        if chunks:
            PineconeVectorStore.from_documents(chunks, embeddings, index_name=INDEX_NAME)

        # Free memory immediately
        del loader, docs, chunks
    except Exception as exc:
        logger.warning("   Skipped broken PDF: %s - %s", os.path.basename(pdf), exc)

    # Empty the trash
    gc.collect()

logger.info("Local Historical Upload Complete! The Cloud Brain is updated.")