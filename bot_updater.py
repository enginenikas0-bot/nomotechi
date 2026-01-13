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

# --- 1. CONFIG ---
HAS_AI = False
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        HAS_AI = True
        print("✅ Gemini AI Connected! (Surgical Precision Mode)")
    else:
        print("⚠️ No API Key. Falling back to Safety Net.")
except Exception as e:
    print(f"⚠️ AI Error: {e}")

# --- 2. SOURCES (CLEAN LIST) ---
RSS_FEEDS = {
   "⚖️ Dikastiko": "https://www.dikastiko.gr/feed/",
    "⚖️ Dikastiko Reportaz": "https://www.dikastikoreportaz.gr/feed/", 
    "⚖️ Lawspot": "https://www.lawspot.gr/rss",
    "⚖️ Syntagma Watch": "https://www.syntagmawatch.gr/feed/", 
    "⚖️ LawNet": "https://www.lawnet.gr/feed/",
    "⚖️ ΔΣΑ": "https://www.dsa.gr/rss.xml",
    "⚖️ eThemis": "https://www.ethemis.gr/feed/",
    "🏠 POMIDA": "https://www.pomida.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🏛️ Michanikos": "https://www.michanikos.gr/feed/",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "💰 Capital": "https://www.capital.gr/rss/oikonomia",
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# --- 3. HELPERS ---
def remove_accents(input_str):
    replacements = {'ά':'α','έ':'ε','ή':'η','ί':'ι','ό':'ο','ύ':'υ','ώ':'ω'}
    input_str = input_str.lower()
    for char, rep in replacements.items(): input_str = input_str.replace(char, rep)
    return input_str

def scrape_full_text(url):
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer", "aside"]): tag.extract()
            paragraphs = soup.find_all('p')
            full_text = " ".join([p.get_text() for p in paragraphs])
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            if len(full_text) < 150: return "" 
            return full_text[:9000]
    except: return ""
    return ""

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

# --- 4. SANITIZER (Safety Check) ---
def sanitize_tags(tags_str):
    if not tags_str or tags_str == "GENERAL": return tags_str
    tag_list = [t.strip().upper() for t in tags_str.split(',')]
    
    # ΚΑΝΟΝΑΣ: Το "LEGAL" φεύγει ΜΟΝΟ αν υπάρχει Τεχνικό θέμα
    if ("ENGINEERS" in tag_list or "REAL_ESTATE" in tag_list) and "LEGAL" in tag_list:
        tag_list.remove("LEGAL")
        
    return ", ".join(tag_list)

# --- 5. SAFETY NET ---
def guess_category_classic(text):
    text = remove_accents(text)
    tags = []
    
    if any(w in text for w in ['μηχανικ', 'εργα', 'δομηση', 'αυθαιρετα', 'εξοικονομω', 'ενεργεια', 'πολεοδομ', 'κτηματολογ', 'υποδομες', 'αναπλαση']):
        tags.append("ENGINEERS")
    
    if any(w in text for w in ['ακινητ', 'ενοικι', 'airbn', 'αντικειμενικ', 'gold visa', 'ενφια', 'ααδε', 'μεταβιβαση']):
        tags.append("REAL_ESTATE")
    
    is_legal = any(w in text for w in ['δικαστηρι', 'δικηγορ', 'στε', 'αρεοπαγ', 'αγωγη', 'ποινικ', 'συνταγμα', 'δικαιοσυνη'])
    is_tech = "ENGINEERS" in tags or "REAL_ESTATE" in tags
    if is_legal and not is_tech: 
        tags.append("LEGAL")

    if any(w in text for w in ['φεκ', 'εγκυκλιος', 'υπουργικη αποφαση', 'νομος υπ αριθμ', 'τροπολογια']):
        tags.append("LEGISLATION")
    
    if any(w in text for w in ['προθεσμια', 'προστιμ', 'παραταση', 'ληξη']):
        tags.append("SOS")

    if not tags: return "GENERAL"
    return ", ".join(tags)

# --- 6. AI ANALYST (SURGICAL PROMPT) ---
def analyze_article_with_ai(title, full_text):
    if not HAS_AI: return None, None
    
    prompt = f"""
    Act as a Senior Intelligence Analyst. Classify this article with extreme precision.
    TITLE: {title}
    TEXT: {full_text[:8000]}
    
    --- CATEGORIZATION LOGIC ---
    
    1. [ENGINEERS]:
       - MUST contain Technical topics: Construction, Infrastructure, Public Works (Erga), Energy, Zoning, Ktimatologio.
       - Even if it mentions "Contracts" or "Laws", if the SUBJECT is a Project -> Tag ENGINEERS.
       
    2. [LEGAL]:
       - MUST contain Pure Legal topics: Criminal/Civil/Family Law, Court Procedure, Bar Association (DSA), Justice Reform.
       - SAFETY CHECK: Does it mention Concrete, Buildings, or Roads? If YES -> DO NOT USE "LEGAL" (Use Engineers).
       - Only use "LEGAL" for pure justice matters.

    3. [REAL_ESTATE]:
       - Property Tax, Rents, Buying/Selling.

    4. [LEGISLATION]:
       - Official Documents ONLY: FEK, Laws, Decisions.

    5. [SOS]:
       - Deadlines/Fines.

    --- SUMMARY ---
    - Greek Bullet Points (•). Precise Data.
    
    --- OUTPUT ---
    TAG1, TAG2 ||| • Bullet 1...
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        if "|||" in text:
            parts = text.split("|||")
            tags = parts[0].strip().upper()
            summary = parts[1].strip()
            return tags, summary
        else:
            return None, text 
    except Exception as e:
        print(f"AI Error: {e}")
        return None, None

# --- 7. MAIN LOOP ---
def run():
    print(f"🤖 [NomoTechi SURGICAL v13] Starting...")
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds: return

    try:
        creds_dict = json.loads(json_creds)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("laws_database")
        sheet = sh.sheet1
        header = ['id', 'source', 'title', 'content', 'link', 'last_update', 'category', 'image_url']
        if sheet.row_values(1) != header: sheet.update('A1:H1', [header])
        existing_data = sheet.get_all_records()
        link_map = {row['link']: i + 2 for i, row in enumerate(existing_data)}
    except Exception as e:
        print(f"DB Error: {e}")
        return

    new_items = 0
    updated_items = 0
    
    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if not feed.entries: continue
            
            # Έλεγχος στα 6 πρώτα για να μην χάνουμε ειδήσεις
            for entry in feed.entries[:6]: 
                print(f"   🔎 Checking: {entry.title[:30]}...")
                
                scraped_text = scrape_full_text(entry.link)
                if not scraped_text: scraped_text = entry.summary
                
                tags, ai_summary = analyze_article_with_ai(entry.title, scraped_text)
                
                if not tags or tags == "GENERAL" or len(tags) < 3:
                    tags = guess_category_classic(entry.title + " " + scraped_text)
                if not ai_summary: ai_summary = entry.summary
                
                # Εφαρμογή του Καθαριστή
                tags = sanitize_tags(tags)

                real_image_url = fetch_article_image(entry.link)

                if entry.link in link_map:
                    row_num = link_map[entry.link]
                    sheet.update_cell(row_num, 4, ai_summary)
                    sheet.update_cell(row_num, 7, tags)
                    if real_image_url: sheet.update_cell(row_num, 8, real_image_url)
                    updated_items += 1
                else:
                    print(f"      ✨ Adding: {tags}")
                    new_row = [len(existing_data) + new_items + 1, source_name, entry.title, ai_summary, entry.link, datetime.now().strftime("%Y-%m-%d"), tags, real_image_url]
                    sheet.append_row(new_row)
                    new_items += 1
                
                time.sleep(3.5) 
        except: pass

    print(f"🏁 Done. Added: {new_items}, Updated: {updated_items}")

if __name__ == "__main__":
    run()

