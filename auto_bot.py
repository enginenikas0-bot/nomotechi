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
from urllib.parse import urljoin 

# Απενεργοποίηση προειδοποιήσεων SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
GCP_CREDENTIALS = os.environ.get("GCP_CREDENTIALS")
SPREADSHEET_NAME = "laws_database"
FETCH_DAYS_LIMIT = 20 
DB_RETENTION_DAYS = 31

# RSS URLS 
RSS_FEEDS = {
    "🏗️ Michanikos": "https://www.michanikos.gr/rss/1-news.xml/",
    "🏗️ TEE": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🏗️ B2Green": "https://news.b2green.gr/feed",
    "🏗️ PEDMEDE": "https://pedmede.gr/feed/",
    "🏗️ ELINYAE": "https://www.elinyae.gr/rss.xml",
    "⚖️ Dikastiko": "https://www.dikastiko.gr/feed/",
    "⚖️ Dikastiko Rep": "https://www.dikastikoreportaz.gr/feed/",
    "⚖️ Syntagma": "https://www.syntagmawatch.gr/feed/",
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

# --- Η ΣΥΝΑΡΤΗΣΗ ΠΟΥ ΕΛΕΙΠΕ (Κρίσιμη για να μην κρασάρει) ---
def fallback_classify(title, source):
    """Backup classification logic if AI fails"""
    t = title.lower()
    # ENG keywords
    if any(k in t for k in ["μηχανικ", "εργα", "αυθαιρετ", "δομηση", "ενεργεια", "ακινητ", "ktimatologio", "τεε", "οικοδομ", "εξοικονομ"]): return "ENG"
    # LAW keywords
    if any(k in t for k in ["δικαστ", "συμβουλιο", "αρεο", "δικηγορ", "αρειο", "αστυνομ", "νομικ", "δσα", "στε"]): return "LAW"
    # FEK keywords
    if any(k in t for k in ["φεκ", "νομος", "αποφαση", "εγκυκλιος", "τροπολογια", "ααδε"]): return "FEK"
    return "GEN"

def fetch_article_image(url, session):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = session.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            img_url = ""
            
            # 1. Meta Tags 
            meta = soup.find("meta", attrs={"property": "og:image"})
            if meta: img_url = meta.get("content")
            
            if not img_url:
                meta = soup.find("meta", attrs={"name": "twitter:image"})
                if meta: img_url = meta.get("content")

            if not img_url:
                meta = soup.find("meta", attrs={"itemprop": "image"})
                if meta: img_url = meta.get("content")

            if not img_url:
                link = soup.find("link", attrs={"rel": "image_src"})
                if link: img_url = link.get("href")
            
            # 2. Deep Scan
            if not img_url:
                main_content = soup.find("article") or soup.find("main") or soup.find("div", class_="post-content") or soup.find("div", class_="entry-content")
                if main_content:
                    first_img = main_content.find("img")
                    if first_img:
                        img_url = first_img.get("src") or first_img.get("data-src")
            
            # 3. Absolute URL
            if img_url: return urljoin(url, img_url)
                
    except Exception as e:
        print(f"⚠️ Img Error: {str(e)[:20]}") 
    return ""

def scrape_full_text(url, session):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/'
        }
        response = session.get(url, headers=headers, timeout=15, verify=False) 
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]): tag.extract()
            return soup.get_text(separator=" ").strip()[:8000]
    except: return ""
    return ""

