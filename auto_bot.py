import os
import json
import gspread
import feedparser
from datetime import datetime
import re

# --- 1. ΟΙ ΠΗΓΕΣ ---
RSS_FEEDS = {
    # ΝΟΜΟΘΕΣΙΑ & ΔΙΚΑΙΟΣΥΝΗ
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "⚖️ ΔΣΑ": "https://www.dsa.gr/rss.xml",
    "⚖️ Lawspot": "https://www.lawspot.gr/nomika-nea/feed",
    "🎓 Dikaiologitika": "https://www.dikaiologitika.gr/feed", 
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",

    # ΤΕΧΝΙΚΑ & ΠΕΡΙΒΑΛΛΟΝΤΙΚΑ
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "⚡ EnergyPress": "https://energypress.gr/feed",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    "👷 Michanikos": "https://www.michanikos-online.gr/feed/",
    "🌍 GreenAgenda": "https://greenagenda.gr/feed/",
    
    # ΑΚΙΝΗΤΑ & ΟΙΚΟΝΟΜΙΑ
    "🏠 POMIDA": "https://www.pomida.gr/feed/",
    "📐 Archetypes": "https://www.archetypes.gr/feed/",
    "💰 Capital": "https://www.capital.gr/rss/oikonomia"
}

# --- 2. ADVANCED AI CLASSIFIER ---
def remove_accents(input_str):
    """Βοηθητική συνάρτηση για να καθαρίζει τόνους (π.χ. άδεια -> αδεια)"""
    replacements = {
        'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
        'Ά': 'Α', 'Έ': 'Ε', 'Ή': 'Η', 'Ί': 'Ι', 'Ό': 'Ο', 'Ύ': 'Υ', 'Ώ': 'Ω',
        'ϊ': 'ι', 'ϋ': 'υ', 'ΐ': 'ι', 'ΰ': 'υ'
    }
    for char, replacement in replacements.items():
        input_str = input_str.replace(char, replacement)
    return input_str.lower()

