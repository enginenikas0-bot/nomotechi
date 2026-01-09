import os
import json
import gspread
import feedparser
from datetime import datetime
import time

# --- 1. Η "ELITE" ΛΙΣΤΑ ΠΗΓΩΝ (Μηχανικοί, Νομικοί, Κράτος) ---
RSS_FEEDS = {
    # === ΘΕΣΜΙΚΟΙ ΦΟΡΕΙΣ & ΝΟΜΟΘΕΣΙΑ ===
    "📜 E-Nomothesia (ΦΕΚ)": "https://www.e-nomothesia.gr/rss.xml",       # Η Νο1 πηγή για ΦΕΚ
    "🏛️ ΤΕΕ (Κεντρικό)": "https://web.tee.gr/feed/",                       # Τεχνικό Επιμελητήριο
    "⚖️ Δικηγορικός Σύλλογος (ΔΣΑ)": "https://www.dsa.gr/rss.xml",         # Δικηγορικός Σύλλογος Αθηνών
    "🎓 Dikaiologitika": "https://www.dikaiologitika.gr/feed",             # Διοικητική ενημέρωση
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",                        # Φορολογική & Εργατική Νομοθεσία

    # === ΜΗΧΑΝΙΚΟΙ & ΚΑΤΑΣΚΕΥΕΣ ===
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",                           # Δημόσια Έργα & Υποδομές
    "🌿 B2Green": "https://news.b2green.gr/feed",                          # Ενέργεια, Εξοικονομώ, Περιβάλλον
    "⚡ EnergyPress": "https://energypress.gr/feed",                         # ΑΠΕ, ΡΑΕ, Ενεργειακή Πολιτική
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",                          # Εργολήπτες Δημοσίων Έργων
    "👷 Michanikos Online": "https://www.michanikos-online.gr/feed/",      # Τεχνική Ενημέρωση

    # === ΝΟΜΙΚΟΙ & ΑΚΙΝΗΤΑ ===
    "⚖️ Lawspot": "https://www.lawspot.gr/nomika-nea/feed",                # Νομική Επικαιρότητα & Αναλύσεις
    "🏠 POMIDA (Ιδιοκτήτες)": "https://www.pomida.gr/feed/",               # Θέματα Ακινήτων & Ιδιοκτησίας
    "🌍 GreenAgenda": "https://greenagenda.gr/feed/",                      # Περιβαλλοντικό Δίκαιο & Κυκλική Οικονομία
    "📐 Archetypes": "https://www.archetypes.gr/feed/",                    # Αρχιτεκτονική & Design
    "💰 Capital (Οικονομία)": "https://www.capital.gr/rss/oikonomia"       # Οικονομικό Κλίμα
}

# --- 2. ΕΞΥΠΝΗ ΚΑΤΗΓΟΡΙΟΠΟΙΗΣΗ (Engineers vs Lawyers vs Notaries) ---
def guess_category(text):
    text = text.lower()
    
    # ΠΡΟΤΕΡΑΙΟΤΗΤΑ 1: ΝΟΜΟΘΕΣΙΑ & ΦΕΚ (Κοινό για όλους)
    if any(x in text for x in ['φεκ', 'εγκύκλιος', 'νομοσχέδιο', 'τροπολογία', 'κοινή υπουργική απόφαση', 'κυα', 'προεδρικό διάταγμα', 'νόμος του κράτους']):
        return "📜 Νομοθεσία & ΦΕΚ"

    # ΠΡΟΤΕΡΑΙΟΤΗΤΑ 2: ΜΗΧΑΝΙΚΟΙ
    elif any(x in text for x in ['αυθαίρετα', '4495', 'πολεοδομ', 'δόμηση', 'κτιριοδομ', 'αδειες', 'ν.ο.κ.', 'νοκ', 'τοπογραφικ', 'ηλεκτρονική ταυτότητα', 'id κτιρίου']):
        return "📐 Μηχανικοί: Πολεοδομία"
    elif any(x in text for x in ['εξοικονομώ', 'ενέργεια', 'φωτοβολταϊκά', 'περιβάλλον', 'απε', 'ραε', 'υδρογόνο', 'κλιματικ', 'ενεργειακ']):
        return "🌱 Μηχανικοί: Ενέργεια"
    elif any(x in text for x in ['διαγωνισμ', 'δημόσια έργα', 'μελέτες', 'σύμβαση', 'ανάθεση', 'εσπα', 'υποδομές', 'πεδμεδε', 'μειοδοτ']):
        return "✒️ Μηχανικοί: Έργα"
        
    # ΠΡΟΤΕΡΑΙΟΤΗΤΑ 3: ΝΟΜΙΚΟΙ & ΣΥΜΒΟΛΑΙΟΓΡΑΦΟΙ
    elif any(x in text for x in ['κτηματολόγιο', 'δασικ', 'συμβολαιογράφ', 'μεταβίβαση', 'γονική παροχή', 'κληρονομι', 'διαθήκη', 'αντικειμενικ', 'enfia', 'υποθηκοφυλακ']):
        return "🖋️ Συμβολαιογραφικά & Ακίνητα"
    elif any(x in text for x in ['δικαστήρι', 'αρεοπαγ', 'συμβούλιο της επικρατείας', 'στε', 'ποινικ', 'αστικ', 'δίκη', 'αγωγή', 'δικηγόρ', 'ολομέλεια', 'νομικό συμβούλιο']):
        return "⚖️ Νομικά Θέματα & Δικαιοσύνη"
    
    # ΠΡΟΤΕΡΑΙΟΤΗΤΑ 4: ΟΙΚΟΝΟΜΙΚΑ & ΘΕΣΜΙΚΑ
    elif any(x in text for x in ['φορολογ', 'ααδε', 'mydata', 'εφορία', 'εισφορές', 'φπα', 'μισθοδοσία', 'τράπεζες', 'δάνεια', 'εφκα']):
        return "💼 Φορολογικά & Οικονομία"
    elif any(x in text for x in ['τεε', 'εκλογές', 'σεμινάρι', 'συνέδριο', 'παράταση', 'ανακοίνωση', 'δελτίο τύπου']):
        return "📢 Θεσμικά & Ανακοινώσεις"
        
    else:
        return "🌐 Γενική Ενημέρωση"

