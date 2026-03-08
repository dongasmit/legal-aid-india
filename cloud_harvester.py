import os
import json
import feedparser
import requests
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from config import INDEX_NAME, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, get_logger

logger = get_logger(__name__)

# --- CONFIGURATION ---
# Using GitHub Secrets for environment variables in the cloud
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")

HARVESTED_URLS_FILE = "harvested_urls.json"

# Legal RSS Feeds (Unblockable, constantly updated)
RSS_FEEDS = [
    "https://www.livelaw.in/rss/top-stories", # Top Legal News in India
    "https://news.google.com/rss/search?q=Supreme+Court+of+India+Judgment&hl=en-IN&gl=IN&ceid=IN:en" # Google News RSS for SC
]


def load_harvested_urls() -> set:
    """Load the set of already-processed URLs from disk."""
    if os.path.exists(HARVESTED_URLS_FILE):
        try:
            with open(HARVESTED_URLS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            logger.warning("Could not parse %s; starting with empty URL set.", HARVESTED_URLS_FILE)
    return set()


def save_harvested_urls(urls: set) -> None:
    """Persist the set of processed URLs to disk."""
    with open(HARVESTED_URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(urls), f)


def clean_html(html_content):
    """Extracts clean text from web pages."""
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove scripts and styles
    for script in soup(["script", "style"]):
        script.extract()
    return soup.get_text(separator=" ", strip=True)

def harvest_rss_feeds():
    logger.info("Starting Cloud RSS Harvest...")
    harvested_urls = load_harvested_urls()
    documents = []
    new_urls: set = set()

    for feed_url in RSS_FEEDS:
        logger.info("Connecting to feed: %s", feed_url)
        feed = feedparser.parse(feed_url)

        # Grab the top 5 most recent articles per feed
        for entry in feed.entries[:5]:
            try:
                if entry.link in harvested_urls:
                    logger.info("   Skipping already-harvested URL: %s", entry.link)
                    continue

                logger.info("   Fetching: %s", entry.title)
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
                    new_urls.add(entry.link)
            except Exception as exc:
                logger.warning("   Failed to parse %s: %s", entry.link, exc)

    # Persist the updated URL set after harvesting
    harvested_urls.update(new_urls)
    save_harvested_urls(harvested_urls)

    return documents

def push_to_pinecone(documents):
    if not documents:
        logger.info("No new documents to process.")
        return

    logger.info("Processing %d new legal documents...", len(documents))

    # 1. Chunk the text
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    # Format for Pinecone
    texts = [doc["page_content"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]

    chunks = text_splitter.create_documents(texts, metadatas)
    logger.info("Split into %d chunks.", len(chunks))

    # 2. Embed and Upload to Cloud Brain
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    logger.info("Beaming data to Pinecone...")
    PineconeVectorStore.from_documents(
        chunks,
        embeddings,
        index_name=INDEX_NAME
    )
    logger.info("Cloud Brain Updated Successfully!")

if __name__ == "__main__":
    if not PINECONE_API_KEY:
        logger.error("PINECONE_API_KEY is missing. Harvester aborting.")
        exit(1)

    docs = harvest_rss_feeds()
    push_to_pinecone(docs)