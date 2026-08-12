"""
web_search.py — Phase 4: Web Search Fallback for Unknown / Out-of-Corpus Queries
===================================================================================
Queries trusted external Indian legal sources (Indian Kanoon public search endpoint)
when the local Qdrant RAG corpus has low relevance score / missing information.

Functions:
    search_indian_kanoon(query, limit=5) -> list[dict]
    search_web_legal(query, limit=5) -> list[dict]

Standalone test:
    python3 web_search.py "Bharatiya Nyaya Sanhita section 103 punishment for murder"
"""

import os
import sys
import re
import logging
from typing import Optional
import httpx
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

INDIANKANOON_BASE = "https://indiankanoon.org"
SEARCH_URL = f"{INDIANKANOON_BASE}/search/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def clean_text(text: str) -> str:
    """Clean extra spaces, newlines, and HTML artifact tags."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def search_indian_kanoon(query: str, limit: int = 5) -> list[dict]:
    """
    Scrapes Indian Kanoon public search endpoint for relevant judgments / legal provisions.
    Returns list of result dicts: {title, snippet, url, source, source_type}
    """
    log.info(f"🌐 Querying Indian Kanoon web fallback for: '{query}'...")
    results = []

    params = {
        "formInput": query,
        "pagenum": 0,
    }

    try:
        with httpx.Client(headers=HEADERS, timeout=12.0, follow_redirects=True) as client:
            resp = client.get(SEARCH_URL, params=params)
            if resp.status_code != 200:
                log.warning(f"Indian Kanoon search returned HTTP {resp.status_code}")
                return results

            soup = BeautifulSoup(resp.text, "lxml")
            result_divs = soup.find_all("div", class_="result")

            for div in result_divs[:limit]:
                # Extract title and link
                title_tag = div.find("div", class_="result_title") or div.find("a")
                if not title_tag:
                    continue

                link = title_tag.find("a") if title_tag.name != "a" else title_tag
                if not link or not link.get("href"):
                    continue

                title = clean_text(link.get_text())
                rel_url = link["href"]
                full_url = f"{INDIANKANOON_BASE}{rel_url}" if rel_url.startswith("/") else rel_url

                # Extract snippet snippet
                headline_div = div.find("div", class_="headline")
                snippet = clean_text(headline_div.get_text()) if headline_div else title

                results.append({
                    "id": f"web_{hash(full_url)}",
                    "title": title,
                    "text": snippet,
                    "snippet": snippet,
                    "source": f"Indian Kanoon ({title})",
                    "url": full_url,
                    "page": 1,
                    "source_type": "web",
                    "rerank_score": 0.75,  # Baseline score for web hits
                })

    except Exception as e:
        log.error(f"Error scraping Indian Kanoon fallback: {e}")

    log.info(f"🌐 Indian Kanoon returned {len(results)} search results.")
    return results


def search_web_legal(query: str, limit: int = 5) -> list[dict]:
    """
    Unified entry point for Web Legal Search Fallback.
    Returns prioritized list of trusted Indian legal search results.
    """
    # Primary source: Indian Kanoon public search
    results = search_indian_kanoon(query, limit=limit)
    return results


# ── Standalone CLI Test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_query = sys.argv[1] if len(sys.argv) > 1 else "Bharatiya Nyaya Sanhita section 103 penalty"
    print(f"\n🌐 Testing Web Search Fallback (Indian Kanoon)")
    print(f"   Query: '{test_query}'\n")

    res = search_web_legal(test_query, limit=3)

    print("=" * 70)
    for i, item in enumerate(res):
        print(f"[{i+1}] Title: {item['title']}")
        print(f"    URL  : {item['url']}")
        print(f"    Text : {item['snippet'][:200]}...")
        print("-" * 70)
