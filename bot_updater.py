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
        print("✅ Gemini AI Connected! (Filter Mode: ON)")
    else:
        print("⚠️ No API Key. Falling back to Keywords.")
except Exception as e:
    print(f"⚠️ AI Error: {e}")

RSS_FEEDS = {
    # --- PRO SOURCES ---
    "⚖️ Dikastiko": "https://www.dikastiko.gr/feed/",
    "⚖️ Dikastiko Reportaz": "https://www.dikastikoreportaz.gr/feed/", 
    "⚖️ Lawspot": "https://www.lawspot.gr/rss",
    "⚖️ LawNet": "https://www.lawnet.gr/feed/",
    "⚖️ Syntagma Watch": "https://www.syntagmawatch.gr/feed/", 
    "⚖️ ΔΣΑ": "https://www.dsa.gr/rss.xml",
    "🏠 POMIDA": "https://www.pomida.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    "🏘️ Property": "https://www.newsauto.gr/category/news/feed/",
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "💰 Capital": "https://www.capital.gr/rss/oikonomia",
    "🚢 Naftemporiki": "https://www.naftemporiki.gr/feed/",
    
    # --- GENERAL (RISKY SOURCES - NEED FILTERS) ---
    "📰 Kathimerini": "https://www.kathimerini.gr/feed/",
    "📰 To Vima": "https://www.tovima.gr/feed/",
    "📰 Iefimerida": "https://www.iefimerida.gr/rss.xml",
    "📰 Ethnos": "https://www.ethnos.gr/feed/",
    "📰 ProtoThema": "https://www.protothema.gr/rss",
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# --- 2. HELPERS ---
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

# --- 3. SAFETY NET (STRICT) ---
def guess_category_classic(text):
    text = remove_accents(text)
    tags = []
    
    # KEYWORDS WE WANT
    eng_keys = ['μηχανικ', 'εργα', 'δομηση', 'αυθαιρετα', 'εξοικονομω', 'ενεργεια', 'πολεοδομ', 'κτηματολογ', 'υποδομες', 'αναπλαση', 'μετρο', 'οδικος']
    real_keys = ['ακινητ', 'ενοικι', 'airbn', 'αντικειμενικ', 'gold visa', 'ενφια', 'ααδε', 'μεταβιβαση', 'πλειστηριασμ']
    legal_keys = ['δικαστηρι', 'δικηγορ', 'στε', 'αρεοπαγ', 'αγωγη', 'ποινικ', 'συνταγμα', 'δικαιοσυνη', 'εισαγγελ']
    legis_keys = ['φεκ', 'εγκυκλιος', 'υπουργικη αποφαση', 'νομος υπ αριθμ', 'τροπολογια']
    sos_keys = ['προθεσμια', 'προστιμ', 'παραταση', 'ληξη']

    if any(w in text for w in eng_keys): tags.append("ENGINEERS")
    if any(w in text for w in real_keys): tags.append("REAL_ESTATE")
    
    is_legal = any(w in text for w in legal_keys)
    is_tech = "ENGINEERS" in tags or "REAL_ESTATE" in tags
    if is_legal and not is_tech: tags.append("LEGAL")

    if any(w in text for w in legis_keys): tags.append("LEGISLATION")
    if any(w in text for w in sos_keys): tags.append("SOS")

    # ΑΝ ΔΕΝ ΒΡΗΚΕ ΤΙΠΟΤΑ -> None (ΓΙΑ ΝΑ ΔΙΑΓΡΑΦΕΙ)
    if not tags: return None
    return ", ".join(tags)

# --- 4. AI ANALYST (THE BOUNCER) ---
def analyze_article_with_ai(title, full_text):
    if not HAS_AI: return None, None
    
    prompt = f"""
    Act as a Strict Filter for a Professional Portal (Lawyers/Engineers/Economists).
    Analyze this article:
    TITLE: {title}
    TEXT: {full_text[:8000]}
    
    --- 1. RELEVANCE CHECK (THE BOUNCER) ---
    Is this article about:
    - Lifestyle / Gossip / Celebrities / Survivor?
    - Sports?
    - Simple Police News (Robberies/Accidents without court ruling)?
    - General Politics (Parties arguing) without specific laws/projects?
    - International News without effect on Greece?
    
    IF YES TO ANY ABOVE -> OUTPUT: SKIP ||| Junk
    
    --- 2. CATEGORIZATION (If Relevant) ---
    - ENGINEERS: Construction, Infrastructure, Energy, Zoning, Ktimatologio.
    - REAL_ESTATE: Property, Tax, Rents.
    - LEGAL: Courts, Lawyers, Justice System (NOT technical laws).
    - LEGISLATION: Official FEK, Laws, Decisions.
    - SOS: Deadlines.
    
    --- 3. SUMMARY ---
    - Greek Bullet Points (•). Extract dates/amounts.
    
    --- OUTPUT FORMAT ---
    TAG1, TAG2 ||| • Bullet 1...
    OR
    SKIP ||| Reason
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        if "|||" in text:
            parts = text.split("|||")
            tags = parts[0].strip().upper()
            summary = parts[1].strip()
            
            # ΑΝ ΤΟ AI ΠΕΙ SKIP, ΕΠΙΣΤΡΕΦΟΥΜΕ None ΣΤΑ TAGS
            if "SKIP" in tags: return None, None
            
            return tags, summary
        else:
            return None, text 
    except Exception as e:
        print(f"AI Error: {e}")
        return None, None

# --- 5. MAIN LOOP ---
def run():
    print(f"🤖 [NomoTechi FILTER v8] Starting...")
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
    skipped_items = 0
    
    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if not feed.entries: continue
            
            # Ελέγχουμε τα 3 πρώτα
            for entry in feed.entries[:3]: 
                print(f"   🔎 Checking: {entry.title[:30]}...")
                
                scraped_text = scrape_full_text(entry.link)
                if not scraped_text: scraped_text = entry.summary
                
                # 1. AI Analysis
                tags, ai_summary = analyze_article_with_ai(entry.title, scraped_text)
                
                # 2. Safety Net / FILTER
                # Αν το AI δεν έβγαλε tags (ή έβγαλε SKIP -> None), δοκιμάζουμε το strict keyword check
                if not tags:
                    tags = guess_category_classic(entry.title + " " + scraped_text)
                
                # 3. FINAL JUDGMENT: Αν ακόμα δεν έχουμε tags, είναι ΣΚΟΥΠΙΔΙΑ -> SKIP
                if not tags:
                    print(f"      ⛔ SKIPPED (Irrelevant): {entry.title[:30]}")
                    skipped_items += 1
                    continue # Πάμε στο επόμενο, δεν σώζουμε τίποτα

                if not ai_summary: ai_summary = entry.summary
                real_image_url = fetch_article_image(entry.link)

                if entry.link in link_map:
                    # UPDATE
                    row_num = link_map[entry.link]
                    print(f"      ♻️ Updating: {tags}")
                    sheet.update_cell(row_num, 4, ai_summary)
                    sheet.update_cell(row_num, 7, tags)
                    if real_image_url: sheet.update_cell(row_num, 8, real_image_url)
                    updated_items += 1
                else:
                    # NEW
                    print(f"      ✨ Adding: {tags}")
                    new_row = [len(existing_data) + new_items + 1, source_name, entry.title, ai_summary, entry.link, datetime.now().strftime("%Y-%m-%d"), tags, real_image_url]
                    sheet.append_row(new_row)
                    new_items += 1
                
                time.sleep(1) 
        except: pass

    print(f"🏁 Done. Added: {new_items}, Updated: {updated_items}, Junk Skipped: {skipped_items}")

if __name__ == "__main__":
    run()
