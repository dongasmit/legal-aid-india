import os
import feedparser
import requests
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

# --- CONFIGURATION ---
# Using GitHub Secrets for environment variables in the cloud
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
INDEX_NAME = "jurisone-index"

# Legal RSS Feeds (Unblockable, constantly updated)
RSS_FEEDS = [
    "https://www.livelaw.in/rss/top-stories", # Top Legal News in India
    "https://news.google.com/rss/search?q=Supreme+Court+of+India+Judgment&hl=en-IN&gl=IN&ceid=IN:en" # Google News RSS for SC
]

def clean_html(html_content):
    """Extracts clean text from web pages."""
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove scripts and styles
    for script in soup(["script", "style"]):
        script.extract()
    return soup.get_text(separator=" ", strip=True)

def harvest_rss_feeds():
    print("🚜 Starting Cloud RSS Harvest...")
    documents = []
    
    for feed_url in RSS_FEEDS:
        print(f"📡 Connecting to feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        # Grab the top 5 most recent articles per feed
        for entry in feed.entries[:5]:
            try:
                print(f"   📄 Fetching: {entry.title}")
                # Get the actual article content
                response = requests.get(entry.link, timeout=10)
                if response.status_code == 200:
                    clean_text = clean_html(response.text)
                    
                    # Create a standard dictionary format for LangChain
                    doc = {
                        "page_content": clean_text,
                        "metadata": {"source": entry.link, "title": entry.title}
                    }
                    documents.append(doc)
            except Exception as e:
                print(f"   ⚠️ Failed to parse {entry.link}: {e}")
                
    return documents

def push_to_pinecone(documents):
    if not documents:
        print("💤 No new documents to process.")
        return

    print(f"🧠 Processing {len(documents)} new legal documents...")
    
    # 1. Chunk the text
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    
    # Format for Pinecone
    texts = [doc["page_content"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]
    
    chunks = text_splitter.create_documents(texts, metadatas)
    print(f"✂️ Split into {len(chunks)} chunks.")

    # 2. Embed and Upload to Cloud Brain
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    print("☁️ Beaming data to Pinecone...")
    PineconeVectorStore.from_documents(
        chunks, 
        embeddings, 
        index_name=INDEX_NAME
    )
    print("✅ Cloud Brain Updated Successfully!")

if __name__ == "__main__":
    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY is missing. Harvester aborting.")
        exit(1)
        
    docs = harvest_rss_feeds()
    push_to_pinecone(docs)