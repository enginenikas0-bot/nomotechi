import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime

# --- ΡΥΘΜΙΣΕΙΣ ΣΕΛΙΔΑΣ (PROFESSIONAL LOOK) ---
st.set_page_config(
    page_title="NomoTechi | Νομική Ενημέρωση Μηχανικών",
    page_icon="🏛️",
    layout="wide"
)

# --- ΣΥΝΔΕΣΗ ΜΕ GOOGLE SHEETS ---
def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        sh = gc.open("laws_database")
        return sh.sheet1
    except Exception as e:
        st.error(f"⚠️ Σφάλμα σύνδεσης συστήματος: {e}")
        return None

def load_data():
    sheet = get_db_connection()
    if sheet:
        try:
            return sheet.get_all_records()
        except:
            return []
    return []

# --- ΛΟΓΙΚΗ ΚΑΤΗΓΟΡΙΟΠΟΙΗΣΗΣ (ΕΠΙΣΗΜΑ ΣΥΜΒΟΛΑ) ---
def guess_category(text):
    text = text.lower()
    # Χρησιμοποιούμε πιο "αυστηρά" σύμβολα
    if any(x in text for x in ['αυθαίρετα', 'νόμος 4495', 'πολεοδομία', 'δόμηση', 'κτιριοδομικός', 'αδειες', 'ν.ο.κ.', 'νοκ']):
        return "📐 Πολεοδομία & Δόμηση"
    elif any(x in text for x in ['εξοικονομώ', 'ενέργεια', 'φωτοβολταϊκά', 'ανακύκλωση', 'περιβάλλον', 'ενεργειακ']):
        return "🌱 Ενέργεια & Περιβάλλον"
    elif any(x in text for x in ['φορολογ', 'ααδε', 'mydata', 'εφορία', 'εισφορές', 'φπα', 'μισθοδοσία']):
        return "💼 Φορολογικά & Ασφαλιστικά"
    elif any(x in text for x in ['διαγωνισμ', 'δημόσια έργα', 'μελέτες', 'σύμβαση', 'ανάθεση']):
        return "✒️ Δημόσια Έργα & Συμβάσεις"
    else:
        return "📢 Γενική Ενημέρωση"

# --- ΛΕΙΤΟΥΡΓΙΑ ΣΥΓΧΡΟΝΙΣΜΟΥ (BACKEND) ---
def run_bot_update():
    RSS_FEEDS = {
        "Taxheaven": "https://www.taxheaven.gr/rss",
        "B2Green": "https://news.b2green.gr/feed",
        "Lawspot": "https://www.lawspot.gr/nomika-nea/feed"
    }
    
    sheet = get_db_connection()
    if not sheet: return 0
    
    existing_data = sheet.get_all_records()
    existing_links = [row['link'] for row in existing_data]
    
    new_items_found = 0
    
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]: 
                if entry.link not in existing_links:
                    
                    category = guess_category(entry.title + " " + entry.summary)
                    
                    new_row = [
                        len(existing_data) + new_items_found + 1,
                        source,
                        entry.title,
                        entry.summary[:200] + "...",
                        entry.link,
                        datetime.now().strftime("%Y-%m-%d"),
                        category 
                    ]
                    sheet.append_row(new_row)
                    new_items_found += 1
                    existing_links.append(entry.link)
        except Exception:
            pass # Αθόρυβη λειτουργία σε περίπτωση λάθους feed
            
    return new_items_found

# --- UI ΕΦΑΡΜΟΓΗΣ (FRONTEND) ---

# Sidebar με πιο επίσημο ύφος
st.sidebar.markdown("## 🏛️ NomoTechi")
st.sidebar.caption("Πύλη Νομικής Ενημέρωσης Μηχανικών")
st.sidebar.markdown("---")

# Φόρτωση δεδομένων
data = load_data()
df = pd.DataFrame(data)

# Φίλτρα
st.sidebar.subheader("🗂️ Φίλτρα Αναζήτησης")
if not df.empty and 'category' in df.columns:
    unique_categories = df['category'].unique().tolist()
    # Ταξινόμηση κατηγοριών αλφαβητικά
    unique_categories.sort()
    selected_cats = st.sidebar.multiselect("Επιλέξτε Θεματολογία:", unique_categories, default=unique_categories)
else:
    selected_cats = []

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Διαχείριση")

# Κουμπιά Διαχείρισης (Πιο τεχνικά)
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🔄 Ανανέωση"):
        st.cache_data.clear()
        st.rerun()
with col2:
    if st.button("📡 Σύστημα"): # Αντί για "Ρομποτάκι"
        with st.spinner("Συγχρονισμός..."):
            count = run_bot_update()
        if count > 0:
            st.toast(f"✅ Προστέθηκαν {count} νέα θέματα!", icon="✅")
            st.cache_data.clear()
            st.rerun()
        else:
            st.toast("Το σύστημα είναι ενήμερο.", icon="ℹ️")

# --- ΚΥΡΙΩΣ ΠΕΡΙΟΧΗ ---
st.title("Επικαιρότητα & Νομοθεσία")
st.markdown("**Τελευταία Ενημέρωση:** " + datetime.now().strftime("%d/%m/%Y"))
st.divider()

if not df.empty:
    if 'category' in df.columns:
        df_filtered = df[df['category'].isin(selected_cats)]
    else:
        df_filtered = df
    
    if not df_filtered.empty:
        df_filtered = df_filtered.iloc[::-1]

        for index, row in df_filtered.iterrows():
            # Κάρτα Είδησης με minimal σχεδιασμό
            with st.container():
                # Τίτλος με εικονίδιο κατηγορίας στην αρχή αν θέλουμε, ή καθαρό
                st.subheader(f"{row['title']}")
                
                # Metadata line
                col_meta1, col_meta2 = st.columns([0.7, 0.3])
                with col_meta1:
                    # Εμφάνιση ετικέτας με χρώμα ανάλογα την κατηγορία (Streamlit native badge)
                    st.caption(f"📅 {row['last_update']} | Πηγή: {row['law']}")
                with col_meta2:
                    # Ειδική μορφοποίηση για την κατηγορία
                    st.markdown(f"**{row['category']}**")
                
                st.write(row['content'])
                st.markdown(f"🔗 [Διαβάστε το πλήρες κείμενο]({row['link']})")
                st.divider()
    else:
        st.info("Δεν βρέθηκαν αποτελέσματα με τα επιλεγμένα φίλτρα.")
else:
    st.warning("Η βάση δεδομένων είναι προσωρινά μη διαθέσιμη. Πατήστε 'Σύστημα' για ενημέρωση.")
