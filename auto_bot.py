import time
import feedparser
import gspread
import google.generativeai as genai
from bs4 import BeautifulSoup
import requests
import random
from datetime import datetime
import json
import os
import sys

# --- 1. CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "TO_API_KEY_SOU_EDW_AN_TREXEIS_TOPIKA")
SERVICE_ACCOUNT_FILE = "service_account.json"
SPREADSHEET_NAME = "laws_database"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# --- 2. LIST OF SOURCES ---
RSS_FEEDS = {
    # --- ΜΗΧΑΝΙΚΟΙ / ΚΑΤΑΣΚΕΥΕΣ ---
    "Michanikos": "https://www.michanikos.gr/rss/1-news.xml/",
    "TEE": "https://web.tee.gr/feed/",
    "Ypodomes": "https://ypodomes.com/feed/",
    "B2Green": "https://news.b2green.gr/feed",
    "POMIDA": "https://www.pomida.gr/feed/",
    "PEDMEDE": "https://www.pedmede.gr/feed/",
    "ELINYAE": "https://www.elinyae.gr/rss.xml",

    # --- ΝΟΜΙΚΑ & ΔΙΚΑΙΟΣΥΝΗ ---
    "E-Themis": "https://www.ethemis.gr/feed/",
    "Dikastiko": "https://www.dikastiko.gr/feed/",
    "Dikastiko Rep": "https://www.dikastikoreportaz.gr/feed/",
    "Lawspot": "https://www.lawspot.gr/rss",
    "Syntagma Watch": "https://www.syntagmawatch.gr/feed/",
    "LawNet": "https://www.lawnet.gr/feed/",
    "DSA": "https://www.dsa.gr/rss.xml",

    # --- ΝΟΜΟΘΕΣΙΑ & ΟΙΚΟΝΟΜΙΑ ---
    "E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "Taxheaven": "https://www.taxheaven.gr/rss",
    "Capital": "https://www.capital.gr/rss/oikonomia"
}

# --- 3. SETUP ---
def setup_ai():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return None

def setup_db():
    try:
        # Check environment variable first (Cloud)
        json_creds = os.environ.get("GCP_CREDENTIALS")
        if json_creds:
            creds_dict = json.loads(json_creds)
            gc = gspread.service_account_from_dict(creds_dict)
        elif os.path.exists(SERVICE_ACCOUNT_FILE):
            # Check local file (Local PC)
            gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        else:
            print("❌ No Credentials found!")
            return None
        
        sh = gc.open(SPREADSHEET_NAME)
        return sh.sheet1
    except Exception as e:
        print(f"⚠️ DB Error: {e}")
        return None

# --- 4. HELPERS ---
def clean_html(html_text):
    if not html_text: return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ").strip()

def scrape_full_text(url):
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "aside", "header"]): 
                tag.extract()
            paragraphs = soup.find_all('p')
            full_text = " ".join([p.get_text() for p in paragraphs])
            return full_text.strip()[:5000] # Safe limit
    except: 
        return ""
    return ""

def fetch_article_image(url):
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"): 
                return og_image["content"]
    except: 
        return ""
    return ""

def get_ai_summary(model, title, content):
    if not model: return "AI unavailable."
    try:
        prompt = f"""
        Γράψε περίληψη (max 30 λέξεις) στα Ελληνικά. 
        Τίτλος: {title}
        Κείμενο: {content[:1500]}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Περίληψη μη διαθέσιμη."

# --- 5. CLEANUP ---
def cleanup_database_safe(worksheet):
    print("🧹 Cleaning database...")
    try:
        all_values = worksheet.get_all_values()
        total_rows = len(all_values)
        MAX_ROWS = 700 # Αυξημένο όριο λόγω των 10 άρθρων
        KEEP_ROWS = 600
        
        if total_rows > MAX_ROWS:
            print(f"⚠️ Limit reached ({total_rows}). Trimming to {KEEP_ROWS}...")
            header = all_values[0]
            data_to_keep = all_values[-KEEP_ROWS:]
            worksheet.clear()
            worksheet.append_row(header)
            worksheet.append_rows(data_to_keep)
            print("✨ Database optimized.")
        else:
            print("✅ Database size OK.")
    except Exception as e:
        print(f"⚠️ Cleanup skipped: {e}")

# --- 6. MAIN JOB ---
def run_scraper():
    print(f"🚀 Job Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    model = setup_ai()
    worksheet = setup_db()
    
    if not worksheet:
        print("❌ CRITICAL: No DB Connection. Exiting.")
        sys.exit(1) # Force Error for GitHub Actions to see

    try:
        existing_links = set(worksheet.col_values(5)) 
    except:
        existing_links = set()

    new_rows = []
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"📡 Scanning {source_name}...", end=" ", flush=True)
        try:
            feed = feedparser.parse(feed_url)
            count = 0
            
            # Επαναφορά στο 10 (Max Volume)
            for entry in feed.entries[:10]:
                link = entry.get('link', '')
                
                if link in existing_links:
                    continue 
                
                title = entry.get('title', 'No Title')
                
                try:
                    full_text = scrape_full_text(link)
                    if len(full_text) < 50: 
                        full_text = clean_html(entry.get('summary', '') or entry.get('description', ''))
                    
                    real_image_url = fetch_article_image(link)
                    ai_summary = get_ai_summary(model, title, full_text)
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    new_row = [
                        str(hash(link)),
                        source_name,
                        title,
                        ai_summary,
                        link,
                        now_str,
                        source_name, 
                        real_image_url
                    ]
                    
                    new_rows.append(new_row)
                    existing_links.add(link)
                    count += 1
                except Exception:
                    continue
                
            print(f"✅ Found: {count}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

    if new_rows:
        try:
            worksheet.append_rows(new_rows)
            print(f"💾 SUCCESS: Saved {len(new_rows)} new articles.")
        except Exception as e:
            print(f"❌ DB Write Error: {e}")
    else:
        print("💤 No new content found.")

    cleanup_database_safe(worksheet)
    print("🏁 Job Finished Successfully.")

# --- 7. EXECUTION (NO LOOP) ---
if __name__ == "__main__":
    # Τρέχει ΜΙΑ φορά και σταματάει (Ιδανικό για GitHub Actions με όριο 10 άρθρα)
    run_scraper()
