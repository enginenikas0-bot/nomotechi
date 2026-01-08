import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime
import time

# --- 1. RYZMISEIS SELIDAS (PROFESSIONAL UI) ---
st.set_page_config(
    page_title="NomoTechi | Το Portal του Μηχανικού",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS για πιο "επαγγελματικό" look
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1E3A8A; text-align: center; font-weight: bold;}
    .sub-header {font-size: 1.2rem; color: #4B5563; text-align: center; margin-bottom: 2rem;}
    .card {background-color: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #e5e7eb; margin-bottom: 10px;}
    .source-tag {font-size: 0.8rem; background-color: #E0F2FE; color: #0369A1; padding: 2px 8px; border-radius: 4px;}
    .cat-tag {font-weight: bold; color: #333;}
</style>
""", unsafe_allow_html=True)

# --- 2. SYNDESH ME VASI ---
def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        sh = gc.open("laws_database")
        return sh.sheet1
    except Exception as e:
        st.error(f"⚠️ Σφάλμα σύνδεσης με τη Βάση: {e}")
        return None

def load_data():
    sheet = get_db_connection()
    if sheet:
        try:
            return sheet.get_all_records()
        except:
            return []
    return []

# --- 3. LOGIKI ENIMEROSIS (GIA TO ADMIN BUTTON) ---
# Αντιγράφουμε τη λογική και εδώ για να δουλεύει το manual κουμπί
RSS_FEEDS = {
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "⚖️ Lawspot": "https://www.lawspot.gr/nomika-nea/feed",
    "⚡ EnergyPress": "https://energypress.gr/feed",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    "👷 Michanikos": "https://www.michanikos-online.gr/feed/",
    "♻️ GreenAgenda": "https://greenagenda.gr/feed/",
    "📐 Archetypes": "https://www.archetypes.gr/feed/"
}

def guess_category(text):
    text = text.lower()
    if any(x in text for x in ['αυθαίρετα', '4495', 'πολεοδομ', 'δόμηση', 'κτιριοδομ', 'αδειες', 'ν.ο.κ.', 'νοκ', 'οικοδομ', 'κατασκευ', 'real estate', 'κτηματολόγιο', 'δασικ']):
        return "📐 Πολεοδομία & Δόμηση"
    elif any(x in text for x in ['εξοικονομώ', 'ενέργεια', 'φωτοβολταϊκά', 'ανακύκλωση', 'περιβάλλον', 'ενεργειακ', 'green', 'απε', 'ραε', 'απόβλητα']):
        return "🌱 Ενέργεια & Περιβάλλον"
    elif any(x in text for x in ['φορολογ', 'ααδε', 'mydata', 'εφορία', 'εισφορές', 'φπα', 'μισθοδοσία', 'λογιστικ', 'οικονομικ', 'τσμεδε', 'εφκα']):
        return "💼 Φορολογικά & Ασφαλιστικά"
    elif any(x in text for x in ['διαγωνισμ', 'δημόσια έργα', 'μελέτες', 'σύμβαση', 'ανάθεση', 'εσπα', 'υποδομές', 'μετρό', 'οδικός', 'πεδμεδε', 'διακήρυξη']):
        return "✒️ Δημόσια Έργα & ΕΣΠΑ"
    elif any(x in text for x in ['τεε', 'μηχανικ', 'επιμελητήριο', 'εκλογές', 'πειθαρχικ', 'σεμινάρι', 'ημερίδα', 'συνέδριο']):
        return "🏛️ Θεσμικά ΤΕΕ & Επάγγελμα"
    else:
        return "📢 Γενική Ενημέρωση"

def run_bot_update_manual():
    sheet = get_db_connection()
    if not sheet: return 0
    
    try:
        existing_data = sheet.get_all_records()
        existing_links = [row['link'] for row in existing_data]
    except:
        existing_data = []
        existing_links = []
    
    new_items_found = 0
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_feeds = len(RSS_FEEDS)
    current_feed = 0
    
    for source, url in RSS_FEEDS.items():
        current_feed += 1
        progress = current_feed / total_feeds
        progress_bar.progress(progress)
        status_text.text(f"📡 Σάρωση: {source}...")
        
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
            
    progress_bar.empty()
    status_text.empty()
    return new_items_found

# --- 4. NAVIGATION MENU ---
with st.sidebar:
    st.markdown("## 🏛️ NomoTechi")
    st.caption("Intelligence for Engineers")
    st.markdown("---")
    
    selected_page = st.radio(
        "Πλοήγηση:", 
        ["📊 Dashboard", "🔍 Αναζήτηση & Αρχείο", "⚙️ Διαχείριση (Admin)"],
        index=0
    )
    
    st.markdown("---")
    st.info("💡 Tip: Η βάση ενημερώνεται αυτόματα κάθε πρωί στις 08:00.")

# --- LOAD DATA ---
data = load_data()
df = pd.DataFrame(data)

# --- PAGE 1: DASHBOARD ---
if selected_page == "📊 Dashboard":
    st.markdown('<p class="main-header">NomoTechi Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Η καθημερινή ενημέρωση του Μηχανικού σε μία οθόνη</p>', unsafe_allow_html=True)
    
    if not df.empty:
        # Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Σύνολο Άρθρων", len(df))
        col2.metric("Πηγές Ενημέρωσης", len(RSS_FEEDS))
        
        # Υπολογισμός σημερινών άρθρων
        today = datetime.now().strftime("%Y-%m-%d")
        today_articles = df[df['last_update'] == today].shape[0]
        col3.metric("Σημερινά Άρθρα", today_articles, delta=today_articles)
        
        col4.metric("Κατάσταση", "Online 🟢")
        
        st.markdown("---")
        st.subheader("🔥 Τελευταίες Ειδήσεις")
        
        # Show top 10 latest
        df_sorted = df.iloc[::-1].head(10)
        
        for index, row in df_sorted.iterrows():
            with st.container():
                c1, c2 = st.columns([0.85, 0.15])
                with c1:
                    st.markdown(f"**{row['title']}**")
                    st.caption(f"{row['last_update']} | {row['law']}")
                with c2:
                    st.markdown(f"*{row['category']}*")
                
                with st.expander("Περίληψη"):
                    st.write(row['content'])
                    st.markdown(f"👉 [Διαβάστε το πλήρες άρθρο]({row['link']})")
                st.divider()
    else:
        st.warning("Η βάση δεδομένων είναι κενή. Πηγαίνετε στο μενού Admin για αρχικοποίηση.")

# --- PAGE 2: SEARCH & FILTER ---
elif selected_page == "🔍 Αναζήτηση & Αρχείο":
    st.header("🗂️ Βιβλιοθήκη Ειδήσεων")
    
    if not df.empty:
        # --- FILTERS SECTION ---
        with st.expander("🔎 Φίλτρα Αναζήτησης", expanded=True):
            col_search, col_cat, col_source = st.columns([2, 1, 1])
            
            with col_search:
                search_term = st.text_input("Αναζήτηση (π.χ. αυθαίρετα, εξοικονομώ)...")
            
            with col_cat:
                categories = sorted(df['category'].unique().tolist()) if 'category' in df.columns else []
                selected_cats = st.multiselect("Κατηγορία", categories)
                
            with col_source:
                sources = sorted(df['law'].unique().tolist())
                selected_sources = st.multiselect("Πηγή", sources)
        
        # --- FILTERING LOGIC ---
        df_filtered = df.copy()
        
        # Filter by text
        if search_term:
            df_filtered = df_filtered[df_filtered['title'].str.contains(search_term, case=False) | df_filtered['content'].str.contains(search_term, case=False)]
            
        # Filter by category
        if selected_cats:
            df_filtered = df_filtered[df_filtered['category'].isin(selected_cats)]
            
        # Filter by source
        if selected_sources:
            df_filtered = df_filtered[df_filtered['law'].isin(selected_sources)]
            
        # Sort latest first
        df_filtered = df_filtered.iloc[::-1]
        
        st.markdown(f"**Βρέθηκαν {len(df_filtered)} αποτελέσματα:**")
        st.divider()
        
        # --- DISPLAY RESULTS ---
        for index, row in df_filtered.iterrows():
            st.markdown(f"### {row['title']}")
            
            # Badge Line
            col_badges = st.columns([1, 1, 4])
            col_badges[0].markdown(f"📅 `{row['last_update']}`")
            col_badges[1].markdown(f"🏷️ `{row['category']}`")
            col_badges[2].markdown(f"🔗 **{row['law']}**")
            
            st.write(row['content'])
            st.markdown(f"[Διαβάστε περισσότερα στο {row['law']} ↗]({row['link']})")
            st.markdown("---")

    else:
        st.info("Δεν υπάρχουν δεδομένα.")

# --- PAGE 3: ADMIN ---
elif selected_page == "⚙️ Διαχείριση (Admin)":
    st.header("🔐 Κέντρο Ελέγχου")
    
    password = st.text_input("Κωδικός Διαχειριστή", type="password")
    
    if password == st.secrets.get("admin_password", ""):
        st.success("Είσοδος επιτυχής")
        
        st.subheader("🛠️ Εργαλεία")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🔄 Χειροκίνητος Συγχρονισμός")
            st.write("Σάρωση και των 10 πηγών τώρα.")
            if st.button("🚀 Έναρξη Σάρωσης", type="primary"):
                count = run_bot_update_manual()
                if count > 0:
                    st.success(f"Βρέθηκαν {count} νέα άρθρα!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.info("Δεν βρέθηκαν νέα άρθρα.")
        
        with col2:
            st.markdown("### 🗑️ Καθαρισμός Cache")
            st.write("Αν κολλήσει η εφαρμογή.")
            if st.button("🧹 Clear Cache"):
                st.cache_data.clear()
                st.rerun()
        
        st.divider()
        st.subheader("📋 Προβολή Δεδομένων (Raw)")
        st.dataframe(df, use_container_width=True)
        
    elif password != "":
        st.error("Λάθος κωδικός.")
