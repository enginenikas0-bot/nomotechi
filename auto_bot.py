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

# ΑΥΣΤΗΡΟ ΟΡΙΟ: Αγνοούμε άρθρα παλιότερα από 2 ημέρες
# Αυτό προστατεύει το όριο (Quota) όταν διαβάζουμε 15 άρθρα/πηγή
DAYS_LIMIT = 2

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

RSS_FEEDS = {
    "🏗️ Michanikos": "https://www.michanikos.gr/rss/1-news.xml/",
    "🏗️ TEE": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🏗️ B2Green": "https://news.b2green.gr/feed",
    "🏗️ POMIDA": "https://www.pomida.gr/feed/",
    "🏗️ PEDMEDE": "https://www.pedmede.gr/feed/",
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
    "💰 Capital": "https://www.capital.gr/rss/roi"
}

def setup_ai():
    if not GEMINI_API_KEY: return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Χρησιμοποιούμε το δυνατό Gemini 2.0 Flash
        return genai.GenerativeModel('gemini-2.0-flash')
    except: return None

def setup_db():
    if not GCP_CREDENTIALS: sys.exit(1)
    try:
        creds_dict = json.loads(GCP_CREDENTIALS)
        gc = gspread.service_account_from_dict(creds_dict)
        return gc.open(SPREADSHEET_NAME).sheet1
    except: sys.exit(1)

def get_date_obj(entry):
    """Εξάγει την ημερομηνία με ασφάλεια"""
    try:
        if entry.get('published_parsed'):
            return datetime.fromtimestamp(time.mktime(entry.published_parsed))
        date_str = entry.get('published') or entry.get('pubDate') or entry.get('updated')
        if date_str:
            return dateutil.parser.parse(date_str, fuzzy=True).replace(tzinfo=None)
    except: pass
    return datetime.now() 

def scrape_full_text(url):
    try:
        time.sleep(random.uniform(1, 2))
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]): tag.extract()
            text = soup.get_text(separator=" ").strip()
            return text[:8000] if len(text) > 50 else ""
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

# --- BACKUP LOGIC (Αλεξίπτωτο) ---
def fallback_classify(title, source):
    """Κατηγοριοποίηση ανάγκης αν το AI είναι Busy"""
    t = title.lower()
    s = source.lower()
    
    # 1. Βάσει Πηγής
    if "michanikos" in s or "b2green" in s or "ypodomes" in s or "tee" in s: return "ENG"
    if "dikastiko" in s or "lawspot" in s or "dsa" in s: return "LAW"
    if "nomothesia" in s or "taxheaven" in s: return "FEK"
    
    # 2. Βάσει Λέξεων
    if any(k in t for k in ["δικαστ", "συμβουλιο", "αρεο", "δικηγορ"]): return "LAW"
    if any(k in t for k in ["μηχανικ", "εργα", "αυθαιρετ", "δομηση", "ενεργεια"]): return "ENG"
    if any(k in t for k in ["φεκ", "νομος", "αποφαση", "εγκυκλιος"]): return "FEK"
    
    return "GEN"

def analyze_with_ai(model, title, content, original_summary):
    # Trash Filter
    trash_keywords = ["ολυμπιακος", "παοκ", "αεκ", "παναθηναικος", "τζοκερ", "κληρωση", "survivor", "masterchef", "ζωδια", "gossip", "super league"]
    if any(kw in title.lower() for kw in trash_keywords):
        return "TRASH", "Rejected"

    if not model: 
        return fallback_classify(title, ""), original_summary
    
    try:
        prompt = f"""
        ROLE: Senior Analyst.
        TASK: Classify and Summarize in Greek.
        
        CATEGORIES (Select ALL that apply, comma-separated):
        - ENG: Engineering/Real Estate.
        - LAW: Legal/Courts.
        - FEK: Legislation/Gazette.
        - GEN: General/Economy.
        
        SUMMARY: Professional, 80-100 words, with dates/amounts.
        
        DATA:
        Title: {title}
        Content: {content[:2000]}
        
        Format: CAT1, CAT2 ||| [SUMMARY]
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "|||" in text:
            parts = text.split("|||")
            return parts[0].strip().upper(), parts[1].strip()
        return fallback_classify(title, ""), text 
        
    except Exception:
        # Αν "σκάσει" το AI, γυρνάμε στο Fallback χωρίς να σταματήσουμε
        print("⚠️ AI Busy/Quota Exceeded. Using Fallback.")
        return fallback_classify(title, ""), (original_summary if len(original_summary) > 10 else "Δεν υπάρχει διαθέσιμη περίληψη.")

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
    print(f"🚀 Bot v41 (Masterplan: 15 items/feed) Started...")
    model = setup_ai()
    worksheet = setup_db()
    
    try: existing_links = set(worksheet.col_values(5))
    except: existing_links = set()

    new_rows = []
    current_time = datetime.now()
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"📡 {source_name}...", end=" ", flush=True)
        try:
            feed = feedparser.parse(feed_url)
            count = 0
            
            # --- ΕΔΩ Η ΑΛΛΑΓΗ: 15 ΑΡΘΡΑ ---
            for entry in feed.entries[:15]:
                link = entry.get('link', '')
                if link in existing_links: continue
                
                # DATE FILTER: Απορρίπτουμε τα παλιά για να μην καίμε τζάμπα AI
                article_dt = get_date_obj(entry)
                if (current_time - article_dt).days > DAYS_LIMIT:
                    continue

                title = entry.get('title', 'No Title')
                pub_date_str = article_dt.strftime("%Y-%m-%d %H:%M:%S")
                rss_summary = entry.get('summary', '') or entry.get('description', '') or title

                try:
                    full_text = scrape_full_text(link)
                    if len(full_text) < 50: full_text = rss_summary
                    
                    time.sleep(6) 
                    
                    cat_tag, ai_article = analyze_with_ai(model, title, full_text, rss_summary)
                    
                    # Extra check αν το AI επέστρεψε κενή κατηγορία
                    if cat_tag == "GEN" or cat_tag == "":
                         cat_tag = fallback_classify(title, source_name)

                    if "TRASH" in cat_tag:
                        existing_links.add(link)
                        print(f"🗑️ Trash: {title}")
                        continue
                    
                    new_row = [str(hash(link)), source_name, title, ai_article, link, pub_date_str, cat_tag, fetch_article_image(link)]
                    new_rows.append(new_row)
                    existing_links.add(link)
                    count += 1
                except Exception as e: 
                    print(f"Skipping: {e}")
                    continue
            print(f"✅ {count} (Fresh)")
        except: print("❌")

    if new_rows:
        try:
            worksheet.append_rows(new_rows)
            print(f"💾 Saved {len(new_rows)} items.")
        except: sys.exit(1)
    
    cleanup_database_safe(worksheet)

if __name__ == "__main__":
    run_scraper()
