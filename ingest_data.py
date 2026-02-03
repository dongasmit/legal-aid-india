import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# Updated import to fix the warning you saw
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import sys
import io

# ⚠️ CRITICAL FIX: Force UTF-8 encoding for Windows consoles/logs
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ... (rest of your imports like os, langchain, etc.) ...
# Configuration
DATA_FOLDER = "source_docs"
DB_PATH = "vector_db"

def ingest_pdfs():
    # 1. Check if folder exists
    if not os.path.exists(DATA_FOLDER):
        print(f"❌ Error: Folder '{DATA_FOLDER}' not found.")
        return

    # 2. Find all PDFs
    pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"❌ No PDFs found in '{DATA_FOLDER}'.")
        return

    print(f"📚 Found {len(pdf_files)} PDFs...")

    all_chunks = []

    # 3. Process each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_FOLDER, pdf_file)
        print(f"Processing {pdf_file}...")
        
        try:
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            
            # Split Text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\nSection", "\nArticle", "\n", " "]
            )
            
            chunks = text_splitter.split_documents(documents)
            all_chunks.extend(chunks)
            print(f"   -> Split into {len(chunks)} chunks.")
        except Exception as e:
            print(f"   ⚠️ Error reading {pdf_file}: {e}")

    print(f"🧠 Embeddings {len(all_chunks)} total chunks (Processing in batches)...")
    
    # 4. Create/Reset Vector DB
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    if os.path.exists(DB_PATH):
        import shutil
        shutil.rmtree(DB_PATH)
        print("   -> Cleared old database.")

    # Initialize DB
    vector_db = Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings
    )

    # 5. Batch Insert (The Fix!)
    # We insert 4000 chunks at a time to stay under the 5461 limit
    BATCH_SIZE = 4000
    total_batches = (len(all_chunks) // BATCH_SIZE) + 1

    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        print(f"   -> Inserting batch {i//BATCH_SIZE + 1}/{total_batches} ({len(batch)} chunks)...")
        vector_db.add_documents(documents=batch)

    print(f"✅ Success! Knowledge Base updated with {len(all_chunks)} chunks.")

if __name__ == "__main__":
    ingest_pdfs()