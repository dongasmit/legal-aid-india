import os
import requests
import datetime
import subprocess
import sys
import time
import random
from googlesearch import search
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
DOWNLOAD_FOLDER = "source_docs"
LOG_FILE = "update_log.txt"
MAX_DOWNLOADS = 5  # Files per run

# 1. Search Queries (Broader is better)
SEARCH_QUERIES = [
    "Law Commission of India Reports pdf",
    "Landmark Supreme Court Judgments India full text pdf",
    "Indian Penal Code commentary pdf"
]

# 2. Direct Targets (Failsafe - Sites known to host PDFs)
DIRECT_TARGETS = [
    "https://cdnbbsr.s3waas.gov.in/s380537a945c7aaa788ccfcdf1b99b5d8f/uploads/2023/05/2023050195.pdf", # Example: A recent Gazette/Law
    "https://lawcommissionofindia.nic.in/report_277.pdf" # Wrongful Prosecution Report
]

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Force UTF-8 for emoji support
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def download_file(url, source_label="Search"):
    try:
        # Fake a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 1. Check HEAD first (Save bandwidth)
        try:
            head = requests.head(url, headers=headers, timeout=5)
            if 'application/pdf' not in head.headers.get('Content-Type', ''):
                return None
        except:
            pass # HEAD failed, try GET anyway

        # 2. Download
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Generate Name
            parsed = urlparse(url)
            filename = os.path.basename(unquote(parsed.path))
            
            # Clean filename
            if not filename.lower().endswith('.pdf'):
                filename = f"doc_{int(time.time())}.pdf"
            
            # Save
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            
            if not os.path.exists(filepath):
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filename
            else:
                return "EXISTS"
    except Exception as e:
        log(f"⚠️ Error downloading {url}: {e}")
    return None

def run_direct_target_scan():
    """Download from hardcoded reliable lists if search fails."""
    log("🎯 Running Direct Target Scan...")
    count = 0
    for url in DIRECT_TARGETS:
        res = download_file(url, "Direct")
        if res and res != "EXISTS":
            log(f"   ⬇️ Direct Download: {res}")
            count += 1
        elif res == "EXISTS":
            log(f"   ⏩ file exists: {url.split('/')[-1]}")
    return count

def run_google_scour():
    log("🌍 Scouring Google (Slow Mode)...")
    count = 0
    
    for query in SEARCH_QUERIES:
        if count >= MAX_DOWNLOADS: break
        
        log(f"🔎 Searching: '{query}'")
        
        # 'sleep_interval' makes it act human (Wait 5s between requests)
        # 'num' is results per page, 'stop' is when to stop
        try:
            for url in search(query, num_results=10, advanced=True, sleep_interval=5):
                if count >= MAX_DOWNLOADS: break
                
                link = url.url
                
                # Check if it's a PDF
                if link.lower().endswith('.pdf'):
                    log(f"   👀 Found PDF link: {link[:40]}...")
                    res = download_file(link)
                    
                    if res and res != "EXISTS":
                        log(f"   ⬇️ Downloaded: {res}")
                        count += 1
                    elif res == "EXISTS":
                        log("   ⏩ Exists.")
                        
        except Exception as e:
            log(f"⚠️ Search blocked or failed: {e}")
            
    return count

def run_ingestion():
    log("🧠 Running ingestion...")
    result = subprocess.run([sys.executable, "ingest_data.py"], capture_output=True, text=True)
    if result.returncode == 0:
        log("✅ Ingestion successful.")
        return True
    else:
        log(f"❌ Ingestion Failed: {result.stderr}")
        return False

def push_to_cloud():
    log("☁️ Pushing to Cloud...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto-update: {datetime.date.today()}"], check=True)
        subprocess.run(["git", "push"], check=True)
        log("🚀 Deployed!")
    except Exception as e:
        log(f"❌ Deploy Failed: {e}")

if __name__ == "__main__":
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    # 1. Run Search
    new_files = run_google_scour()
    
    # 2. If search failed, run Direct Targets
    if new_files == 0:
        log("⚠️ Search yielded 0 files. Switching to Direct Targets...")
        new_files += run_direct_target_scan()

    # 3. Ingest & Deploy
    if new_files > 0:
        if run_ingestion():
            push_to_cloud()
    else:
        log("💤 No new data found anywhere.")