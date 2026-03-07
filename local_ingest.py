import os
import glob
import gc
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

# Load API keys from your .env file
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError("❌ PINECONE_API_KEY is missing in your .env file!")

INDEX_NAME = "jurisone-index"
extract_folder = "source_docs"

print("🚀 Initializing Local Ingestion Engine...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

# Find all PDFs in your local folder
pdf_files = glob.glob(f"{extract_folder}/**/*.pdf", recursive=True)
print(f"📚 Found {len(pdf_files)} PDFs in local folder.")

if len(pdf_files) == 0:
    print("⚠️ No PDFs found! Make sure you unzipped the Kaggle data into the 'source_docs' folder.")
    exit()

# The Local Tank Loop (Processing first 500 for testing, change to process all later)
for i, pdf in enumerate(pdf_files[:500]): 
    print(f"🔄 Processing [{i+1}/500]: {os.path.basename(pdf)}")
    try:
        loader = PyMuPDFLoader(pdf)
        docs = loader.load()
        chunks = text_splitter.split_documents(docs)
        
        if chunks:
            PineconeVectorStore.from_documents(chunks, embeddings, index_name=INDEX_NAME)
            
        # Free memory immediately
        del loader, docs, chunks
    except Exception as e:
        print(f"   ⚠️ Skipped broken PDF: {os.path.basename(pdf)} - {e}")
    
    # Empty the trash
    gc.collect()

print("✅ Local Historical Upload Complete! The Cloud Brain is updated.")