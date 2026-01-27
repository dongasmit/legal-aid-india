import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Configuration
DATA_FOLDER = "source_docs"
DB_PATH = "vector_db"

def ingest_pdfs():
    # 1. Check if folder exists
    if not os.path.exists(DATA_FOLDER):
        print(f"❌ Error: Folder '{DATA_FOLDER}' not found. Please create it and add your PDFs.")
        return

    # 2. Find all PDFs
    pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"❌ No PDFs found in '{DATA_FOLDER}'. Please add the BNS PDF.")
        return

    print(f"📚 Found {len(pdf_files)} PDFs: {pdf_files}")

    all_chunks = []

    # 3. Process each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_FOLDER, pdf_file)
        print(f"Processing {pdf_file}...")
        
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        
        # 4. Split Text into smart chunks
        # We use a large chunk size (1000 chars) so the AI gets full context of a law
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\nSection", "\nArticle", "\n", " "]
        )
        
        chunks = text_splitter.split_documents(documents)
        all_chunks.extend(chunks)
        print(f"   -> Split into {len(chunks)} chunks.")

    print(f"🧠 Embeddings {len(all_chunks)} total chunks (This will take a while)...")
    
    # 5. Create Vector DB
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Delete old DB if it exists to start fresh
    if os.path.exists(DB_PATH):
        import shutil
        shutil.rmtree(DB_PATH)
        print("   -> Cleared old database.")

    vector_db = Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=DB_PATH
    )

    print(f"✅ Success! Knowledge Base updated with {len(all_chunks)} chunks.")

if __name__ == "__main__":
    ingest_pdfs()