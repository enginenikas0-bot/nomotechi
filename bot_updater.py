import os
import json
import gspread
import feedparser
from datetime import datetime

# --- 1. ΟΛΕΣ ΟΙ ΠΗΓΕΣ ΕΙΔΗΣΕΩΝ (RSS) ---
RSS_FEEDS = {
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "⚖️ Lawspot": "https://www.lawspot.gr/nomika-nea/feed",
    "⚡ EnergyPress": "https://energypress.gr/feed",
    "🚜 PEDMEDE (Εργολήπτες)": "https://www.pedmede.gr/feed/",
    "👷 Michanikos": "https://www.michanikos-online.gr/feed/",
    "♻️ GreenAgenda": "https://greenagenda.gr/feed/",
    "📐 Archetypes": "https://www.archetypes.gr/feed/"
}

# --- 2. ΕΞΥΠΝΗ ΚΑΤΗΓΟΡΙΟΠΟΙΗΣΗ ---
def guess_category(text):
    text = text.lower()
    
    # Πολεοδομία & Δόμηση
    if any(x in text for x in ['αυθαίρετα', '4495', 'πολεοδομ', 'δόμηση', 'κτιριοδομ', 'αδειες', 'ν.ο.κ.', 'νοκ', 'οικοδομ', 'κατασκευ', 'real estate', 'κτηματολόγιο', 'δασικ', 'αρχιτεκτον', 'design']):
        return "📐 Πολεοδομία & Δόμηση"
    
    # Ενέργεια & Περιβάλλον
    elif any(x in text for x in ['εξοικονομώ', 'ενέργεια', 'φωτοβολταϊκά', 'ανακύκλωση', 'περιβάλλον', 'ενεργειακ', 'green', 'απε', 'ραε', 'energy', 'απόβλητα', 'κυκλική', 'κλιματικ', 'υδρογόνο']):
        return "🌱 Ενέργεια & Περιβάλλον"
    
    # Φορολογικά & Ασφαλιστικά
    elif any(x in text for x in ['φορολογ', 'ααδε', 'mydata', 'εφορία', 'εισφορές', 'φπα', 'μισθοδοσία', 'λογιστικ', 'οικονομικ', 'τσμεδε', 'εφκα', 'επιδότηση', 'αναπτυξιακ']):
        return "💼 Φορολογικά & Ασφαλιστικά"
    
    # Δημόσια Έργα & ΕΣΠΑ
    elif any(x in text for x in ['διαγωνισμ', 'δημόσια έργα', 'μελέτες', 'σύμβαση', 'ανάθεση', 'εσπα', 'υποδομές', 'μετρό', 'οδικός', 'παραχώρηση', 'πεδμεδε', 'διακήρυξη', 'μειοδοτ', 'εργοληπ']):
        return "✒️ Δημόσια Έργα & ΕΣΠΑ"
    
    # Θεσμικά ΤΕΕ & Επαγγελματικά
    elif any(x in text for x in ['τεε', 'μηχανικ', 'επιμελητήριο', 'εκλογές', 'πειθαρχικ', 'σεμινάρι', 'ημερίδα', 'συνέδριο']):
        return "🏛️ Θεσμικά ΤΕΕ & Επάγγελμα"
        
    else:
        return "📢 Γενική Ενημέρωση"

# --- 3. ΚΥΡΙΑ ΛΕΙΤΟΥΡΓΙΑ ΡΟΜΠΟΤ ---
def run():
    print("🤖 Το ρομποτάκι ξεκίνησε σάρωση σε 10 πηγές...")
    
    # Ανάκτηση κωδικών από τα Secrets του GitHub
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds:
        print("❌ Σφάλμα: Δεν βρέθηκαν κωδικοί (GCP_CREDENTIALS).")
        return

    try:
        creds_dict = json.loads(json_creds)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("laws_database") # Το όνομα του Sheet σου
        sheet = sh.sheet1
    except Exception as e:
        print(f"❌ Σφάλμα σύνδεσης με Google Sheets: {e}")
        return

    # Ανάγνωση υπαρχόντων για να μην έχουμε διπλότυπα
    try:
        existing_data = sheet.get_all_records()
        existing_links = [row['link'] for row in existing_data]
    except:
        existing_data = []
        existing_links = []
        
    new_items_count = 0

    # Σάρωση κάθε πηγής
    for source_name, url in RSS_FEEDS.items():
        print(f"📡 Έλεγχος: {source_name}...")
        try:
            feed = feedparser.parse(url)
            # Παίρνουμε τα 3 πιο πρόσφατα από κάθε πηγή
            for entry in feed.entries[:3]:
                if entry.link not in existing_links:
                    
                    category = guess_category(entry.title + " " + entry.summary)
                    
                    new_row = [
                        len(existing_data) + new_items_count + 1,
                        source_name,
                        entry.title,
                        entry.summary[:200] + "...",
                        entry.link,
                        datetime.now().strftime("%Y-%m-%d"),
                        category
                    ]
                    
                    sheet.append_row(new_row)
                    new_items_count += 1
                    existing_links.append(entry.link)
                    print(f"   ✅ Νέο: {entry.title[:40]}...")
                    
        except Exception as e:
            print(f"   ⚠️ Πρόβλημα με το feed {source_name}: {e}")

    print(f"🏁 Ολοκληρώθηκε! Προστέθηκαν {new_items_count} νέα θέματα.")

if __name__ == "__main__":
    run()