# --- 3. Η ΜΗΧΑΝΗ ΤΟΥ ΡΟΜΠΟΤ ---
def run():
    print(f"🤖 [NomoTechi Bot] Ξεκινάει σάρωση στις: {datetime.now()}")
    
    # Σύνδεση με GitHub Secrets
    json_creds = os.environ.get("GCP_CREDENTIALS")
    if not json_creds:
        print("❌ Σφάλμα: Δεν βρέθηκαν κωδικοί (GCP_CREDENTIALS).")
        return

    # Σύνδεση με Google Sheets
    try:
        creds_dict = json.loads(json_creds)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open("laws_database")
        sheet = sh.sheet1
        print("✅ Σύνδεση με Βάση Δεδομένων επιτυχής.")
    except Exception as e:
        print(f"❌ Critical Error: Δεν μπορώ να συνδεθώ στο Sheet. {e}")
        return

    # Ανάκτηση υπαρχόντων για αποφυγή διπλότυπων
    try:
        existing_data = sheet.get_all_records()
        existing_links = [row['link'] for row in existing_data]
    except:
        existing_data = []
        existing_links = []
        print("⚠️ Η βάση είναι άδεια ή υπάρχει πρόβλημα ανάγνωσης.")
        
    new_items_count = 0

    # Κεφαλίδες User-Agent (Για να φαινόμαστε σαν Browser και όχι σαν Bot)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    # Σάρωση κάθε πηγής
    for source_name, url in RSS_FEEDS.items():
        print(f"📡 Scanning: {source_name}...")
        try:
            # Χρήση του 'agent' παραμέτρου ή headers αν χρειαστεί
            feed = feedparser.parse(url, agent=headers['User-Agent'])
            
            # Έλεγχος αν το feed είναι valid
            if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
                 # Μερικά feeds έχουν μικρολάθη αλλά δουλεύουν, το καταγράφουμε και συνεχίζουμε
                 pass

            if not feed.entries:
                print(f"   ⚠️ Κενό feed ή μπλοκαρισμένο: {source_name}")
                continue
                
            # Παίρνουμε τα 5 πιο πρόσφατα άρθρα από κάθε πηγή
            for entry in feed.entries[:5]: 
                if entry.link not in existing_links:
                    
                    # Καθαρισμός τίτλου και κειμένου
                    title = entry.title
                    summary = entry.summary if 'summary' in entry else ""
                    # Αν η περίληψη έχει HTML tags, τα κρατάμε απλά (clean text είναι πολύπλοκο χωρίς extra libs)
                    summary_clean = summary.replace("<p>", "").replace("</p>", "")[:250] + "..."
                    
                    category = guess_category(title + " " + summary_clean)
                    
                    new_row = [
                        len(existing_data) + new_items_count + 1, # ID
                        source_name,                              # Source
                        title,                                    # Title
                        summary_clean,                            # Content
                        entry.link,                               # Link
                        datetime.now().strftime("%Y-%m-%d"),      # Date (Fetch Date)
                        category                                  # Category
                    ]
                    
                    sheet.append_row(new_row)
                    new_items_count += 1
                    existing_links.append(entry.link)
                    print(f"   ✅ ΝΕΟ: [{category}] {title[:40]}...")
                    
        except Exception as e:
            print(f"   ❌ Error scanning {source_name}: {e}")
            continue # Συνεχίζουμε στην επόμενη πηγή

    print(f"🏁 Ολοκληρώθηκε. Προστέθηκαν {new_items_count} νέα θέματα στη βάση.")

if __name__ == "__main__":
    run()
