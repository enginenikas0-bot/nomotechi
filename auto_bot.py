import time
import feedparser
import gspread
import google.generativeai as genai
from bs4 import BeautifulSoup
import requests
import random
from datetime import datetime, timedelta
import json
import os
import sys

# --- 1. CONFIGURATION ---
# Παίρνουμε τα κλειδιά από τα Secrets του GitHub
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
GCP_CREDENTIALS = os.environ.get("GCP_CREDENTIALS")

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
    "Capital": "https://www.capital.gr/rss/roi"
}

# --- 3. SETUP ---
def setup_ai():
    if not GEMINI_API_KEY:
        print("⚠️ WARNING: Gemini API Key missing. Summaries will be empty.")
        return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return None

def setup_db():
    print("🔌 Connecting to Google Sheets...")
    if not GCP_CREDENTIALS:
        print("❌ CRITICAL ERROR: GCP_CREDENTIALS Secret is missing!")
        sys.exit(1) # ΣΤΑΜΑΤΑΕΙ ΤΟ RUN ΜΕ ΚΟΚΚΙΝΟ
    
    try:
        creds_dict = json.loads(GCP_CREDENTIALS)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open(SPREADSHEET_NAME)
        print("✅ Connected to Spreadsheet successfully.")
        return sh.sheet1
    except Exception as e:
        print(f"❌ DATABASE CONNECTION FAILED: {e}")
        print("💡 HINT: Check if your JSON in GitHub Secrets is correct.")
        sys.exit(1) # ΣΤΑΜΑΤΑΕΙ ΤΟ RUN ΜΕ ΚΟΚΚΙΝΟ

# --- 4. HELPERS ---
def clean_html(html_text):
    if not html_text: return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ").strip()

def scrape_full_text(url):
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10) # Increased timeout
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "aside", "header"]): 
                tag.extract()
            paragraphs = soup.find_all('p')
            full_text = " ".join([p.get_text() for p in paragraphs])
            return full_text.strip()[:6000]
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

def analyze_with_ai(model, title, content):
    """
    STRICT AI TAGGING
    """
    if not model: return "GEN", "Περίληψη μη διαθέσιμη (No AI)."
    try:
        prompt = f"""
        Act as a classifier for a Greek Technical & Legal Portal.
        1. CLASSIFY this article into ONE category:
           - ENG (Engineering, Construction, Real Estate, Technical Projects)
           - LAW (Courts, Justice, Lawyers, Criminal/Civil Law)
           - FEK (Official Government Gazette, Legislation, Decisions)
           - GEN (General News, Economy)
        
        2. SUMMARIZE in Greek (max 25 words).

        INPUT:
        Title: {title}
        Text: {content[:1500]}

        OUTPUT FORMAT:
        CATEGORY ||| SUMMARY
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if "|||" in text:
            parts = text.split("|||")
            cat = parts[0].strip().upper()
            summary = parts[1].strip()
            valid_tags = ["ENG", "LAW", "FEK", "GEN"]
            if not any(v in cat for v in valid_tags): cat = "GEN"
            return cat, summary
        else:
            return "GEN", text
    except:
        return "GEN", "AI Busy."

# --- 5. CLEANUP ---
def cleanup_database_safe(worksheet):
    # Κρατάει τη βάση καθαρή αλλά δεν σβήνει τα πάντα
    try:
        all_values = worksheet.get_all_values()
        if len(all_values) > 900:
            print("🧹 Trimming database...")
            header = all_values[0]
            data_to_keep = all_values[-700:] # Keep last 700
            worksheet.clear()
            worksheet.append_row(header)
            worksheet.append_rows(data_to_keep)
    except Exception as e:
        print(f"⚠️ Cleanup Warning: {e}")

# --- 6. MAIN JOB ---
def run_scraper():
    print(f"🚀 Job Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Setup Phase
    model = setup_ai()
    worksheet = setup_db() # Αυτό θα κρασάρει αν δεν συνδεθεί (σωστό!)

    # 2. Load Existing Links to avoid duplicates
    try:
        existing_links = set(worksheet.col_values(5)) 
        print(f"📚 Loaded {len(existing_links)} existing articles from DB.")
    except:
        existing_links = set()
        print("⚠️ Could not load existing links. Starting fresh check.")

    new_rows = []
    
    # 3. Scanning Loop
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"📡 Scanning {source_name}...", end=" ", flush=True)
        try:
            feed = feedparser.parse(feed_url)
            count = 0
            
            # Scan 15 articles per source
            for entry in feed.entries[:15]:
                link = entry.get('link', '')
                
                # DUPLICATE CHECK
                if link in existing_links:
                    continue 
                
                title = entry.get('title', 'No Title')
                
                try:
                    # Get Content
                    full_text = scrape_full_text(link)
                    if len(full_text) < 50: 
                        full_text = clean_html(entry.get('summary', '') or entry.get('description', ''))
                    
                    real_image_url = fetch_article_image(link)
                    
                    # AI Analysis
                    cat_tag, ai_summary = analyze_with_ai(model, title, full_text)
                    
                    # Time Fix (+2 hours for Greece)
                    now_obj = datetime.utcnow() + timedelta(hours=2) 
                    now_str = now_obj.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Prepare Row
                    # ID | Source | Title | Content | Link | Time | Category | Image
                    new_row = [
                        str(hash(link)),
                        source_name,
                        title,
                        ai_summary,
                        link,
                        now_str,
                        cat_tag,
                        real_image_url
                    ]
                    
                    new_rows.append(new_row)
                    existing_links.add(link) # Add to local set immediately
                    count += 1
                except Exception as e:
                    # Skip problematic article, move to next
                    continue
                
            print(f"✅ Found {count} new.")
                
        except Exception as e:
            print(f"❌ Feed Error: {e}")

    # 4. Saving Phase
    if new_rows:
        print(f"💾 Saving {len(new_rows)} articles to Google Sheets...")
        try:
            worksheet.append_rows(new_rows)
            print("✅ SUCCESS: Database Updated!")
        except Exception as e:
            print(f"❌ WRITE ERROR: Could not write to Google Sheets. {e}")
            sys.exit(1) # ΚΟΚΚΙΝΟ αν αποτύχει η εγγραφή
    else:
        print("💤 No new content found in any source.")

    # 5. Cleanup Phase
    cleanup_database_safe(worksheet)
    print("🏁 Finished.")

if __name__ == "__main__":
    run_scraper()
