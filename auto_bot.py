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

# --- 1. CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
GCP_CREDENTIALS = os.environ.get("GCP_CREDENTIALS")
SPREADSHEET_NAME = "laws_database"
FETCH_DAYS_LIMIT = 10 
DB_RETENTION_DAYS = 31

USER_AGENTS = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36']

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

def scrape_full_text(url):
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
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
        # Διατήρηση της σταθερότητας με 6s delay
        time.sleep(6) 
        
        prompt = f"""
        ROLE: Specialized Intelligence Analyst for NomoTech.gr. Your expertise lies in distilling complex Greek Engineering, Legal, and Legislative data for professionals.

        TASK: Analyze the provided article and assign ALL applicable CATEGORIES. Accuracy is critical for professional decision-making.

        TAXONOMY & KEYWORDS:
        - ENG (Engineering & Real Estate): Focus on Building Permits (Άδειες Δόμησης), Cadastre (Κτηματολόγιο), Energy Performance (Εξοικονομώ, ΠΕΑ), Real Estate Market Trends, Construction Costs, Infrastructure Projects, Urban Planning (Πολεοδομία), Civil Engineering technicalities, Engineering, Construction, Real Estate prices/trends, Energy, Technical projects, Immovable asset, ΤΕΕ, NOK (ΝΟΚ), GOK (ΓΟΚ), Technical Issues.
        - LAW (Legal & Jurisprudence): Focus on Court Rulings (Αποφάσεις Δικαστηρίων), Supreme Court (Άρειος Πάγος), Council of State (ΣτΕ), Litigation (Αγωγές), Legal Procedures, Lawyer Professional News, Penal/Civil/Administrative Law updates, Justice system, Court rulings (Areios Pagos, StE), Lawyer news.
        - FEK (Government Gazette & Legislation): Focus on New Laws (Νόμοι), Ministerial Decisions (Υπουργικές Αποφάσεις), Circulars (Εγκύκλιοι), Official Gazette publications, Tax Legislation updates.
        - GEN (General Economy): Macro-economics, general business news, or social news with NO specific technical, legal, or legislative impact.

        MULTITAGGING PROTOCOL:
        * If an article discusses Real Estate prices AND new legislation, use: ENG, FEK.
        * If an article discusses a Court ruling regarding a construction project, use: ENG, LAW.
        * If an article discusses a new Law about Lawyers, use: LAW, FEK.
        * ALWAYS include 'ENG' for anything related to Property, Housing/Building Market, Urban planning, Cadastre (Κτηματολόγιο), Real estate, Construction, or engineering.

        SUMMARY REQUIREMENTS:
        * Language: Professional Greek (Formal tone).
        * Content: Focus on "Who, What, When, and the Professional Impact".
        * Length: 120-150 words.

        ARTICLE DATA:
        Title: {title}
        Content: {content[:2500]}

        OUTPUT FORMAT: CATEGORIES (comma-separated) ||| Summary
        """

        # Εκτέλεση με Gemini 2.0 Flash
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        text = response.text.strip()
        
        if "|||" in text:
            parts = text.split("|||")
            tags = parts[0].strip().upper() 
            summary = parts[1].strip()
            return tags, summary
            
        return fallback_classify(title, ""), text
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
        cleaned.sort(key=lambda x: x[5])
        worksheet.clear()
        worksheet.append_row(header)
        if cleaned: worksheet.append_rows(cleaned)
        print(f"✅ Database Processed: Kept {len(cleaned)} items.")
    except Exception as e: print(f"⚠️ Error: {e}")

def run_scraper():
    print("🚀 NomoTech Bot v2.0.5 (Billing Enabled) Started...")
    client, worksheet = setup_ai(), setup_db()
    try: existing_links = set(worksheet.col_values(5))
    except: existing_links = set()
    new_rows, current_time = [], datetime.utcnow() + timedelta(hours=2)
    
    for source_name, feed_url in RSS_FEEDS.items():
        print(f"📡 {source_name}...", end=" ", flush=True)
        try:
            feed = feedparser.parse(feed_url)
            count = 0
            for entry in feed.entries[:15]:
                link = entry.get('link', '')
                if link in existing_links or (current_time - get_date_obj(entry)).days > FETCH_DAYS_LIMIT: continue
                title = entry.get('title', 'No Title')
                full_text = scrape_full_text(link) or title
                cat_tag, ai_article = analyze_with_ai(client, title, full_text, entry.get('summary', title))
                new_rows.append([str(hash(link)), source_name, title, ai_article, link, get_date_obj(entry).strftime("%Y-%m-%d %H:%M:%S"), cat_tag, ""])
                existing_links.add(link)
                count += 1
            print(f"✅ {count}")
        except: print("❌")
    if new_rows: worksheet.append_rows(new_rows)
    sort_and_clean_database(worksheet)

if __name__ == "__main__":
    run_scraper()

