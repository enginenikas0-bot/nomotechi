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
        print("✅ Gemini AI Connected! (Specialized Mode)")
    else:
        print("⚠️ No API Key. Falling back to Safety Net.")
except Exception as e:
    print(f"⚠️ AI Error: {e}")

# --- 2. THE CLEAN SOURCE LIST ---
RSS_FEEDS = {
    # --- ΝΟΜΙΚΑ & ΔΙΚΑΙΟΣΥΝΗ (Αυτά που ζήτησες) ---
    "⚖️ Dikastiko": "https://www.dikastiko.gr/feed/",
    "⚖️ Dikastiko Reportaz": "https://www.dikastikoreportaz.gr/feed/", 
    "⚖️ Lawspot": "https://www.lawspot.gr/rss",
    "⚖️ Syntagma Watch": "https://www.syntagmawatch.gr/feed/", 
    "⚖️ LawNet": "https://www.lawnet.gr/feed/",
    "⚖️ ΔΣΑ": "https://www.dsa.gr/rss.xml",
    
    # --- ΜΗΧΑΝΙΚΟΙ / ΑΚΙΝΗΤΑ / ΚΑΤΑΣΚΕΥΕΣ ---
    "🏠 POMIDA": "https://www.pomida.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    
    # --- ΟΙΚΟΝΟΜΙΑ & ΝΟΜΟΘΕΣΙΑ (Στοχευμένα) ---
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
            # Αφαίρεση περιττών
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

# --- 4. SAFETY NET ---
def guess_category_classic(text):
    text = remove_accents(text)
    tags = []
    
    if any(w in text for w in ['μηχανικ', 'εργα', 'δομηση', 'αυθαιρετα', 'εξοικονομω', 'ενεργεια', 'πολεοδομ', 'κτηματολογ', 'υποδομες', 'αναπλαση']):
        tags.append("ENGINEERS")
    
    if any(w in text for w in ['ακινητ', 'ενοικι', 'airbn', 'αντικειμενικ', 'gold visa', 'ενφια', 'ααδε', 'μεταβιβαση']):
        tags.append("REAL_ESTATE")
    
    is_legal = any(w in text for w in ['δικαστηρι', 'δικηγορ', 'στε', 'αρεοπαγ', 'αγωγη', 'ποινικ', 'συνταγμα', 'δικαιοσυνη', 'εισαγγελ'])
    # Αν είναι Τεχνικό, ΟΧΙ νομικό
    is_tech = "ENGINEERS" in tags or "REAL_ESTATE" in tags
    if is_legal and not is_tech: tags.append("LEGAL")

    if any(w in text for w in ['φεκ', 'εγκυκλιος', 'υπουργικη αποφαση', 'νομος υπ αριθμ', 'τροπολογια']):
        tags.append("LEGISLATION")
    
    if any(w in text for w in ['προθεσμια', 'προστιμ', 'παραταση', 'ληξη']):
        tags.append("SOS")

    if not tags: return "GENERAL"
    return ", ".join(tags)

# --- 5. AI ANALYST (GOVERNMENT GRADE) ---
def analyze_article_with_ai(title, full_text):
    if not HAS_AI: return None, None
    
    prompt = f"""
    You are a Senior Analyst for a Professional Portal (Engineers/Lawyers).
    Analyze this article.
    TITLE: {title}
    TEXT: {full_text[:8000]}
    
    --- 1. STRICT CATEGORIZATION ---
    Assign tags based on the Target Audience:
    
    [ENGINEERS]:
    - For: Civil Engineers, Contractors.
    - Topics: Public Works, Ktimatologio, Arbitrary Buildings, Urban Planning, Energy Saving.
    
    [REAL_ESTATE]:
    - For: Real Estate Agents, Property Owners.
    - Topics: Property Taxes, Buying/Selling, Rents, Golden Visa.

    [LEGAL]:
    - For: Lawyers, Judges.
    - Topics: Court Rulings (StE/Areopagos), Penal Code, Civil Code, DSA.
    - EXCLUSION: If the article is about a Technical Project, DO NOT use "LEGAL".

    [LEGISLATION]:
    - STRICTLY for Official Documents: FEK, Circulars, Ministerial Decisions (YA).
    - Not for general news.

    [SOS]:
    - For: Urgent Deadlines, Fines.

    --- 2. SUMMARY (GREEK) ---
    - Write a summary in Greek using Bullet Points (•).
    - EXTRACT: Hard Data (Dates, Amounts €, Law Numbers).
    
    --- OUTPUT FORMAT ---
    TAG1, TAG2 ||| • Bullet 1... • Bullet 2...
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

# --- 6. MAIN LOOP (SMART UPDATER) ---
def run():
    print(f"🤖 [NomoTechi CLEAN SOURCES v9] Starting...")
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
            
            # Τσεκάρουμε τα 2 πρώτα άρθρα
            for entry in feed.entries[:2]: 
                print(f"   🔎 Checking: {entry.title[:30]}...")
                
                scraped_text = scrape_full_text(entry.link)
                if not scraped_text: scraped_text = entry.summary
                
                tags, ai_summary = analyze_article_with_ai(entry.title, scraped_text)
                
                # Safety Net
                if not tags or tags == "GENERAL" or len(tags) < 3:
                    tags = guess_category_classic(entry.title + " " + scraped_text)
                if not ai_summary: ai_summary = entry.summary

                real_image_url = fetch_article_image(entry.link)

                if entry.link in link_map:
                    # UPDATE EXISTING
                    row_num = link_map[entry.link]
                    print(f"      ♻️ Updating Row {row_num}: {tags}")
                    sheet.update_cell(row_num, 4, ai_summary)
                    sheet.update_cell(row_num, 7, tags)
                    if real_image_url: sheet.update_cell(row_num, 8, real_image_url)
                    updated_items += 1
                else:
                    # NEW ENTRY
                    print(f"      ✨ Adding New: {tags}")
                    new_row = [len(existing_data) + new_items + 1, source_name, entry.title, ai_summary, entry.link, datetime.now().strftime("%Y-%m-%d"), tags, real_image_url]
                    sheet.append_row(new_row)
                    new_items += 1
                
                time.sleep(1)
        except: pass

    print(f"🏁 Clean Update Complete. Added: {new_items}, Updated: {updated_items}")

if __name__ == "__main__":
    run()
