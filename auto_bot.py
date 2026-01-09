import os
import json
import gspread
import feedparser
from datetime import datetime
import time
import re
import requests
from bs4 import BeautifulSoup

# --- 1. CONFIG ---
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

def fetch_article_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                return og_image["content"]
    except:
        return ""
    return ""

def remove_accents(input_str):
    replacements = {'ά':'α','έ':'ε','ή':'η','ί':'ι','ό':'ο','ύ':'υ','ώ':'ω','Ά':'Α','Έ':'Ε','Ή':'Η','Ί':'Ι','Ό':'Ο','Ύ':'Υ','Ώ':'Ω','ϊ':'ι','ϋ':'υ'}
    for char, rep in replacements.items():
        input_str = input_str.replace(char, rep)
    return input_str.lower()

def clean_summary(text):
    text = re.sub('<[^<]+?>', '', text)
    return text[:500] + "..."

def guess_category_smart(title, summary, source_name):
    full_text = remove_accents(title + " " + summary)
    source_clean = remove_accents(source_name)
    
    fek_keywords = ['φεκ', 'εγκυκλιος', 'κυα', 'προεδρικο διαταγμα', 'νομοσχεδιο', 'τροπολογια', 'αποφαση υπουργου']
    is_fek = any(w in full_text for w in fek_keywords) or "e-nomothesia" in source_clean

    if is_fek:
        eng_relevant_words = ['αυθαιρετα', '4495', 'πολεοδομ', 'δομηση', 'κτιριοδομ', 'αδειες', 'οικοδομ', 'νοκ', 'δημοσια εργα', 'αναθεση', 'συμβαση', 'υποδομες', 'μετρο', 'πεδμεδε', 'μηχανικ', 'τεε', 'ενεργειακ', 'εξοικονομω', 'αντικειμενικ', 'στατικ', 'αντισεισμικ', 'σκυροδεμ']
        if any(w in full_text for w in eng_relevant_words):
            return "📜 Νομοθεσία: Μηχανικών & Έργων"
        return "📜 Νομοθεσία & ΦΕΚ"

    scores = {"eng_poleodomia": 0, "eng_energy": 0, "eng_projects": 0, "law_realestate": 0, "law_justice": 0, "finance": 0, "news_general": 0}

    if "b2green" in source_clean or "greenagenda" in source_clean:
        scores["eng_energy"] += 3
    elif "ypodomes" in source_clean or "pedmede" in source_clean:
        scores["eng_projects"] += 3
    elif "pomida" in source_clean:
        scores["law_realestate"] += 3
    elif "lawspot" in source_clean or "dsa" in source_clean:
        scores["law_justice"] += 3
    elif "taxheaven" in source_clean or "capital" in source_clean:
        scores["finance"] += 3

    # ΔΙΟΡΘΩΜΕΝΟΙ ΒΡΟΓΧΟΙ (Σωστό Indentation)
    poleodomia_words = ['αυθαιρετα', '4495', 'πολεοδομ', 'δομηση', 'κτιριοδομ', 'αδειες', 'οικοδομ', 'νοκ', 'τοπογραφικ', 'ταυτοτητα κτιριου', 'συντελεστης', 'υδομ']
    for w in poleodomia_words:
        if w in full_text:
            scores["eng_poleodomia"] += 2
            
    energy_words = ['εξοικονομω', 'φωτοβολταικ', 'ενεργεια', 'απε', 'ραε', 'υδρογονο', 'κλιματικ', 'περιβαλλον', 'ανακυκλωση', 'αποβλητα']
    for w in energy_words:
        if w in full_text:
            scores["eng_energy"] += 2
            
    project_words = ['διαγωνισμ', 'δημοσια εργα', 'αναθεση', 'συμβαση', 'υποδομες', 'μετρο', 'οδικος', 'πεδμεδε', 'μειοδοτ', 'αναδοχος', 'εργοταξιο', 'κατασκευαστικ', 'γεφυρα', 'αυτοκινητοδρομος', 'σιδηροδρομ']
    for w in project_words:
        if w in full_text:
            scores["eng_projects"] += 2
            
    estate_words = ['συμβολαιογραφ', 'μεταβιβαση', 'γονικη παροχη', 'κληρονομι', 'διαθηκη', 'αντικειμενικ', 'enfia', 'υποθηκοφυλακ', 'κτηματολογιο', 'ε9', 'ακινητ']
    for w in estate_words:
        if w in full_text:
            scores["law_realestate"] += 2

    disaster_words = ['ηφαιστειο', 'σεισμος', 'χιονια', 'κακοκαιρια', 'πυρκαγια', 'φωτια', 'πλημμυρα', 'καιρος']
    is_disaster = any(w in full_text for w in disaster_words)
    justice_words = ['δικαστηρι', 'αρεοπαγ', 'στε', 'ποινικ', 'αστικ', 'δικη', 'αγωγη', 'δικηγορ', 'ολομελεια', 'παραβαση', 'κατηγορουμεν']
    found_justice_words = sum(1 for w in justice_words if w in full_text)
    
    if is_disaster and found_justice_words < 2:
        scores["law_justice"] = -10 
    else:
        scores["law_justice"] += (found_justice_words * 2)

    fin_words = ['φορολογ', 'ααδε', 'mydata', 'εφορια', 'φπα', 'μισθοδοσια', 'τραπεζ', 'δανει', 'εφκα']
    for w in fin_words:
        if w in full_text:
            scores["finance"] += 2

    best_category = max(scores, key=scores.get)
    if scores[best_category] < 2:
        if any(w in full_text for w in ['εκλογες', 'παραταση', 'ανακοινωση']):
            return "📢 Θεσμικά & Ανακοινώσεις"
        return "🌐 Γενική Ενημέρωση"

    category_map = {
        "eng_poleodomia": "📐 Μηχανικοί: Πολεοδομία",
        "eng_energy": "🌱 Μηχανικοί: Ενέργεια & Περιβάλλον",
        "eng_projects": "✒️ Μηχανικοί: Έργα",
        "law_realestate": "🖋️ Συμβολαιογραφικά & Ακίνητα",
        "law_justice": "⚖️ Νομικά Θέματα",
        "finance": "💼 Φορολογικά & Οικονομία",
        "news_general": "🌐 Γενική Ενημέρωση"
    }
    return category_map[best_category]

# --- 5. MAIN ---
def run():
    print(f"🤖 [NomoTechi AI] Scanning with Image Scraping...")
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds: return
    try:
        creds_dict = json.loads(json_creds)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("laws_database")
        sheet = sh.sheet1
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
    headers = {'User-Agent': 'Mozilla/5.0'}

    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url, agent=headers['User-Agent'])
            if not feed.entries and feed.bozo: continue
            for entry in feed.entries[:3]: 
                if entry.link not in existing_links:
                    title = entry.title
                    summary = clean_summary(entry.summary if 'summary' in entry else "")
                    category = guess_category_smart(title, summary, source_name)
                    print(f"   📸 Getting image: {title[:20]}...")
                    real_image_url = fetch_article_image(entry.link)
                    new_row = [len(existing_data)+new_items_count+1, source_name, title, summary, entry.link, datetime.now().strftime("%Y-%m-%d"), category, real_image_url]
                    sheet.append_row(new_row)
                    new_items_count += 1
                    existing_links.append(entry.link)
        except:
            pass
    print(f"🏁 Done. New: {new_items_count}")

if __name__ == "__main__":
    run()
