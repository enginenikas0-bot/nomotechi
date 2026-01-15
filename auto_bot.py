import time
import feedparser
import gspread
from google import genai 
from bs4 import BeautifulSoup
import requests
import random
from datetime import datetime, timedelta
import dateutil.parser
import json
import os
import sys
import urllib3

# Απενεργοποίηση προειδοποιήσεων SSL για καθαρό log
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
GCP_CREDENTIALS = os.environ.get("GCP_CREDENTIALS")
SPREADSHEET_NAME = "laws_database"
FETCH_DAYS_LIMIT = 10 
DB_RETENTION_DAYS = 31

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

def fetch_article_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"): return og_image["content"]
    except: return ""
    return ""

def scrape_full_text(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=15, verify=False) 
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]): tag.extract()
            return soup.get_text(separator=" ").strip()[:8000]
    except: return ""
    return ""

def fallback_classify(title, source):
    t, s = title.lower(), source.lower()
    if any(k in s for k in ["michanikos", "b2green", "ypodomes", "tee"]): return "ENG"
    if any(k in s for k in ["dikastiko", "lawspot", "dsa"]): return "LAW"
    if any(k in s for k in ["nomothesia", "taxheaven"]): return "FEK"
    if any(k in t for k in ["δικαστ", "συμβουλιο", "αρεο", "δικηγορ", "αρειο", "αστυνομ"]): return "LAW"
    if any(k in t for k in ["μηχανικ", "εργα", "αυθαιρετ", "δομηση", "ενεργεια", "ακινητ"]): return "ENG"
    if any(k in t for k in ["φεκ", "νομος", "αποφαση"]): return "FEK"
    return "GEN"

def analyze_with_ai(client, title, content, original_summary):
    if not client: return fallback_classify(title, ""), original_summary
    try:
        time.sleep(6) 
        prompt = f"""
        ROLE: Specialized Intelligence Analyst for NomoTech.gr. 
        TASK: Analyze article and assign ALL applicable CATEGORIES (ENG, LAW, FEK, GEN).
        
        KEYWORDS:
        - ENG: Building Permits, Cadastre, Real Estate, Construction, Energy, ΠΕΑ, ΤΕΕ, ΝΟΚ/ΓΟΚ.
        - LAW: Court Rulings, Supreme Court (Άρειος Πάγος), Council of State (ΣτΕ), Litigation, Lawyers.
        - FEK: New Laws, Ministerial Decisions, Circulars (Εγκύκλιοι), Gazette.
        
        STRICT RULES:
        1. ALWAYS include 'ENG' for Real Estate, Property market, Housing, or Construction projects.
        2. MULTITAGGING: Use comma-separated tags (e.g., ENG, LAW) if the topic overlaps.
        3. Professional Greek summary, 120-150 words.
        
        DATA: Title: {title} | Content: {content[:2500]}
        OUTPUT FORMAT: CATEGORIES ||| Summary
        """
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        text = response.text.strip()
        if "|||" in text:
            parts = text.split("|||")
            return parts[0].strip().upper(), parts[1].strip()
        return fallback_classify(title, ""), text
    except Exception as e:
        print(f"⚠️ AI Error: {str(e)[:40]}. Using Fallback.")
        return fallback_classify(title, ""), original_summary

def sort_and_clean_database(worksheet):
    print(f"🧹 Sorting & Cleaning Database ({DB_RETENTION_DAYS} days)...")
    try:
        all_values = worksheet.get_all_values()
        if len(all_values) < 2: return 
        header, data = all_values[0], all_values[1:]
        cutoff = datetime.utcnow() + timedelta(hours=2) - timedelta(days=DB_RETENTION_DAYS)
        cleaned = [row for row in data if datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S") > cutoff]
        cleaned.sort(key=lambda x: x[5])
        worksheet.clear()
        worksheet.append_row(header)
        if cleaned: worksheet.append_rows(cleaned)
        print(f"✅ Kept {len(cleaned)} items.")
    except: pass

def run_scraper():
    print("🚀 NomoTech Bot v2.0.9 (Full Edition) Started...")
    client, worksheet = setup_ai(), setup_db()
    try: existing_links = set(worksheet.col_values(5))
    except: existing_links = set()
    new_rows, current_time = [], datetime.utcnow() + timedelta(hours=2)
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"📡 {source_name}...", end=" ", flush=True)
        try:
            # Δημιουργία Session για να διατηρούμε τα cookies (βοηθάει πολύ σε Michanikos & Capital)
            session = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*'
            }
            
            # Λήψη του περιεχομένου με το Session
            resp = session.get(feed_url, headers=headers, timeout=20, verify=False)
            
            # Έλεγχος αν το site μας έδωσε δεδομένα
            if resp.status_code != 200:
                print(f"❌ HTTP {resp.status_code}")
                continue
                
            feed = feedparser.parse(resp.content)
            
            # Αν το feed είναι άδειο, δοκίμασε εναλλακτικό parsing
            if not feed.entries:
                print("⚠️ Empty Feed")
                continue

            count = 0
            for entry in feed.entries[:40]:
                link = entry.get('link', '')
                if not link or link in existing_links: continue
                
                # Έλεγχος ημερομηνίας
                article_date = get_date_obj(entry)
                if (current_time - article_date).days > FETCH_DAYS_LIMIT: continue
                
                title = entry.get('title', 'No Title')
                
                # Scraping με το ίδιο session για να φαινόμαστε ως ο ίδιος χρήστης
                full_text = scrape_full_text(link) or title
                cat_tag, ai_article = analyze_with_ai(client, title, full_text, entry.get('summary', title))
                img_url = fetch_article_image(link)
                
                new_rows.append([str(hash(link)), source_name, title, ai_article, link, article_date.strftime("%Y-%m-%d %H:%M:%S"), cat_tag, img_url])
                existing_links.add(link)
                count += 1
            print(f"✅ {count}")
        except Exception as e:
            print(f"❌ Error: {str(e)[:20]}")
    if new_rows: worksheet.append_rows(new_rows)
    sort_and_clean_database(worksheet)

if __name__ == "__main__":
    run_scraper()

