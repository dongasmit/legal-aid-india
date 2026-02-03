import os
import time
import requests
import subprocess
import sys
import datetime
from urllib.parse import urlparse, unquote
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
DOWNLOAD_FOLDER = "source_docs"
LOG_FILE = "harvest_log.txt"
TARGET_COUNT = 30  # Try to find this many PDFs per run

# Queries designed to find BULK legal PDFs
SEARCH_QUERIES = [
    'site:sci.gov.in "judgment" filetype:pdf',
    'site:highcourtchd.gov.in "judgment" filetype:pdf',
    'site:bombayhighcourt.nic.in "judgment" filetype:pdf',
    'site:livelaw.in "read judgment" filetype:pdf',
    'site:nic.in "criminal appeal" judgment filetype:pdf'
]

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def setup_driver():
    """Starts a Headless Chrome Browser"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def download_pdf(url):
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', '').lower():
            
            # Clean filename
            parsed = urlparse(url)
            filename = os.path.basename(unquote(parsed.path))
            if not filename.lower().endswith('.pdf'):
                filename = f"harvest_{int(time.time())}.pdf"
            
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            
            if not os.path.exists(filepath):
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filename
    except:
        pass
    return None

def harvest_google(driver):
    total_downloaded = 0
    
    for query in SEARCH_QUERIES:
        if total_downloaded >= TARGET_COUNT: break
        
        # Google Search URL with "Past Week" filter (&tbs=qdr:w) to get FRESH data
        search_url = f"https://www.google.com/search?q={query}&tbs=qdr:w&num=20"
        
        log(f"🕵️  Browsing Google for: {query}")
        driver.get(search_url)
        time.sleep(3) # Wait for page to load
        
        # Find all links
        links = driver.find_elements(By.TAG_NAME, "a")
        
        for link in links:
            if total_downloaded >= TARGET_COUNT: break
            try:
                href = link.get_attribute("href")
                if href and ".pdf" in href.lower() and "google.com" not in href:
                    
                    log(f"   📎 Found PDF: {href[:40]}...")
                    name = download_pdf(href)
                    
                    if name:
                        log(f"   ⬇️ Downloaded: {name}")
                        total_downloaded += 1
            except:
                continue
                
    return total_downloaded

def run_ingestion():
    # Force UTF-8 environment for subprocess
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    log("🧠 Running ingestion...")
    result = subprocess.run([sys.executable, "ingest_data.py"], capture_output=True, text=True, env=env)
    
    if result.returncode == 0:
        log("✅ Ingestion successful.")
        return True
    else:
        log(f"❌ Ingestion Failed: {result.stderr}")
        return False

if __name__ == "__main__":
    if not os.path.exists(DOWNLOAD_FOLDER): os.makedirs(DOWNLOAD_FOLDER)
    
    log("🚜 Starting Daily Harvest...")
    
    try:
        driver = setup_driver()
        count = harvest_google(driver)
        driver.quit()
        
        log(f"🏁 Harvest Complete. Collected {count} new documents.")
        
        if count > 0:
            run_ingestion()
            # push_to_cloud() # Uncomment if you want auto-push
            
    except Exception as e:
        log(f"❌ Critical Error: {e}")