def guess_category_smart(title, summary, source_name):
    # Ενωση κειμένου και καθαρισμός
    full_text = remove_accents(title + " " + summary)
    source_clean = remove_accents(source_name)

    # --- ΒΗΜΑ 1: HARD RULES ΒΑΣΕΙ ΠΗΓΗΣ (Source Weighting) ---
    # Κάποιες πηγές είναι μονοθεματικές. Τις εμπιστευόμαστε.
    if "e-nomothesia" in source_clean:
        return "📜 Νομοθεσία & ΦΕΚ"
    if "greenagenda" in source_clean or "b2green" in source_clean:
        # Εξαίρεση: Αν μιλάει για νόμο, πάει νομοθεσία, αλλιώς περιβάλλον
        if any(w in full_text for w in ['φεκ', 'τροπολογια', 'νομοσχεδιο']):
            return "📜 Νομοθεσία & ΦΕΚ"
        return "🌱 Μηχανικοί: Ενέργεια & Περιβάλλον"
    if "energypress" in source_clean:
        return "🌱 Μηχανικοί: Ενέργεια & Περιβάλλον"
    if "pomida" in source_clean:
        return "🖋️ Συμβολαιογραφικά & Ακίνητα"

    # --- ΒΗΜΑ 2: ΑΡΝΗΤΙΚΑ ΦΙΛΤΡΑ (SAFETY NET) ---
    # Λέξεις που δείχνουν φυσική καταστροφή ή γενικά νέα (ΓΙΑ ΝΑ ΜΗΝ ΜΠΑΙΝΟΥΝ ΣΤΑ ΝΟΜΙΚΑ)
    nature_words = ['ηφαιστειο', 'σεισμος', 'χιονια', 'κακοκαιρια', 'πυρκαγια', 'φωτια', 'πλημμυρα', 'καιρος', 'δελτιο τυπου', 'εκδηλωση', 'συνεδριο']
    is_nature_event = any(w in full_text for w in nature_words)

    # --- ΒΗΜΑ 3: ΛΕΞΕΙΣ ΚΛΕΙΔΙΑ ΜΕ ΠΡΟΤΕΡΑΙΟΤΗΤΑ ---

    # 1. ΝΟΜΟΘΕΣΙΑ (Απόλυτη Προτεραιότητα)
    if any(w in full_text for w in ['φεκ', 'εγκυκλιος', 'κυα', 'προεδriko διαταγμα', 'νομοσχεδιο', 'ψηφιστηκε', 'τροπολογια']):
        return "📜 Νομοθεσία & ΦΕΚ"

    # 2. ΜΗΧΑΝΙΚΟΙ - ΠΟΛΕΟΔΟΜΙΑ
    eng_keywords = ['αυθαιρετα', '4495', 'πολεοδομ', 'δομηση', 'κτιριοδομ', 'αδειες', 'οικοδομ', 'νοκ', 'τοπογραφικ', 'ταυτοτητα κτιριου', 'κτηματολογιο', 'δασικ']
    if any(w in full_text for w in eng_keywords):
        return "📐 Μηχανικοί: Πολεοδομία"

    # 3. ΜΗΧΑΝΙΚΟΙ - ΕΡΓΑ
    erga_keywords = ['διαγωνισμ', 'δημοσια εργα', 'αναθεση', 'συμβαση', 'υποδομες', 'μετρο', 'οδικος', 'πεδμεδε', 'μειοδοτ']
    if any(w in full_text for w in erga_keywords):
        return "✒️ Μηχανικοί: Έργα"

    # 4. ΕΝΕΡΓΕΙΑ (Αν δεν το έπιασε το Source Rule)
    energy_keywords = ['εξοικονομω', 'φωτοβολταικ', 'ενεργεια', 'απε', 'ραε', 'υδρογονο', 'κλιματικ', 'περιβαλλον', 'ανακυκλωση']
    if any(w in full_text for w in energy_keywords):
        return "🌱 Μηχανικοί: Ενέργεια & Περιβάλλον"

    # 5. ΣΥΜΒΟΛΑΙΟΓΡΑΦΙΚΑ & ΑΚΙΝΗΤΑ
    prop_keywords = ['συμβολαιογραφ', 'μεταβιβαση', 'γονικη παροχη', 'κληρονομι', 'διαθηκη', 'αντικειμενικ', 'enfia', 'υποθηκοφυλακ', 'ε9']
    if any(w in full_text for w in prop_keywords):
        return "🖋️ Συμβολαιογραφικά & Ακίνητα"

    # 6. ΝΟΜΙΚΑ (ΠΡΟΣΟΧΗ: Εδώ γινόταν το λάθος με το ηφαίστειο)
    # Τώρα μπαίνει ΜΟΝΟ αν δεν είναι φυσική καταστροφή, ή αν έχει πολύ ισχυρούς νομικούς όρους
    legal_keywords = ['δικαστηρι', 'αρεοπαγ', 'στε', 'ποινικ', 'αστικ', 'δικη', 'αγωγη', 'δικηγορ', 'ολομελεια', 'παραβαση', 'κατηγορουμεν']
    strong_legal = ['αρεοπαγ', 'στε', 'εφετειο', 'δικαστικη αποφαση'] # Αυτά κερδίζουν ακόμα και το ηφαίστειο
    
    has_legal_word = any(w in full_text for w in legal_keywords)
    has_strong_legal = any(w in full_text for w in strong_legal)

    if has_strong_legal: 
        return "⚖️ Νομικά Θέματα"
    if has_legal_word and not is_nature_event: 
        return "⚖️ Νομικά Θέματα"

    # 7. ΟΙΚΟΝΟΜΙΚΑ / ΦΟΡΟΛΟΓΙΚΑ
    if any(w in full_text for w in ['φορολογ', 'ααδε', 'mydata', 'εφορια', 'φπα', 'μισθοδοσια', 'τραπεζ', 'δανει', 'εφκα', 'συνταξ']):
        return "💼 Φορολογικά & Οικονομία"

    # 8. ΘΕΣΜΙΚΑ
    if any(w in full_text for w in ['εκλογες', 'ψηφοφορια', 'παραταση', 'ανακοινωση']):
        return "📢 Θεσμικά & Ανακοινώσεις"

    # DEFAULT (Αν είναι ηφαίστειο και δεν ταίριαξε πουθενά αλλού)
    return "🌐 Γενική Ενημέρωση"

# --- 3. Η ΜΗΧΑΝΗ ΤΟΥ ΡΟΜΠΟΤ ---
def run():
    print(f"🤖 [NomoTechi AI] Σάρωση και Κατηγοριοποίηση ξεκίνησε...")
    
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url, agent=headers['User-Agent'])
            if not feed.entries and feed.bozo: continue
                
            for entry in feed.entries[:5]: 
                if entry.link not in existing_links:
                    
                    title = entry.title
                    summary = entry.summary.replace("<p>", "").replace("</p>", "")[:250] + "..." if 'summary' in entry else ""
                    
                    # ΚΑΛΟΥΜΕ ΤΟΝ ΕΞΥΠΝΟ CLASSIFIER ΜΕ ΤΟ ΟΝΟΜΑ ΤΗΣ ΠΗΓΗΣ
                    category = guess_category_smart(title, summary, source_name)
                    
                    new_row = [
                        len(existing_data) + new_items_count + 1,
                        source_name,
                        title,
                        summary,
                        entry.link,
                        datetime.now().strftime("%Y-%m-%d"),
                        category
                    ]
                    
                    sheet.append_row(new_row)
                    new_items_count += 1
                    existing_links.append(entry.link)
                    print(f"   ✅ [{category}] {title[:30]}...")
                    
        except Exception:
            pass

    print(f"🏁 Ολοκληρώθηκε. Νέα άρθρα: {new_items_count}")

if __name__ == "__main__":
    run()
