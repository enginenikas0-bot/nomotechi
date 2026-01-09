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
import google.generativeai as genai # Βιβλιοθήκη για το AI

# --- 1. CONFIG & API SETUP ---
# Προσπαθούμε να συνδεθούμε με το AI
HAS_AI = False
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        HAS_AI = True
        print("✅ Gemini AI Connected!")
    else:
        print("⚠️ No Google API Key found. Switching to Keyword Mode.")
except Exception as e:
    print(f"⚠️ AI Init Error: {e}")

RSS_FEEDS = {
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "⚖️ ΔΣΑ": "https://www.dsa.gr/rss.xml",
    "⚖️ Lawspot": "https://www.lawspot.gr/nomika-nea/feed",
    "🎓 Dikaiologitika": "https://www.dikaiologitika.gr/feed", 
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "⚡ EnergyPress": "https://energypress.gr/feed",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    "👷 Michanikos": "https://www.michanikos-online.gr/feed/",
    "🌍 GreenAgenda": "https://greenagenda.gr/feed/",
    "🏠 POMIDA": "https://www.pomida.gr/feed/",
    "📐 Archetypes": "https://www.archetypes.gr/feed/",
    "💰 Capital": "https://www.capital.gr/rss/oikonomia"
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# --- 2. AI BRAIN (Ο ΕΓΚΕΦΑΛΟΣ) ---
def ask_gemini_categories(title, summary):
    """Ρωτάει το AI σε ποιες κατηγορίες ανήκει το άρθρο"""
    if not HAS_AI: return None
    
    prompt = f"""
    Act as a professional editor for a Greek news portal for Engineers and Lawyers.
    Analyze this article title and summary:
    Title: {title}
    Summary: {summary}
    
    Assign it to one or more of these categories based on relevance:
    - ENGINEERS (if it's about construction, energy, urban planning, public works, real estate technicalities)
    - LEGAL (if it's about court decisions, lawyers, laws, justice, tax laws)
    - LEGISLATION (ONLY if it is a FEK, Law, Ministerial Decision, Circular)
    
    Return ONLY the categories separated by comma. Example: ENGINEERS, LEGISLATION
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
    categories = []

    # 1. Check for Legislation (ΦΕΚ)
    fek_keywords = ['φεκ', 'εγκυκλιος', 'κυα', 'προεδρικο διαταγμα', 'νομοσχεδιο', 'τροπολογια', 'αποφαση']
    if any(w in full_text for w in fek_keywords) or "e-nomothesia" in source_clean:
        categories.append("LEGISLATION")

    # 2. Check for Engineers/Real Estate
    eng_keywords = ['μηχανικ', 'εργα', 'ακινητ', 'δομηση', 'αυθαιρετα', 'ενεργεια', 'εξοικονομω', 'κτηματολογιο', 'πολεοδομ', 'κατασκευ', 'υποδομες']
    if any(w in full_text for w in eng_keywords) or any(x in source_clean for x in ['b2green', 'ypodomes', 'tee', 'michanikos', 'pedmede', 'energy']):
        categories.append("ENGINEERS")

    # 3. Check for Legal
    law_keywords = ['δικαστηρι', 'δικηγορ', 'συμβολαιογραφ', 'αρεοπαγ', 'στε', 'νομικ', 'δικαιοσυνη']
    if any(w in full_text for w in law_keywords) or any(x in source_clean for x in ['dsa', 'lawspot', 'taxheaven']):
        categories.append("LEGAL")

    # Default
    if not categories: categories.append("GENERAL")
    
    return ", ".join(categories)

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
    print(f"🤖 [NomoTechi AI] Starting Scan...")
    
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds: return

    try:
        creds_dict = json.loads(json_creds)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("laws_database")
        sheet = sh.sheet1
        
        # Check Header
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
            
            for entry in feed.entries[:3]: 
                if entry.link not in existing_links:
                    title = entry.title
                    summary = clean_summary(entry.summary if 'summary' in entry else "")
                    
                    # --- AI DECISION ---
                    print(f"   🧠 Analyzing: {title[:30]}...")
                    category = ask_gemini_categories(title, summary)
                    
                    # Fallback to classic if AI fails or key is missing
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
                        category, # Multi-tag string (e.g. "ENGINEERS, LEGISLATION")
                        real_image_url
                    ]
                    
                    sheet.append_row(new_row)
                    new_items_count += 1
                    existing_links.append(entry.link)
        except Exception as e:
            print(f"Error on {source_name}: {e}")
            pass

    print(f"🏁 Done. New articles: {new_items_count}")

if __name__ == "__main__":
    run()
