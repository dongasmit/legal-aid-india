import os
from langchain_community.document_loaders import CSVLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

DATA_PATH = "data/bns_cleaned.csv"
DB_PATH = "vector_db"

def create_vector_db():
    if not os.path.exists(DATA_PATH):
        print(" Error: Data file not found. Run ingest_data.py first!")
        return

    print(" Loading data from CSV...")
    loader = CSVLoader(file_path=DATA_PATH, source_column="full_legal_text", encoding="utf-8")
    documents = loader.load()
    
    print(f" Loaded {len(documents)} legal sections.")

    print(" Initializing Embedding Model (This converts text to numbers)...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    print("  Creating Vector Database (This might take a minute)...")
    
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=DB_PATH
    )

    print(f" Success! Vector Database created at '{DB_PATH}'")
    print(" You are ready for Phase 3!")

if __name__ == "__main__":
    create_vector_db()