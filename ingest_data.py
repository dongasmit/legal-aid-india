import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from config import INDEX_NAME, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, DATA_FOLDER, get_logger

logger = get_logger(__name__)

load_dotenv()

def ingest_pdfs():
    # 1. Check if folder exists
    if not os.path.exists(DATA_FOLDER):
        logger.error("Folder '%s' not found.", DATA_FOLDER)
        return

    # 2. Find all PDFs
    pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
    if not pdf_files:
        logger.error("No PDFs found in '%s'.", DATA_FOLDER)
        return

    logger.info("Found %d PDFs...", len(pdf_files))

    all_chunks = []

    # 3. Process each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_FOLDER, pdf_file)
        logger.info("Processing %s...", pdf_file)

        try:
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()

            # Split Text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                separators=["\nSection", "\nArticle", "\n", " "]
            )

            chunks = text_splitter.split_documents(documents)
            all_chunks.extend(chunks)
            logger.info("   -> Split into %d chunks.", len(chunks))
        except Exception as exc:
            logger.warning("   Error reading %s: %s", pdf_file, exc)

    logger.info("Embedding %d total chunks...", len(all_chunks))

    # 4. Embed and upload to Pinecone
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    logger.info("Uploading to Pinecone index '%s'...", INDEX_NAME)
    PineconeVectorStore.from_documents(all_chunks, embeddings, index_name=INDEX_NAME)

    logger.info("Knowledge Base updated with %d chunks.", len(all_chunks))

if __name__ == "__main__":
    ingest_pdfs()