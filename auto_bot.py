import os
import json
import gspread
import feedparser
from datetime import datetime

# ΡΥΘΜΙΣΕΙΣ
RSS_FEEDS = {
    "Taxheaven": "https://www.taxheaven.gr/rss",
    "B2Green": "https://news.b2green.gr/feed",
    "Lawspot": "https://www.lawspot.gr/nomika-nea/feed"
}

def guess_category(text):
    text = text.lower()
    if any(x in text for x in ['αυθαίρετα', 'νόμος 4495', 'πολεοδομία', 'δόμηση', 'κτιριοδομικός', 'αδειες', 'ν.ο.κ.', 'νοκ', 'οικοδομ']):
        return "📐 Πολεοδομία & Δόμηση"
    elif any(x in text for x in ['εξοικονομώ', 'ενέργεια', 'φωτοβολταϊκά', 'ανακύκλωση', 'περιβάλλον', 'ενεργειακ', 'green']):
        return "🌱 Ενέργεια & Περιβάλλον"
    elif any(x in text for x in ['φορολογ', 'ααδε', 'mydata', 'εφορία', 'εισφορές', 'φπα', 'μισθοδοσία', 'λογιστικ']):
        return "💼 Φορολογικά & Ασφαλιστικά"
    elif any(x in text for x in ['διαγωνισμ', 'δημόσια έργα', 'μελέτες', 'σύμβαση', 'ανάθεση', 'εσπα']):
        return "✒️ Δημόσια Έργα & ΕΣΠΑ"
    else:
        return "📢 Γενική Ενημέρωση"

def run():
    print("🤖 Το ρομποτάκι ξύπνησε...")
    
    # Σύνδεση με Google Sheets (Μέσω GitHub Secrets)
    # Εδώ διαβάζει τα κλειδιά από το περιβάλλον του GitHub
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds:
        print("❌ Σφάλμα: Δεν βρέθηκαν κωδικοί (GCP_CREDENTIALS).")
        return

    creds_dict = json.loads(json_creds)
    gc = gspread.service_account_from_dict(creds_dict)
    
    try:
        sh = gc.open("laws_database") # Βεβαιώσου ότι το όνομα είναι σωστό
        sheet = sh.sheet1
    except Exception as e:
        print(f"❌ Δεν βρέθηκε το Sheet: {e}")
        return

    existing_data = sheet.get_all_records()
    existing_links = [row['link'] for row in existing_data]
    new_items = 0

    for source, url in RSS_FEEDS.items():
        print(f"📡 Έλεγχος {source}...")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                if entry.link not in existing_links:
                    category = guess_category(entry.title + " " + entry.summary)
                    new_row = [
                        len(existing_data) + new_items + 1,
                        source,
                        entry.title,
                        entry.summary[:200] + "...",
                        entry.link,
                        datetime.now().strftime("%Y-%m-%d"),
                        category
                    ]
                    sheet.append_row(new_row)
                    new_items += 1
                    existing_links.append(entry.link)
                    print(f"✅ Προστέθηκε: {entry.title[:30]}...")
        except Exception as e:
            print(f"⚠️ Σφάλμα στο feed: {e}")

    print(f"🏁 Τέλος! Προστέθηκαν {new_items} νέα άρθρα.")

if __name__ == "__main__":
    run()