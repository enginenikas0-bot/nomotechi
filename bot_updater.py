import os
import json
import gspread
import feedparser
from datetime import datetime
import time
import re
import requests
from bs4 import BeautifulSoup
import random
import google.generativeai as genai

# --- 1. CONFIG & API ---
HAS_AI = False
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        HAS_AI = True
        print("✅ Gemini AI Connected!")
    else:
        print("⚠️ No API Key. Using Keyword Mode.")
except Exception as e:
    print(f"⚠️ AI Error: {e}")

# ΕΝΙΣΧΥΜΕΝΕΣ ΠΗΓΕΣ ΓΙΑ ΔΙΚΗΓΟΡΟΥΣ & ΜΕΣΙΤΕΣ
RSS_FEEDS = {
    # ΝΟΜΙΚΑ / ΔΙΚΑΙΟΣΥΝΗ (Heavy)
    "⚖️ LawNet (Νομολογία)": "https://www.lawnet.gr/feed/",
    "⚖️ Dikastiko (Δικαστικά)": "https://www.dikastiko.gr/feed/",
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "⚖️ ΔΣΑ (Δικηγόροι)": "https://www.dsa.gr/rss.xml",
    "🎓 Dikaiologitika": "https://www.dikaiologitika.gr/feed", 
    
    # ΜΗΧΑΝΙΚΟΙ & REAL ESTATE (Μεσίτες)
    "🏠 POMIDA (Ιδιοκτήτες)": "https://www.pomida.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    
    # ΟΙΚΟΝΟΜΙΑ & ΓΕΝΙΚΑ
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "💰 Capital Real Estate": "https://www.capital.gr/rss/oikonomia", 
    "⚡ EnergyPress": "https://energypress.gr/feed",
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# --- 2. AI BRAIN (UPDATED) ---
def ask_gemini_smart_tags(title, summary):
    """
    Το AI αποφασίζει κατηγορία ΚΑΙ αν είναι SOS/Deadline.
    """
    if not HAS_AI: return None
    
    prompt = f"""
    Analyze this news for a Greek Professional Portal.
    Title: {title}
    Summary: {summary}
    
    1. Categorize into:
    - ENGINEERS (Construction, Energy, Public Works, Urban Planning)
    - REAL_ESTATE (Property prices, Rents, Golden Visa, Land Registry/Ktimatologio, AirBnB) -> This is crucial for Brokers.
    - LEGAL (Court decisions, Bar association news, Justice system, Lawsuits)
    - LEGISLATION (ONLY if it is a FEK, Law, Circular, Decision)
    - TAX (Taxation, AADE, MyData)

    2. Check for URGENCY:
    - If it mentions a deadline, fine, penalty, or expiry date -> Add tag "SOS"
    - If it is a Supreme Court (Areopagos/StE) decision -> Add tag "JUDICIAL"

    Return tags separated by comma. Example: REAL_ESTATE, SOS, LEGISLATION
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip().upper()
    except:
        return None

# --- 3. CLASSIC LOGIC (BACKUP) ---
def guess_category_classic(title, summary, source_name):
    full_text = remove_accents(title + " " + summary)
    source_clean = remove_accents(source_name)
    tags = []

    # Legislation
    if any(w in full_text for w in ['φεκ', 'εγκυκλιος', 'αποφαση', 'νομος']) or "nomothesia" in source_clean:
        tags.append("LEGISLATION")

    # Real Estate (Broker Focus)
    if any(w in full_text for w in ['ακινητ', 'ενοικι', 'airbn', 'κτηματολογι', 'αντικειμενικ', 'gold visa', 'πλειστηριασμ']):
        tags.append("REAL_ESTATE")
    
    # Engineers
    if any(w in full_text for w in ['μηχανικ', 'εργα', 'δομηση', 'αυθαιρετα', 'εξοικονομω', 'ενεργεια']):
        tags.append("ENGINEERS")

    # Legal
    if any(w in full_text for w in ['δικαστηρι', 'δικηγορ', 'στε', 'αρεοπαγ', 'αγωγη', 'ποινικ']):
        tags.append("LEGAL")
        if "αποφαση" in full_text: tags.append("JUDICIAL")

    # SOS Check
    if any(w in full_text for w in ['προθεσμια', 'προστιμ', 'παραταση', 'ληξη', 'τελος χρονου']):
        tags.append("SOS")

    if not tags: tags.append("GENERAL")
    return ", ".join(tags)

# --- 4. HELPER FUNCTIONS ---
def fetch_article_image(url):
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"): return og_image["content"]
    except: return ""
    return ""

def remove_accents(input_str):
    replacements = {'ά':'α','έ':'ε','ή':'η','ί':'ι','ό':'ο','ύ':'υ','ώ':'ω'}
    for char, rep in replacements.items(): input_str = input_str.replace(char, rep)
    return input_str.lower()

def clean_summary(text):
    text = re.sub('<[^<]+?>', '', text)
    return text[:600] + "..."

# --- 5. MAIN LOOP ---
def run():
    print(f"🤖 [NomoTechi v2] Starting Smart Scan...")
    
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds: return

    try:
        creds_dict = json.loads(json_creds)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("laws_database")
        sheet = sh.sheet1
        if sheet.acell('H1').value != 'image_url': sheet.update_cell(1, 8, 'image_url')
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    try:
        existing_data = sheet.get_all_records()
        existing_links = [row['link'] for row in existing_data]
    except:
        existing_data = []
        existing_links = []
        
    new_items_count = 0
    feed_headers = {'User-Agent': 'Mozilla/5.0'}

    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url, agent=feed_headers['User-Agent'])
            if not feed.entries: continue
            
            for entry in feed.entries[:3]: # Top 3 per source
                if entry.link not in existing_links:
                    title = entry.title
                    summary = clean_summary(entry.summary if 'summary' in entry else "")
                    
                    # --- AI BRAIN ---
                    print(f"   🧠 Analyzing: {title[:30]}...")
                    category = ask_gemini_smart_tags(title, summary)
                    if not category:
                        category = guess_category_classic(title, summary, source_name)
                    
                    print(f"      🏷️ Tags: {category}")
                    real_image_url = fetch_article_image(entry.link)

                    new_row = [
                        len(existing_data) + new_items_count + 1,
                        source_name,
                        title,
                        summary,
                        entry.link,
                        datetime.now().strftime("%Y-%m-%d"),
                        category, 
                        real_image_url
                    ]
                    sheet.append_row(new_row)
                    new_items_count += 1
                    existing_links.append(entry.link)
        except: pass

    print(f"🏁 Done. New articles: {new_items_count}")

if __name__ == "__main__":
    run()
