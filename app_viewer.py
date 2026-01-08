import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime

# --- 1. ΡΥΘΜΙΣΕΙΣ ΣΕΛΙΔΑΣ (Setup) ---
st.set_page_config(
    page_title="NomoTechi | Portal Μηχανικών",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ΣΥΝΔΕΣΗ ΜΕ ΒΑΣΗ (Google Sheets) ---
def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        sh = gc.open("laws_database")
        return sh.sheet1
    except Exception as e:
        st.error(f"⚠️ Σφάλμα σύνδεσης: {e}")
        return None

def load_data():
    sheet = get_db_connection()
    if sheet:
        try:
            return sheet.get_all_records()
        except:
            return []
    return []

# --- 3. ΛΟΓΙΚΗ ΚΑΤΗΓΟΡΙΩΝ (Smart Tagging) ---
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

# --- 4. ΛΕΙΤΟΥΡΓΙΑ ΡΟΜΠΟΤ (Backend Sync) ---
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
            pass 
            
    return new_items_found

# --- 5. UI & MENU (Frontend) ---

# --- SIDEBAR MENU ---
st.sidebar.title("🏛️ NomoTechi")
st.sidebar.caption("Σύμβουλος Μηχανικού")
st.sidebar.markdown("---")

# Το Κεντρικό Μενού Πλοήγησης
menu_options = ["🏠 Αρχική (Όλα τα θέματα)", "📂 Ανά Κατηγορία", "⚙️ Σύστημα (Admin)"]
selected_page = st.sidebar.radio("Πλοήγηση:", menu_options)

st.sidebar.markdown("---")
st.sidebar.info("© 2026 Engineer Legal Hub")


# --- Φόρτωση Δεδομένων ---
data = load_data()
df = pd.DataFrame(data)


# --- ΣΕΛΙΔΑ 1: ΑΡΧΙΚΗ (Dashboard) ---
if selected_page == "🏠 Αρχική (Όλα τα θέματα)":
    st.title("📰 Ροή Ειδήσεων & Νομοθεσίας")
    st.caption("Όλες οι εξελίξεις για τον Μηχανικό σε πραγματικό χρόνο.")
    
    if not df.empty:
        # Στατιστικά (Metrics) - Δείχνει ωραίο επαγγελματικά
        col1, col2, col3 = st.columns(3)
        col1.metric("Σύνολο Άρθρων", len(df))
        col2.metric("Τελευταία Ενημέρωση", datetime.now().strftime("%d/%m"))
        col3.metric("Πηγές", "3 (Live)")
        st.divider()
        
        # Εμφάνιση όλων (Ταξινόμηση: Νεότερα πρώτα)
        df_sorted = df.iloc[::-1]
        
        for index, row in df_sorted.iterrows():
            with st.container():
                st.subheader(f"{row['title']}")
                
                # Metadata Line
                c1, c2 = st.columns([3, 1])
                c1.caption(f"📅 {row['last_update']} | Πηγή: {row['law']}")
                c2.markdown(f"**{row['category']}**") # Η κατηγορία εμφανίζεται bold δεξιά
                
                st.write(row['content'])
                st.markdown(f"🔗 [Διαβάστε περισσότερα]({row['link']})")
                st.divider()
    else:
        st.info("Η βάση δεδομένων είναι κενή. Πηγαίνετε στο μενού 'Σύστημα' για ενημέρωση.")


# --- ΣΕΛΙΔΑ 2: ΚΑΤΗΓΟΡΙΕΣ (Φίλτρα) ---
elif selected_page == "📂 Ανά Κατηγορία":
    st.title("🗂️ Θεματική Αναζήτηση")
    
    if not df.empty and 'category' in df.columns:
        # Δημιουργία λίστας κατηγοριών
        categories = sorted(df['category'].unique().tolist())
        
        # Dropdown Menu για επιλογή
        selected_category = st.selectbox("Επιλέξτε τον τομέα που σας ενδιαφέρει:", categories)
        
        st.divider()
        
        # Φιλτράρισμα
        df_filtered = df[df['category'] == selected_category].iloc[::-1]
        
        if not df_filtered.empty:
            for index, row in df_filtered.iterrows():
                with st.expander(f"{row['last_update']} - {row['title']}", expanded=True):
                    st.write(row['content'])
                    st.markdown(f"[Μετάβαση στο άρθρο]({row['link']})")
        else:
            st.warning("Δεν βρέθηκαν άρθρα σε αυτή την κατηγορία.")
    else:
        st.warning("Δεν υπάρχουν κατηγοριοποιημένα δεδομένα ακόμα.")


# --- ΣΕΛΙΔΑ 3: ADMIN (Κρυφά εργαλεία) ---
# --- ΣΕΛΙΔΑ 3: ADMIN (Κλειδωμένη) ---
elif selected_page == "⚙️ Σύστημα (Admin)":
    st.header("🔐 Περιοχή Διαχειριστή")
    
    # Ζητάμε κωδικό
    password_input = st.text_input("Εισάγετε κωδικό διαχειριστή:", type="password")
    
    # Έλεγχος κωδικού (διαβάζει από τα Secrets)
    if password_input == st.secrets["admin_password"]:
        
        st.success("Επιτυχής είσοδος! ✅")
        st.divider()
        
        st.warning("⚠️ Προσοχή: Οι ενέργειες εδώ επηρεάζουν τη βάση δεδομένων.")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("🤖 Συγχρονισμός")
            if st.button("🚀 Έναρξη Σάρωσης", type="primary"):
                with st.spinner("Γίνεται σύνδεση με πηγές..."):
                    count = run_bot_update()
                if count > 0:
                    st.toast(f"Βρέθηκαν {count} νέα άρθρα!", icon="🎉")
                    st.cache_data.clear()
                else:
                    st.toast("Το σύστημα είναι πλήρως ενημερωμένο.", icon="✅")
                    
        with col_b:
            st.subheader("💾 Βάση Δεδομένων")
            if st.button("🔄 Ανανέωση Προβολής"):
                st.cache_data.clear()
                st.rerun()
                
        st.markdown("---")
        st.subheader("📊 Raw Data (Excel View)")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
    elif password_input != "":
        st.error("❌ Λάθος κωδικός πρόσβασης.")
    else:
        st.info("Η περιοχή αυτή είναι προσβάσιμη μόνο από τον διαχειριστή.")

