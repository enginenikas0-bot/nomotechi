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
from urllib.parse import urljoin # Απαραίτητο import στην κορυφή του αρχείου

# Απενεργοποίηση προειδοποιήσεων SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
GCP_CREDENTIALS = os.environ.get("GCP_CREDENTIALS")
SPREADSHEET_NAME = "laws_database"
FETCH_DAYS_LIMIT = 20 
DB_RETENTION_DAYS = 31

RSS_FEEDS = {
    "🏗️ Michanikos": "https://www.michanikos.gr/rss/1-news.xml/",
    "🏗️ TEE": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🏗️ B2Green": "https://news.b2green.gr/feed",
    "🏗️ POMIDA": "https://www.pomida.gr/feed/",
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
    "💰 Capital": "https://www.capital.gr/rss"
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
    except: return datetime.now()


def fetch_article_image(url, session):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = session.get(url, headers=headers, timeout=12, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Λίστα με όλα τα πιθανά Meta Tags
            img_url = ""
            img_tag = (soup.find("meta", property="og:image") or 
                       soup.find("meta", name="twitter:image") or 
                       soup.find("meta", itemprop="image") or
                       soup.find("link", rel="image_src"))
            
            if img_tag:
                img_url = img_tag.get("content") or img_tag.get("href")
            
            # 2. Deep Scan αν το meta tag λείπει
            if not img_url:
                # Ψάχνουμε την πρώτη εικόνα μέσα στο κύριο άρθρο
                main_content = soup.find("article") or soup.find("main") or soup.find("div", class_="content")
                if main_content:
                    first_img = main_content.find("img")
                    if first_img:
                        img_url = first_img.get("src") or first_img.get("data-src") # data-src για lazy loading sites
            
            # 3. Μετατροπή σε πλήρες URL αν είναι relative
            if img_url:
                return urljoin(url, img_url)
                
    except Exception as e:
        print(f"⚠️ Img Error: {str(e)[:20]}")
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

def sort_and_clean_database(worksheet):
    print(f"🧹 Sorting & Cleaning Database...")
    try:
        all_values = worksheet.get_all_values()
        if len(all_values) < 2: return 
        header, data = all_values[0], all_values[1:]
        cutoff = datetime.now() - timedelta(days=DB_RETENTION_DAYS)
        cleaned = [row for row in data if datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S") > cutoff]
        cleaned.sort(key=lambda x: x[5], reverse=True) # Νεότερα πρώτα
        worksheet.clear()
        worksheet.append_row(header)
        if cleaned: worksheet.append_rows(cleaned)
        print(f"✅ Database Processed.")
    except Exception as e: print(f"⚠️ Clean Error: {e}")

def run_scraper():
    print("🚀 NomoTech Bot v2.1.4 (Deep Image Scan) Started...")
    client, worksheet = setup_ai(), setup_db()
    try: existing_links = set(worksheet.col_values(5))
    except: existing_links = set()
    new_rows, current_time = [], datetime.now()
    session = requests.Session()
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"📡 {source_name}...", end=" ", flush=True)
        try:
            headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/rss+xml, application/xml, */*'}
            resp = session.get(f"{feed_url}?v={random.randint(1,999)}", headers=headers, timeout=25, verify=False)
            if resp.status_code != 200:
                print(f"❌ HTTP {resp.status_code}"); continue
                
            feed = feedparser.parse(resp.content)
            count = 0
            for entry in feed.entries[:40]:
                link = entry.get('link', '')
                if not link or link in existing_links: continue
                if (current_time - get_date_obj(entry)).days > FETCH_DAYS_LIMIT: continue
                
                title = entry.get('title', 'No Title')
                full_text = scrape_full_text(link, session) or title
                cat_tag, ai_article = analyze_with_ai(client, title, full_text, entry.get('summary', title))
                img_url = fetch_article_image(link, session)
                
                new_rows.append([str(hash(link)), source_name, title, ai_article, link, get_date_obj(entry).strftime("%Y-%m-%d %H:%M:%S"), cat_tag, img_url])
                existing_links.add(link)
                count += 1
            print(f"✅ {count}")
        except: print("❌ Error")
        
    if new_rows: worksheet.append_rows(new_rows)
    sort_and_clean_database(worksheet)

if __name__ == "__main__":
    run_scraper()

