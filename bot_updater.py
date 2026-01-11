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

# --- 2. DEEP SCRAPER ---
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

# --- 3. AI ANALYST (ROBUST) ---
def analyze_article_with_ai(title, full_text):
    if not HAS_AI: return "GENERAL", full_text[:300] + "..."
    
    prompt = f"""
    Analyze this Greek article.
    Title: {title}
    Text: {full_text[:7000]}
    
    TASK 1: Categorize (Comma separated tags). Rules:
    - ENGINEERS: Construction, Energy, Public Works, Zoning, Ktimatologio.
    - REAL_ESTATE: Property, Rents, Airbnb, Taxes on property.
    - LEGAL: Court decisions, Justice, Lawyers, Criminal Law.
    - LEGISLATION: FEK, Laws, Decisions.
    - SOS: Deadlines, Fines.
    
    TASK 2: Summary (Greek).
    - Create a structured summary with Bullet Points (•).
    - Include numbers, dates, and amounts.
    
    FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
    TAGS: [tag1, tag2]
    SUMMARY: [Your bullet points here]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        tags = "GENERAL"
        summary = "Δεν μπόρεσε να παραχθεί περίληψη."
        
        # Πιο έξυπνος διαχωρισμός
        if "TAGS:" in text and "SUMMARY:" in text:
            parts = text.split("SUMMARY:")
            tags = parts[0].replace("TAGS:", "").strip().upper()
            summary = parts[1].strip()
        else:
            summary = text # Fallback
            
        return tags, summary
    except Exception as e:
        print(f"AI Error: {e}")
        return "GENERAL", "AI Error during processing."

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
    print(f"🤖 [NomoTechi Repair] Starting...")
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds: return

    try:
        creds_dict = json.loads(json_creds)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("laws_database")
        sheet = sh.sheet1
        
        # --- FIXED: ΕΓΓΡΑΦΗ ΕΠΙΚΕΦΑΛΙΔΩΝ (ΓΙΑ ΝΑ ΜΗ ΧΑΝΟΝΤΑΙ ΟΙ ΚΑΤΗΓΟΡΙΕΣ) ---
        header = ['id', 'source', 'title', 'content', 'link', 'last_update', 'category', 'image_url']
        current_header = sheet.row_values(1)
        if current_header != header:
            print("🔧 Fixing Headers...")
            sheet.update('A1:H1', [header])
            
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
            
            for entry in feed.entries[:2]: 
                if entry.link not in existing_links:
                    print(f"   📖 Processing: {entry.title[:30]}...")
                    
                    scraped_text = scrape_full_text(entry.link)
                    if not scraped_text: scraped_text = entry.summary
                    
                    tags, ai_summary = analyze_article_with_ai(entry.title, scraped_text)
                    
                    # Καθαρισμός αν το AI απέτυχε
                    if len(tags) < 3: tags = "GENERAL"
                    
                    print(f"      🏷️ Tags: {tags}")
                    
                    real_image_url = fetch_article_image(entry.link)

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
                    existing_links.append(entry.link)
                    time.sleep(2)
        except: pass

    print(f"🏁 Done. New articles: {new_items_count}")

if __name__ == "__main__":
    run()
