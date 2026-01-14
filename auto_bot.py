import time
import feedparser
import gspread
import google.generativeai as genai
from bs4 import BeautifulSoup
import requests
import random
from datetime import datetime, timedelta, timezone
import dateutil.parser
import json
import os
import sys

# --- 1. CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
GCP_CREDENTIALS = os.environ.get("GCP_CREDENTIALS")
SPREADSHEET_NAME = "laws_database"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# --- 2. LIST OF SOURCES (ΜΕ EMOJIS) ---
RSS_FEEDS = {
    # --- ΜΗΧΑΝΙΚΟΙ ---
    "🏗️ Michanikos": "https://www.michanikos.gr/rss/1-news.xml/",
    "🏗️ TEE": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🏗️ B2Green": "https://news.b2green.gr/feed",
    "🏗️ POMIDA": "https://www.pomida.gr/feed/",
    "🏗️ PEDMEDE": "https://www.pedmede.gr/feed/",
    "🏗️ ELINYAE": "https://www.elinyae.gr/rss.xml",
    # --- ΝΟΜΙΚΑ ---
    "⚖️ E-Themis": "https://www.ethemis.gr/feed/",
    "⚖️ Dikastiko": "https://www.dikastiko.gr/feed/",
    "⚖️ Dikastiko Rep": "https://www.dikastikoreportaz.gr/feed/",
    "⚖️ Lawspot": "https://www.lawspot.gr/rss",
    "⚖️ Syntagma": "https://www.syntagmawatch.gr/feed/",
    "⚖️ LawNet": "https://www.lawnet.gr/feed/",
    "⚖️ DSA": "https://www.dsa.gr/rss.xml",
    # --- ΝΟΜΟΘΕΣΙΑ ---
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "📜 Taxheaven": "https://www.taxheaven.gr/rss",
    "💰 Capital": "https://www.capital.gr/rss/roi"
}

def setup_ai():
    if not GEMINI_API_KEY: return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-2.0-flash')
    except: return None

def setup_db():
    if not GCP_CREDENTIALS: sys.exit(1)
    try:
        creds_dict = json.loads(GCP_CREDENTIALS)
        gc = gspread.service_account_from_dict(creds_dict)
        return gc.open(SPREADSHEET_NAME).sheet1
    except: sys.exit(1)

def scrape_full_text(url):
    try:
        # Random Delay πριν το αίτημα στο site για να μην φάμε ban
        time.sleep(random.uniform(1, 3))
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]): tag.extract()
            text = soup.get_text(separator=" ").strip()
            return text[:6000] if len(text) > 50 else ""
    except: return ""
    return ""

def fetch_article_image(url):
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"): return og_image["content"]
    except: return ""
    return ""

def analyze_with_ai(model, title, content):
    # TRASH FILTER
    trash_keywords = ["ολυμπιακος", "παοκ", "αεκ", "παναθηναικος", "τζοκερ", "κληρωση", "survivor", "masterchef", "ζωδια", "gossip", "super league"]
    if any(kw in title.lower() for kw in trash_keywords):
        return "TRASH", "Rejected"

    if not model: return "GEN", "No AI."
    
    try:
        prompt = f"""
        ACT AS A STRICT CLASSIFIER for a Professional Portal.
        
        TASK 1: CLASSIFY into ONE category based ONLY on content/title:
        - ENG: Engineering, Technical Projects, Real Estate, Energy, Public Works, Urban Planning.
        - LAW: Courts, Justice, Lawyers, Criminal/Civil Law, Supreme Court Decisions.
        - FEK: Official Legislation, Gazettes (FEK), Circulars, Ministries Decisions.
        - GEN: Economy, Taxes, Politics (General news).
        - TRASH: Sports, Gambling, Lifestyle, Showbiz, Irrelevant.

        TASK 2: SUMMARIZE in Greek (max 25 words).

        DATA:
        Title: {title}
        Content: {content[:1500] if content else "NO CONTENT - JUDGE BY TITLE ONLY"}

        Output Format: CATEGORY ||| SUMMARY
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "|||" in text:
            parts = text.split("|||")
            return parts[0].strip().upper(), parts[1].strip()
        return "GEN", text
    except: 
        return "GEN", "AI Busy."

def get_greek_time_str(entry):
    try:
        date_str = entry.get('published') or entry.get('pubDate') or entry.get('updated')
        dt = None
        if date_str:
            try: dt = dateutil.parser.parse(date_str)
            except: pass
        
        if not dt and entry.get('published_parsed'):
            dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), timezone.utc)

        if dt:
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc)
                dt = dt.replace(tzinfo=None) + timedelta(hours=2)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except: pass
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

def cleanup_database_safe(worksheet):
    try:
        all_values = worksheet.get_all_values()
        if len(all_values) > 900:
            header = all_values[0]
            data_to_keep = all_values[-700:]
            worksheet.clear()
            worksheet.append_row(header)
            worksheet.append_rows(data_to_keep)
    except: pass

def run_scraper():
    print("🚀 Bot v28 (Anti-Busy Delay) Started...")
    model = setup_ai()
    worksheet = setup_db()
    
    try: existing_links = set(worksheet.col_values(5))
    except: existing_links = set()

    new_rows = []
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"📡 {source_name}...", end=" ", flush=True)
        try:
            feed = feedparser.parse(feed_url)
            count = 0
            for entry in feed.entries[:15]:
                link = entry.get('link', '')
                if link in existing_links: continue
                
                title = entry.get('title', 'No Title')
                pub_date = get_greek_time_str(entry)

                try:
                    full_text = scrape_full_text(link)
                    if len(full_text) < 50: full_text = entry.get('summary', '') or entry.get('description', '')
                    
                    # --- CRITICAL FIX: SLOW DOWN AI ---
                    # Περιμένουμε 4 δευτερόλεπτα ΠΡΙΝ καλέσουμε το AI για να μην φάμε "AI Busy"
                    time.sleep(4) 
                    
                    cat_tag, ai_summary = analyze_with_ai(model, title, full_text)
                    
                    if "TRASH" in cat_tag:
                        existing_links.add(link)
                        print(f"🗑️ Trash: {title}")
                        continue
                    
                    new_row = [str(hash(link)), source_name, title, ai_summary, link, pub_date, cat_tag, fetch_article_image(link)]
                    new_rows.append(new_row)
                    existing_links.add(link)
                    count += 1
                except Exception as e:
                    print(f"⚠️ Skip: {e}")
                    continue
            print(f"✅ {count}")
        except: print("❌")

    if new_rows:
        try:
            worksheet.append_rows(new_rows)
            print(f"💾 Saved {len(new_rows)} items.")
        except: sys.exit(1)
    
    cleanup_database_safe(worksheet)

if __name__ == "__main__":
    run_scraper()
