import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime
import time

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTechi | Professional Hub",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS (Smart Design) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif; color: #334155; background-color: #F8FAFC;}
    
    /* Header */
    .header-bar {
        background: linear-gradient(135deg, #0F172A 0%, #334155 100%);
        padding: 25px; color: white; border-radius: 12px; margin-bottom: 20px; text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {gap: 20px; justify-content: center;}
    .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; background-color: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);}
    .stTabs [aria-selected="true"] {background-color: #EFF6FF; color: #2563EB; font-weight: bold; border-bottom: 2px solid #2563EB;}

    /* Cards */
    .news-card {
        background: white; border-radius: 12px; padding: 20px; height: 100%;
        border: 1px solid #F1F5F9; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: transform 0.2s;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .news-card:hover {transform: translateY(-3px); border-color: #cbd5e1; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);}
    
    .cat-badge {
        display: inline-block; padding: 4px 10px; border-radius: 20px; 
        font-size: 0.75rem; font-weight: 600; margin-bottom: 10px; width: fit-content;
    }
    /* Χρώματα για κάθε κλάδο */
    .badge-eng {background: #E0F2FE; color: #0284C7;}
    .badge-law {background: #FEF2F2; color: #DC2626;}
    .badge-fek {background: #F0FDF4; color: #16A34A;}
    .badge-gen {background: #F1F5F9; color: #475569;}

    a {text-decoration: none; color: #1E293B !important; font-weight: 700;}
    a:hover {color: #2563EB !important;}
    
    .scan-log {font-family: monospace; font-size: 0.8rem; background: #1e293b; color: #bef264; padding: 10px; border-radius: 5px; margin-top: 10px;}
</style>
""", unsafe_allow_html=True)

# --- 3. ΡΥΘΜΙΣΕΙΣ ΠΗΓΩΝ (ΓΙΑ ΤΟ MANUAL SCAN) ---
RSS_FEEDS = {
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "⚖️ ΔΣΑ": "https://www.dsa.gr/rss.xml",
    "🎓 Dikaiologitika": "https://www.dikaiologitika.gr/feed", 
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "⚡ EnergyPress": "https://energypress.gr/feed",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    "👷 Michanikos": "https://www.michanikos-online.gr/feed/",
    "⚖️ Lawspot": "https://www.lawspot.gr/nomika-nea/feed",
    "🏠 POMIDA": "https://www.pomida.gr/feed/",
    "🌍 GreenAgenda": "https://greenagenda.gr/feed/",
    "📐 Archetypes": "https://www.archetypes.gr/feed/",
    "💰 Capital": "https://www.capital.gr/rss/oikonomia"
}

def guess_category(text):
    text = text.lower()
    if any(x in text for x in ['φεκ', 'εγκύκλιος', 'νομοσχέδιο', 'τροπολογία', 'κυα', 'προεδρικό διάταγμα']): return "📜 Νομοθεσία & ΦΕΚ"
    elif any(x in text for x in ['αυθαίρετα', '4495', 'πολεοδομ', 'δόμηση', 'κτιριοδομ', 'αδειες', 'νοκ', 'τοπογραφικ']): return "📐 Μηχανικοί: Πολεοδομία"
    elif any(x in text for x in ['εξοικονομώ', 'ενέργεια', 'φωτοβολταϊκά', 'περιβάλλον', 'απε', 'ραε']): return "🌱 Μηχανικοί: Ενέργεια"
    elif any(x in text for x in ['διαγωνισμ', 'δημόσια έργα', 'μελέτες', 'σύμβαση', 'ανάθεση', 'εσπα']): return "✒️ Μηχανικοί: Έργα"
    elif any(x in text for x in ['συμβολαιογράφ', 'μεταβίβαση', 'γονική παροχή', 'κληρονομι', 'διαθήκη', 'κτηματολόγιο']): return "🖋️ Συμβολαιογραφικά & Ακίνητα"
    elif any(x in text for x in ['δικαστήρι', 'αρεοπαγ', 'στε', 'ποινικ', 'αστικ', 'δίκη', 'αγωγή', 'δικηγόρ']): return "⚖️ Νομικά Θέματα"
    elif any(x in text for x in ['φορολογ', 'ααδε', 'mydata', 'εφορία', 'φπα', 'μισθοδοσία', 'τράπεζες']): return "💼 Φορολογικά & Οικονομία"
    elif any(x in text for x in ['τεε', 'εκλογές', 'σεμινάρι', 'ανακοίνωση']): return "📢 Θεσμικά"
    else: return "🌐 Γενική Ενημέρωση"

# --- 4. BACKEND FUNCTIONS ---
def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        return gc.open("laws_database").sheet1
    except: return None

def load_data():
    sheet = get_db_connection()
    return sheet.get_all_records() if sheet else []

def get_badge_class(category):
    if "Μηχανικοί" in category: return "badge-eng"
    if "Νομικά" in category or "Συμβολαιο" in category: return "badge-law"
    if "Νομοθεσία" in category: return "badge-fek"
    return "badge-gen"

# ΕΝΣΩΜΑΤΩΜΕΝΗ ΛΕΙΤΟΥΡΓΙΑ ΣΑΡΩΣΗΣ (ΓΙΑ ΤΟ ΚΟΥΜΠΙ)
def run_force_scan():
    sheet = get_db_connection()
    if not sheet: return 0, "Database Error"
    
    try:
        existing_data = sheet.get_all_records()
        existing_links = [row['link'] for row in existing_data]
    except:
        existing_data = []
        existing_links = []
        
    count = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    log_msg = ""
    
    progress_bar = st.progress(0)
    status = st.empty()
    
    total = len(RSS_FEEDS)
    current = 0
    
    for source, url in RSS_FEEDS.items():
        current += 1
        progress_bar.progress(current / total)
        status.text(f"Scanning: {source}...")
        
        try:
            feed = feedparser.parse(url, agent=headers['User-Agent'])
            if not feed.entries and feed.bozo: continue
            
            for entry in feed.entries[:3]:
                if entry.link not in existing_links:
                    summary = entry.summary.replace("<p>", "").replace("</p>", "")[:200] + "..." if 'summary' in entry else ""
                    cat = guess_category(entry.title + " " + summary)
                    
                    new_row = [
                        len(existing_data) + count + 1,
                        source,
                        entry.title,
                        summary,
                        entry.link,
                        datetime.now().strftime("%Y-%m-%d"),
                        cat
                    ]
                    sheet.append_row(new_row)
                    existing_links.append(entry.link)
                    count += 1
        except: pass
        
    progress_bar.empty()
    status.empty()
    return count

# --- 5. UI LAYOUT ---
st.markdown("""
<div class="header-bar">
    <div style="font-size: 2.2rem; font-weight: 800;">🏛️ NomoTechi</div>
    <div style="font-size: 1rem; opacity: 0.9;">Η Ενιαία Πύλη για Μηχανικούς, Δικηγόρους & Συμβολαιογράφους</div>
</div>
""", unsafe_allow_html=True)

# LOAD DATA
data = load_data()
df = pd.DataFrame(data)

if df.empty:
    st.warning("⚠️ Η βάση είναι άδεια. Πηγαίνετε στην καρτέλα 'Admin' και πατήστε 'Force Scan'.")

# --- MAIN NAVIGATION (TABS) ---
tabs = st.tabs(["🏠 Όλα (Ροή)", "📐 Μηχανικοί", "⚖️ Νομικοί / Συμβ.", "📜 Νομοθεσία (ΦΕΚ)", "⚙️ Admin"])

if not df.empty:
    df = df.iloc[::-1].reset_index(drop=True)

    # TAB 1: HOME
    with tabs[0]:
        if not df.empty:
            hero = df.iloc[0]
            badge_style = get_badge_class(hero['category'])
            st.markdown(f"""
            <div style="background:white; padding:30px; border-radius:15px; border-left:5px solid #0F172A; box-shadow:0 10px 15px -3px rgba(0,0,0,0.1); margin-bottom:30px;">
                <span class="cat-badge {badge_style}">{hero['category']}</span>
                <div style="font-size:1.8rem; font-weight:800; margin-top:10px; line-height:1.2;">
                    <a href="{hero['link']}" target="_blank">{hero['title']}</a>
                </div>
                <div style="color:#475569; margin-top:10px; font-size:1.1rem;">{hero['content']}</div>
                <div style="margin-top:15px; font-size:0.9rem; color:#94A3B8;">📅 {hero['last_update']} • Πηγή: {hero['law']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### 🔔 Πρόσφατη Ενημέρωση")
            cols = st.columns(3)
            for i, col in enumerate(cols):
                if i + 1 < len(df):
                    row = df.iloc[i+1]
                    badge = get_badge_class(row['category'])
                    with col:
                        st.markdown(f"""
                        <div class="news-card">
                            <div>
                                <span class="cat-badge {badge}">{row['category'].split(':')[0]}</span>
                                <div style="font-weight:700; font-size:1.1rem; margin-bottom:10px;">
                                    <a href="{row['link']}" target="_blank">{row['title']}</a>
                                </div>
                                <div style="font-size:0.9rem; color:#64748B;">{row['content'][:100]}...</div>
                            </div>
                            <div style="font-size:0.8rem; color:#94A3B8; margin-top:15px; border-top:1px solid #f1f5f9; padding-top:10px;">
                                {row['law']} • {row['last_update']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    # TAB 2: ENGINEERS
    with tabs[1]:
        st.caption("Πολεοδομία, Ενέργεια, Δημόσια Έργα & Τεχνική Νομοθεσία")
        eng_df = df[df['category'].str.contains("Μηχανικ|Πολεοδομ|Ενέργεια|Έργα|Θεσμικά", case=False)]
        for idx, row in eng_df.iterrows():
            st.markdown(f"""
            <div style="padding:15px; border-bottom:1px solid #E2E8F0; background:white;">
                <span class="cat-badge badge-eng">{row['category']}</span>
                <span style="font-size:1.1rem; font-weight:700; margin-left:10px;">
                    <a href="{row['link']}" target="_blank">{row['title']}</a>
                </span>
                <div style="color:#64748B; font-size:0.9rem; margin-top:5px;">{row['law']} • {row['last_update']}</div>
            </div>
            """, unsafe_allow_html=True)

    # TAB 3: LAWYERS
    with tabs[2]:
        st.caption("Νομικά Θέματα, Δικαστήρια, Κτηματολόγιο, Συμβόλαια")
        law_df = df[df['category'].str.contains("Νομικ|Συμβολαιο|Δικηγόρ|Φορολογ", case=False)]
        for idx, row in law_df.iterrows():
            st.markdown(f"""
            <div style="padding:15px; border-bottom:1px solid #E2E8F0; background:white;">
                <span class="cat-badge badge-law">{row['category']}</span>
                <span style="font-size:1.1rem; font-weight:700; margin-left:10px;">
                    <a href="{row['link']}" target="_blank">{row['title']}</a>
                </span>
                <div style="color:#64748B; font-size:0.9rem; margin-top:5px;">{row['law']} • {row['last_update']}</div>
            </div>
            """, unsafe_allow_html=True)

    # TAB 4: FEK
    with tabs[3]:
        st.info("📜 Εμφάνιση αποκλειστικά ΦΕΚ, Εγκυκλίων και Νομοθεσίας.")
        fek_df = df[df['category'].str.contains("Νομοθεσία|ΦΕΚ", case=False)]
        for idx, row in fek_df.iterrows():
            st.markdown(f"""
            <div style="background:#F0FDF4; padding:20px; border-radius:10px; margin-bottom:10px; border:1px solid #BBF7D0;">
                <span style="color:#16A34A; font-weight:800;">ΦΕΚ / ΑΠΟΦΑΣΗ</span> | <span style="font-size:0.9rem; color:#666;">{row['law']}</span>
                <div style="font-size:1.2rem; font-weight:700; margin-top:5px;">
                    <a href="{row['link']}" target="_blank" style="color:#14532D!important;">{row['title']}</a>
                </div>
                <div style="margin-top:10px; color:#374151;">{row['content']}</div>
            </div>
            """, unsafe_allow_html=True)

# TAB 5: ADMIN (MANUAL SCAN)
with tabs[4]:
    st.header("Διαχείριση")
    pw = st.text_input("Κωδικός Διαχειριστή", type="password")
    
    if pw == st.secrets.get("admin_password", ""):
        st.success("Admin Access: OK")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔄 Άμεση Ενημέρωση")
            st.write("Πιέστε για να σαρώσετε ΤΩΡΑ και τις 15 πηγές.")
            if st.button("🚀 Force Scan (Σάρωση Τώρα)", type="primary"):
                with st.spinner("Γίνεται σάρωση... Παρακαλώ περιμένετε 10-20 δευτερόλεπτα."):
                    new_count = run_force_scan()
                if new_count > 0:
                    st.success(f"Ολοκληρώθηκε! Βρέθηκαν {new_count} νέα άρθρα.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.info("Η σάρωση ολοκληρώθηκε. Δεν βρέθηκαν νέα άρθρα.")
        
        with col2:
            st.subheader("🗑️ Εργαλεία")
            if st.button("🧹 Clear Cache"):
                st.cache_data.clear()
                st.rerun()
            st.write("Καθαρισμός μνήμης αν κολλήσει.")
            
        st.divider()
        st.subheader("Raw Data Preview")
        st.dataframe(df)
