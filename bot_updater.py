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
        print("✅ Gemini AI Connected!")
    else:
        print("⚠️ No API Key. Falling back to Safety Net.")
except Exception as e:
    print(f"⚠️ AI Error: {e}")

RSS_FEEDS = {
    "⚖️ Lawspot.gr": "https://www.lawspot.gr/rss",
    "⚖️ Syntagma Watch": "https://www.syntagmawatch.gr/feed/", 
    "⚖️ Dikastiko": "https://www.dikastiko.gr/feed/",
    "⚖️ LawNet": "https://www.lawnet.gr/feed/",
    "⚖️ ΔΣΑ": "https://www.dsa.gr/rss.xml",
    "🏠 POMIDA": "https://www.pomida.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "💰 Capital": "https://www.capital.gr/rss/oikonomia",
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
            paragraphs = soup.find_all('p')
            full_text = " ".join([p.get_text() for p in paragraphs])
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            if len(full_text) < 200: return "" 
            return full_text[:8000]
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

# --- 3. SAFETY NET ---
def guess_category_classic(text):
    text = remove_accents(text)
    tags = []
    if any(w in text for w in ['μηχανικ', 'εργα', 'δομηση', 'αυθαιρετα', 'εξοικονομω', 'ενεργεια', 'πολεοδομ', 'κτηματολογ']):
        tags.append("ENGINEERS")
    if any(w in text for w in ['ακινητ', 'ενοικι', 'airbn', 'αντικειμενικ', 'gold visa', 'ενφια', 'ααδε']):
        tags.append("REAL_ESTATE")
    is_legal = any(w in text for w in ['δικαστηρι', 'δικηγορ', 'στε', 'αρεοπαγ', 'αγωγη', 'ποινικ', 'συνταγμα'])
    if is_legal and "ENGINEERS" not in tags:
        tags.append("LEGAL")
    if any(w in text for w in ['φεκ', 'εγκυκλιος', 'αποφαση', 'νομος', 'τροπολογια']):
        tags.append("LEGISLATION")
    if any(w in text for w in ['προθεσμια', 'προστιμ', 'παραταση', 'ληξη']):
        tags.append("SOS")
    if not tags: return "GENERAL"
    return ", ".join(tags)

# --- 4. AI ANALYST ---
def analyze_article_with_ai(title, full_text):
    if not HAS_AI: return None, None
    prompt = f"""
    Analyze this Greek article.
    Title: {title}
    Text snippet: {full_text[:7000]}
    
    INSTRUCTIONS:
    1. Categorize strictly:
       - ENGINEERS: Construction, Energy, Zoning, Ktimatologio.
       - REAL_ESTATE: Property, Rents, Tax.
       - LEGAL: Courts, Lawyers (Exclude technical laws).
       - LEGISLATION: FEK, Laws.
       - SOS: Deadlines.
    
    2. Summarize in Greek with Bullet Points (•). Include dates/amounts.
    
    OUTPUT FORMAT (Strictly use ||| to separate tags from summary):
    TAG1, TAG2, TAG3 ||| • Bullet point 1... • Bullet point 2...
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

# --- 5. MAIN LOOP (THE UPDATER) ---
def run():
    print(f"🤖 [NomoTechi Updater] Starting...")
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds: return

    try:
        creds_dict = json.loads(json_creds)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("laws_database")
        sheet = sh.sheet1
        
        # Ensure Headers
        header = ['id', 'source', 'title', 'content', 'link', 'last_update', 'category', 'image_url']
        if sheet.row_values(1) != header: sheet.update('A1:H1', [header])
        
        # Get existing Data & Map Links to Row Numbers
        existing_data = sheet.get_all_records()
        # Δημιουργούμε ένα λεξικό: Link -> Αριθμός Γραμμής (index + 2 γιατί το header είναι 1 και το index ξεκινάει από 0)
        link_map = {row['link']: i + 2 for i, row in enumerate(existing_data)}
        
    except Exception as e:
        print(f"DB Error: {e}")
        return

    new_items_count = 0
    updated_items_count = 0
    
    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if not feed.entries: continue
            
            # Επεξεργασία των 3 πρώτων άρθρων από κάθε πηγή
            for entry in feed.entries[:3]: 
                
                # --- PROCESSOR LOGIC ---
                print(f"   🔎 Checking: {entry.title[:30]}...")
                
                # 1. Scrape & AI Analysis (Γίνεται ΠΑΝΤΑ αν το link είναι νέο ή αν θέλουμε να αναβαθμίσουμε)
                scraped_text = scrape_full_text(entry.link)
                if not scraped_text: scraped_text = entry.summary
                
                tags, ai_summary = analyze_article_with_ai(entry.title, scraped_text)
                
                # Safety Net
                if not tags or tags == "GENERAL" or len(tags) < 3:
                    tags = guess_category_classic(entry.title + " " + scraped_text)
                if not ai_summary: ai_summary = entry.summary

                real_image_url = fetch_article_image(entry.link)

                # --- DECISION: NEW or UPDATE? ---
                if entry.link in link_map:
                    # ΥΠΑΡΧΕΙ ΗΔΗ -> ΑΝΑΒΑΘΜΙΣΗ (UPDATE)
                    row_num = link_map[entry.link]
                    
                    # Παίρνουμε την παλιά κατηγορία για να δούμε αν αξίζει να το πειράξουμε
                    # Αλλά επειδή θέλουμε σίγουρα Bullet Points, κάνουμε update
                    print(f"      ♻️ Updating Row {row_num} with AI Data...")
                    
                    # Ενημέρωση κελιών: D=Content, G=Category, H=Image
                    sheet.update_cell(row_num, 4, ai_summary)
                    sheet.update_cell(row_num, 7, tags)
                    if real_image_url: sheet.update_cell(row_num, 8, real_image_url)
                    
                    updated_items_count += 1
                    
                else:
                    # ΔΕΝ ΥΠΑΡΧΕΙ -> ΝΕΑ ΕΓΓΡΑΦΗ (APPEND)
                    print(f"      ✨ Adding New...")
                    new_row = [
                        len(existing_data) + new_items_count + 1,
                        source_name,
                        entry.title,
                        ai_summary,
                        entry.link,
                        datetime.now().strftime("%Y-%m-%d"),
                        tags, 
                        real_image_url
                    ]
                    sheet.append_row(new_row)
                    new_items_count += 1
                
                time.sleep(1.5) # Ανάσα για το API
                
        except Exception as e:
            print(f"Source Error: {e}")
            pass

    print(f"🏁 Done. Added: {new_items_count}, Updated: {updated_items_count}")

if __name__ == "__main__":
    run()
