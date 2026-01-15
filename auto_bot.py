import time
import feedparser
import gspread
from google import genai 
from bs4 import BeautifulSoup
import requests
import random
from datetime import datetime, timedelta
import json
import os
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
GCP_CREDENTIALS = os.environ.get("GCP_CREDENTIALS")
SPREADSHEET_NAME = "laws_database"
FETCH_DAYS_LIMIT = 20 
DB_RETENTION_DAYS = 31

# ΕΠΙΚΑΙΡΟΠΟΙΗΜΕΝΑ RSS URLS (V2.1.2)
RSS_FEEDS = {
    "🏗️ Michanikos": "https://www.michanikos.gr/rss/1-news.xml/",
    "🏗️ TEE": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🏗️ B2Green": "https://news.b2green.gr/feed",
    "🏗️ POMIDA": "https://www.pomida.gr/feed/", # Διορθωμένο
    "🏗️ PEDMEDE": "https://pedmede.gr/feed/",
    "🏗️ ELINYAE": "https://www.elinyae.gr/rss.xml",
    "⚖️ E-Themis": "https://www.ethemis.gr/feed/", 
    "⚖️ Dikastiko": "https://www.dikastiko.gr/feed/",
    "⚖️ Dikastiko Rep": "https://www.dikastikoreportaz.gr/feed/",
    "⚖️ Lawspot": "https://www.lawspot.gr/rss",
    "⚖️ Syntagma": "https://www.syntagmawatch.gr/feed/",
    "⚖️ LawNet": "https://www.lawnet.gr/feed/",
    "⚖️ DSA": "https://www.dsa.gr/rss.xml",
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "📜 Taxheaven": "https://www.taxheaven.gr/rss", 
    "💰 Capital": "https://www.capital.gr/rss" # Διορθωμένο
}

def setup_ai():
    if not GEMINI_API_KEY: return None
    try: return genai.Client(api_key=GEMINI_API_KEY)
    except: return None

def setup_db():
    if not GCP_CREDENTIALS: sys.exit(1)
    try:
        creds_dict = json.loads(GCP_CREDENTIALS)
        gc = gspread.service_account_from_dict(creds_dict)
        return gc.open(SPREADSHEET_NAME).sheet1
    except: sys.exit(1)

def get_date_obj(entry):
    try:
        dt = datetime.now()
        if entry.get('published_parsed'): dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        elif entry.get('updated_parsed'): dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
        return dt + timedelta(hours=2)
    except: return datetime.utcnow() + timedelta(hours=2)

# ΕΝΙΣΧΥΜΕΝΟ IMAGE SCRAPING ΜΕ SESSION
def fetch_article_image(url, session):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = session.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Έλεγχος og:image, twitter:image και main article images
            img = soup.find("meta", property="og:image") or soup.find("meta", name="twitter:image")
            if img and img.get("content"): return img["content"]
            # Fallback στην πρώτη μεγάλη εικόνα του άρθρου
            main_img = soup.find("article").find("img") if soup.find("article") else None
            if main_img and main_img.get("src"): return main_img["src"]
    except: return ""
    return ""

def scrape_full_text(url, session):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = session.get(url, headers=headers, timeout=15, verify=False) 
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]): tag.extract()
            return soup.get_text(separator=" ").strip()[:8000]
    except: return ""
    return ""

def analyze_with_ai(client, title, content, original_summary):
    if not client: return "GEN", original_summary
    try:
        time.sleep(6) 
        prompt = f"Role: Senior Industry Analyst. Classify (ENG, LAW, FEK, GEN) and summarize in Greek: {title}. Content: {content[:2500]}. Format: CAT ||| Summary"
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        text = response.text.strip()
        if "|||" in text:
            parts = text.split("|||")
            return parts[0].strip().upper(), parts[1].strip()
        return "GEN", text
    except: return "GEN", original_summary

def run_scraper():
    print("🚀 NomoTech Bot v2.1.2 (Session Image Fix) Started...")
    client, worksheet = setup_ai(), setup_db()
    try: existing_links = set(worksheet.col_values(5))
    except: existing_links = set()
    new_rows, current_time = [], datetime.utcnow() + timedelta(hours=2)
    
    session = requests.Session() # Ενιαίο session για όλο το run
    
    for source_name, feed_url in RSS_FEEDS.items():
        # Cache Buster
        final_url = f"{feed_url}?nocache={random.randint(1, 9999)}"
        print(f"📡 {source_name}...", end=" ", flush=True)
        try:
            headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/rss+xml, application/xml, */*'}
            resp = session.get(final_url, headers=headers, timeout=25, verify=False)
            
            if resp.status_code != 200:
                print(f"❌ HTTP {resp.status_code}")
                continue
                
            feed = feedparser.parse(resp.content)
            count = 0
            for entry in feed.entries[:40]:
                link = entry.get('link', '')
                if not link or link in existing_links: continue
                if (current_time - get_date_obj(entry)).days > FETCH_DAYS_LIMIT: continue
                
                title = entry.get('title', 'No Title')
                # Χρήση Session και για το κείμενο και για την εικόνα
                full_text = scrape_full_text(link, session) or title
                cat_tag, ai_article = analyze_with_ai(client, title, full_text, entry.get('summary', title))
                img_url = fetch_article_image(link, session)
                
                new_rows.append([str(hash(link)), source_name, title, ai_article, link, get_date_obj(entry).strftime("%Y-%m-%d %H:%M:%S"), cat_tag, img_url])
                existing_links.add(link)
                count += 1
            print(f"✅ {count}")
        except Exception as e: print(f"❌ Error")
        
    if new_rows: worksheet.append_rows(new_rows)

if __name__ == "__main__":
    run_scraper()
