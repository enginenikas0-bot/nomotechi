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
        print("⚠️ No API Key. Falling back to simple mode.")
except Exception as e:
    print(f"⚠️ AI Error: {e}")

# ΟΙ ΠΗΓΕΣ ΜΑΣ
RSS_FEEDS = {
    # ΝΟΜΙΚΑ (HEAVY)
    "⚖️ Lawspot.gr": "https://www.lawspot.gr/rss",
    "⚖️ Syntagma Watch": "https://www.syntagmawatch.gr/feed/", 
    "⚖️ Dikastiko": "https://www.dikastiko.gr/feed/",
    "⚖️ LawNet": "https://www.lawnet.gr/feed/",
    "⚖️ ΔΣΑ": "https://www.dsa.gr/rss.xml",
    # ΤΕΧΝΙΚΑ / REAL ESTATE
    "🏠 POMIDA": "https://www.pomida.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    # ΓΕΝΙΚΑ / ΦΕΚ
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "💰 Capital": "https://www.capital.gr/rss/oikonomia",
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# --- 2. DEEP SCRAPER (ΔΙΑΒΑΖΕΙ ΤΟ ΑΡΘΡΟ) ---
def scrape_full_text(url):
    """Μπαίνει στο site και παίρνει το κυρίως κείμενο"""
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Προσπάθεια εύρεσης κυρίως κειμένου (p tags)
            paragraphs = soup.find_all('p')
            full_text = " ".join([p.get_text() for p in paragraphs])
            
            # Καθαρισμός
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            
            if len(full_text) < 200: return "" 
            return full_text[:8000] # Αυξήσαμε το όριο για να χωράει λεπτομέρειες
    except:
        return ""
    return ""

# --- 3. AI ANALYST (STRICT CATEGORIES + BULLET POINTS) ---
def analyze_article_with_ai(title, full_text):
    if not HAS_AI: return "GENERAL", "No AI Summary available."
    
    prompt = f"""
    Act as a Senior Legal & Technical Analyst for a Greek Professional Portal.
    
    Article Title: {title}
    Article Text (snippet): {full_text[:7000]}
    
    --- TASK 1: STRICT CATEGORIZATION ---
    Return tags (comma separated) based on these rules:
    1. ENGINEERS: Construction, Public Works, Energy, Arbitrary Buildings, Zoning, Ktimatologio (Technical).
       - IF it is a Law/FEK about these, tag ENGINEERS + LEGISLATION (NOT LEGAL).
    2. REAL_ESTATE: Property prices, Rents, Golden Visa, Buying/Selling, Airbnb, AADE Property Taxes.
    3. LEGAL: Court decisions (Areopagos, StE), Lawsuits, Criminal Law, Bar Association (DSA).
       - DO NOT tag as LEGAL if it is purely technical/construction.
    4. LEGISLATION: Any FEK, Law, Ministerial Decision.
    5. SOS: If there is a deadline, fine, or penalty.

    --- TASK 2: DETAILED SUMMARY (GREEK) ---
    - Write a summary in Greek using Bullet Points (•).
    - Capture ALL dates, deadlines, amounts (€), and legal references.
    - Do NOT be vague. Be precise.
    
    --- OUTPUT FORMAT ---
    TAGS: [Tags here]
    SUMMARY: [Summary here]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        tags = "GENERAL"
        summary = "Δεν μπόρεσε να παραχθεί περίληψη."
        
        if "TAGS:" in text and "SUMMARY:" in text:
            parts = text.split("SUMMARY:")
            tags = parts[0].replace("TAGS:", "").strip().upper()
            summary = parts[1].strip()
        else:
            # Fallback αν το AI δεν ακολουθήσει το format
            summary = text
            
        return tags, summary
    except Exception as e:
        print(f"AI Error: {e}")
        return None, None

# --- 4. IMAGE FETCH ---
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

# --- 5. MAIN LOOP ---
def run():
    print(f"🤖 [NomoTechi Deep-AI v2] Starting Scan...")
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds: return

    try:
        creds_dict = json.loads(json_creds)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("laws_database")
        sheet = sh.sheet1
        if sheet.acell('H1').value != 'image_url': sheet.update_cell(1, 8, 'image_url')
    except: return

    try:
        existing_data = sheet.get_all_records()
        existing_links = [row['link'] for row in existing_data]
    except: existing_data = []; existing_links = []
        
    new_items_count = 0
    
    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if not feed.entries: continue
            
            # 2 Άρθρα ανά πηγή για να μην καθυστερεί πολύ το Deep Scraping
            for entry in feed.entries[:2]: 
                if entry.link not in existing_links:
                    print(f"   📖 Reading Deep: {entry.title[:30]}...")
                    
                    # 1. Scrape Full Text (Μπαίνουμε μέσα στο site)
                    scraped_text = scrape_full_text(entry.link)
                    if not scraped_text: scraped_text = entry.summary # Αν αποτύχει, παίρνουμε την απλή περίληψη
                    
                    # 2. AI Analysis (Zητάμε Bullet Points)
                    tags, ai_summary = analyze_article_with_ai(entry.title, scraped_text)
                    
                    if not tags: tags = "GENERAL"
                    if not ai_summary: ai_summary = entry.summary 
                    
                    print(f"      ✅ AI Tags: {tags}")
                    
                    real_image_url = fetch_article_image(entry.link)

                    new_row = [
                        len(existing_data) + new_items_count + 1,
                        source_name,
                        entry.title,
                        ai_summary, # Εδώ θα μπουν τα Bullet Points
                        entry.link,
                        datetime.now().strftime("%Y-%m-%d"),
                        tags, 
                        real_image_url
                    ]
                    sheet.append_row(new_row)
                    new_items_count += 1
                    existing_links.append(entry.link)
                    
                    time.sleep(2) # Σεβασμός στον server
        except: pass

    print(f"🏁 Done. New articles: {new_items_count}")

if __name__ == "__main__":
    run()
