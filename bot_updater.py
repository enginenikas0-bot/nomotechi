import time
import schedule
import feedparser
import gspread
import google.generativeai as genai
from bs4 import BeautifulSoup
import requests
import random
from datetime import datetime, timedelta
import json
import os

# --- 1. CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "TO_API_KEY_SOU_EDW_AN_TREXEIS_TOPIKA")
SERVICE_ACCOUNT_FILE = "service_account.json"
SPREADSHEET_NAME = "laws_database"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# --- 2. ΠΛΗΡΗΣ ΛΙΣΤΑ ΠΗΓΩΝ ---
RSS_FEEDS = {
    # --- ΜΗΧΑΝΙΚΟΙ / ΚΑΤΑΣΚΕΥΕΣ / ΑΚΙΝΗΤΑ ---
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
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        else:
            json_creds = os.environ.get("GCP_CREDENTIALS")
            if json_creds:
                creds_dict = json.loads(json_creds)
                gc = gspread.service_account_from_dict(creds_dict)
            else:
                return None
        
        sh = gc.open(SPREADSHEET_NAME)
        return sh.sheet1
    except Exception as e:
        print(f"⚠️ DB Error: {e}")
        return None

# --- 4. SCRAPING HELPERS ---
def clean_html(html_text):
    if not html_text: return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ").strip()

def scrape_full_text(url):
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "aside", "header"]): 
                tag.extract()
            paragraphs = soup.find_all('p')
            full_text = " ".join([p.get_text() for p in paragraphs])
            return full_text.strip()[:8000]
    except: 
        return ""
    return ""

def fetch_article_image(url):
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
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
        Είσαι ειδικός αναλυτής (NomoTech Bot). 
        Γράψε μια πολύ σύντομη περίληψη (max 25-30 λέξεις) στα Ελληνικά.
        Εστίασε στην ουσία: Τι αλλάζει, ποια είναι η προθεσμία, ποιον αφορά.
        
        Τίτλος: {title}
        Κείμενο: {content[:2000]}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Η περίληψη δεν είναι διαθέσιμη."

# --- 5. CLEANUP FUNCTION (NEW) ---
def cleanup_database(worksheet):
    """Διαγράφει οριστικά άρθρα παλιότερα των 30 ημερών από το Sheet."""
    print("🧹 Cleaning up old articles...")
    try:
        # 1. Φέρνουμε όλα τα δεδομένα
        all_values = worksheet.get_all_values()
        if not all_values: return

        header = all_values[0]
        rows = all_values[1:]

        # 2. Ορίζουμε το όριο (30 μέρες πριν)
        cutoff_date = datetime.now() - timedelta(days=30)
        kept_rows = []

        # 3. Φιλτράρισμα
        for row in rows:
            try:
                # Η ημερομηνία είναι στη στήλη 6 (index 5)
                row_date_str = row[5]
                row_date = datetime.strptime(row_date_str, "%Y-%m-%d %H:%M:%S")
                
                # Κρατάμε μόνο τα φρέσκα
                if row_date > cutoff_date:
                    kept_rows.append(row)
            except:
                # Αν δεν μπορεί να διαβάσει ημερομηνία, το κρατάμε για ασφάλεια (ή το σβήνουμε)
                # Εδώ επιλέγουμε να το κρατήσουμε μήπως είναι κάτι άλλο
                kept_rows.append(row)

        # 4. Αν υπάρχουν διαγραφές, ξαναγράφουμε το Sheet
        if len(kept_rows) < len(rows):
            deleted_count = len(rows) - len(kept_rows)
            print(f"🗑️ Deleting {deleted_count} old articles...")
            
            # Καθαρισμός και Επανεγγραφή (Πιο ασφαλές από delete_rows σε loop)
            worksheet.clear()
            worksheet.append_row(header)
            if kept_rows:
                worksheet.append_rows(kept_rows)
            print("✨ Database optimized.")
        else:
            print("✨ No old articles to delete.")

    except Exception as e:
        print(f"⚠️ Cleanup Error: {e}")

# --- 6. MAIN JOB ---
def run_scraper():
    print(f"🔄 Starting Scraping Cycle: {datetime.now().strftime('%H:%M:%S')}")
    
    model = setup_ai()
    worksheet = setup_db()
    
    if not worksheet:
        print("❌ Database connection failed.")
        return

    # Φόρτωσε τα ήδη υπάρχοντα links
    try:
        existing_links = set(worksheet.col_values(5)) 
    except:
        existing_links = set()

    new_rows = []
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"📡 {source_name}...", end=" ", flush=True)
        try:
            feed = feedparser.parse(feed_url)
            count = 0
            
            # Έλεγχος 10 άρθρων ανά πηγή
            for entry in feed.entries[:10]:
                link = entry.get('link', '')
                
                if link in existing_links:
                    continue 
                
                title = entry.get('title', 'No Title')
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
                    source_name, # Category placeholder
                    real_image_url
                ]
                
                new_rows.append(new_row)
                existing_links.add(link)
                count += 1
                time.sleep(1)
                
            print(f"✅ Found {count}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

    # Αποθήκευση νέων
    if new_rows:
        try:
            worksheet.append_rows(new_rows)
            print(f"💾 Saved {len(new_rows)} new articles.")
        except Exception as e:
            print(f"❌ Error saving to DB: {e}")
    else:
        print("💤 No new articles.")

    # --- ΤΡΕΧΟΥΜΕ ΤΟΝ ΚΑΘΑΡΙΣΜΟ ΣΤΟ ΤΕΛΟΣ ΚΑΘΕ ΚΥΚΛΟΥ ---
    cleanup_database(worksheet)

# --- 7. SCHEDULER ---
schedule.every().day.at("08:00").do(run_scraper)
schedule.every().day.at("10:00").do(run_scraper)
schedule.every().day.at("13:00").do(run_scraper)
schedule.every().day.at("15:00").do(run_scraper)
schedule.every().day.at("18:00").do(run_scraper)
schedule.every().day.at("21:00").do(run_scraper)
schedule.every().day.at("23:30").do(run_scraper)

if __name__ == "__main__":
    print("🤖 NomoTech Autobot v13 (Auto-Cleanup) Started...")
    run_scraper()
    while True:
        schedule.run_pending()
        time.sleep(60)