def analyze_with_ai(client, title, content, original_summary):
    if not client: return fallback_classify(title, ""), original_summary
    try:
        time.sleep(6) 
        # --- ΤΟ PROMPT ΠΑΡΑΜΕΝΕΙ ΑΚΡΙΒΩΣ ΙΔΙΟ (ΔΕΝ ΑΛΛΑΖΕΙ ΤΙΠΟΤΑ ΕΔΩ) ---
        prompt = f"""
        ROLE: Specialized Intelligence Analyst for NomoTech.gr.
        TASK: Analyze article and assign ALL applicable CATEGORIES (ENG, LAW, FEK, GEN). 
        STRICT PRIORITY: Always include 'ENG' for Property, Housing Market, Construction, or Engineering.
        
        TAXONOMY & KEYWORDS (EXPANDED):
        
        1. [ENG] - ENGINEERING, REAL ESTATE & CONSTRUCTION:
           - Real Estate: Αγορά Ακινήτων, Αντικειμενικές Αξίες, ΕΝΦΙΑ, Μεταβιβάσεις, Συμβόλαια, Golden Visa, Airbnb/Βραχυχρόνια, Πλειστηριασμοί Ακινήτων, Στεγαστική Πολιτική, Ενοίκια.
           - Urban Planning (Πολεοδομία): Εκτός Σχεδίου Δόμηση, Χρήσεις Γης, Ρυμοτομικό, Δασικοί Χάρτες, Κτηματολόγιο (Cadastre), Κτηματογράφηση.
           - Construction/Technical: Οικοδομική Άδεια, ΝΟΚ (Νέος Οικοδομικός Κανονισμός), ΓΟΚ, Αυθαίρετα (Τακτοποίηση), Ηλεκτρονική Ταυτότητα Κτιρίου (ΗΤΚ), Εξοικονομώ, Ενεργειακή Αναβάθμιση (ΠΕΑ), ΑΠΕ (Φωτοβολταϊκά).
           - Infrastructure: Δημόσια Έργα, Διαγωνισμοί, ΣΔΙΤ, Αναδοχές, Υποδομές (Μετρό, Δρόμοι), Εργοληπτικά Πτυχία.
           - Professional: ΤΕΕ (Τεχνικό Επιμελητήριο), Μηχανικοί, Αρχιτέκτονες, Εργολήπτες.

        2. [LAW] - LEGAL, JUSTICE & COURTS:
           - Courts (Δικαστήρια): Συμβούλιο της Επικρατείας (ΣτΕ), Άρειος Πάγος, Ελεγκτικό Συνέδριο, Διοικητικό Εφετείο, Πρωτοδικείο, Ειρηνοδικείο.
           - Jurisprudence (Νομολογία): Δικαστικές Αποφάσεις, Αναίρεση, Έφεση, Αγωγή, Ασφαλιστικά Μέτρα, Προσωρινή Διαταγή.
           - Areas of Law: Αστικό Δίκαιο (Κληρονομικά, Οικογενειακό), Ποινικό, Εργατικό (Αποζημιώσεις, Απολύσεις), Εμπορικό (Πτωχεύσεις, Εξυγίανση, Κόκκινα Δάνεια).
           - Professional: Δικηγόροι, Δικηγορικός Σύλλογος (ΔΣΑ, ΔΣΘ), Συμβολαιογράφοι, Δικαστικοί Επιμελητές, Ολομέλεια Δικηγορικών Συλλόγων.

        3. [FEK] - LEGISLATION & GAZETTE:
           - Official Acts: ΦΕΚ (Government Gazette), Νόμος (Law), Προεδρικό Διάταγμα (ΠΔ), Υπουργική Απόφαση (ΚΥΑ/ΥΑ), Εγκύκλιος, Τροπολογία, Πολυνομοσχέδιο.
           - Authorities: ΑΑΔΕ (Tax Authority), Υπουργείο Οικονομικών, Υπουργείο Περιβάλλοντος (ΥΠΕΝ), Βουλή.

        INSTRUCTIONS:
        - If an article mentions a "Court Ruling on Arbitrary Buildings" (ΣτΕ για Αυθαίρετα) -> TAG: ENG, LAW.
        - If an article is about "New Tax Law for Lawyers" -> TAG: LAW, FEK.
        - If an article is about "Golden Visa changes" -> TAG: ENG, FEK.
        
        SUMMARY: Professional Greek, 120-150 words. Focus on the impact for professionals.
        
        Title: {title} | Content: {content[:2500]}
        OUTPUT: CATEGORIES (comma-separated) ||| Summary
        """
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        text = response.text.strip()
        
        # --- ΕΔΩ ΕΙΝΑΙ Η ΜΟΝΗ ΑΛΛΑΓΗ (PARSING FIX) ---
        # 1. Καθαρισμός από "σκουπίδια" που βάζει το AI (π.χ. "Output: ENG")
        clean_text = text.replace("Category:", "").replace("Output:", "").replace("Tags:", "").strip()
        
        if "|||" in clean_text:
            parts = clean_text.split("|||")
            return parts[0].strip().upper(), parts[1].strip()
            
        # 2. Fail-safe: Αν το AI ξέχασε το ||| αλλά έγραψε ENG στην αρχή
        if clean_text.startswith("ENG") or clean_text.startswith("LAW") or clean_text.startswith("FEK"):
            # Παίρνουμε τα πρώτα γράμματα ως Tag και το υπόλοιπο ως κείμενο
            # π.χ. "ENG, LAW Αυτό είναι το κείμενο..."
            split_point = max(clean_text.find(" "), clean_text.find(":"))
            if split_point > 0:
                possible_tag = clean_text[:split_point].strip(" .:-").upper()
                possible_summary = clean_text[split_point:].strip(" .:-")
                return possible_tag, possible_summary

        # Αν αποτύχουν όλα, fallback
        return fallback_classify(title, ""), clean_text
        
    except Exception as e:
        print(f"⚠️ AI Error: {str(e)[:50]}. Using Fallback.")
        return fallback_classify(title, ""), original_summary

def sort_and_clean_database(worksheet):
    print(f"🧹 Sorting & Cleaning Database ({DB_RETENTION_DAYS} days)...")
    try:
        all_values = worksheet.get_all_values()
        if len(all_values) < 2: return 
        header, data = all_values[0], all_values[1:]
        cutoff = datetime.utcnow() + timedelta(hours=2) - timedelta(days=DB_RETENTION_DAYS)
        cleaned = [row for row in data if datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S") > cutoff]
        cleaned.sort(key=lambda x: x[5], reverse=True)
        worksheet.clear()
        worksheet.append_row(header)
        if cleaned: worksheet.append_rows(cleaned)
        print(f"✅ Kept {len(cleaned)} items.")
    except Exception as e: print(f"⚠️ Clean Error: {e}")

def run_scraper():
    print("🚀 NomoTech Bot v2.1.8 (Final Master) Started...")
    client, worksheet = setup_ai(), setup_db()
    try: existing_links = set(worksheet.col_values(5))
    except: existing_links = set()
    new_rows, current_time = [], datetime.now()
    session = requests.Session()
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"📡 {source_name}...", end=" ", flush=True)
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, */*'
            }
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
        except Exception as e: print(f"❌ Error: {str(e)[:15]}")
        
    if new_rows: worksheet.append_rows(new_rows)
    sort_and_clean_database(worksheet)

if __name__ == "__main__":
    run_scraper()

