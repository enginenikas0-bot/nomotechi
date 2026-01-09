import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime

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
        padding: 25px; color: white; border-radius: 12px; margin-bottom: 10px; text-align: center;
    }
    
    /* Tabs Styling - Κάνει τις καρτέλες πιο όμορφες */
    .stTabs [data-baseweb="tab-list"] {gap: 20px; justify-content: center;}
    .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .stTabs [aria-selected="true"] {background-color: #EFF6FF; color: #2563EB; font-weight: bold;}

    /* Cards */
    .news-card {
        background: white; border-radius: 12px; padding: 20px; height: 100%;
        border: 1px solid #F1F5F9; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: transform 0.2s;
    }
    .news-card:hover {transform: translateY(-3px); border-color: #cbd5e1;}
    
    .cat-badge {
        display: inline-block; padding: 4px 10px; border-radius: 20px; 
        font-size: 0.75rem; font-weight: 600; margin-bottom: 10px;
    }
    /* Χρώματα για κάθε κλάδο */
    .badge-eng {background: #E0F2FE; color: #0284C7;} /* Μηχανικοί - Γαλάζιο */
    .badge-law {background: #FEF2F2; color: #DC2626;} /* Νομικοί - Κόκκινο */
    .badge-fek {background: #F0FDF4; color: #16A34A;} /* ΦΕΚ - Πράσινο */
    .badge-gen {background: #F1F5F9; color: #475569;} /* Γενικά - Γκρι */

    a {text-decoration: none; color: #1E293B !important; font-weight: 700;}
    a:hover {color: #2563EB !important;}
</style>
""", unsafe_allow_html=True)

# --- 3. DATA LOGIC ---
def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        return gc.open("laws_database").sheet1
    except: return None

def load_data():
    sheet = get_db_connection()
    return sheet.get_all_records() if sheet else []

# Helper για να διαλέγουμε χρώμα badge
def get_badge_class(category):
    if "Μηχανικοί" in category: return "badge-eng"
    if "Νομικά" in category or "Συμβολαιο" in category: return "badge-law"
    if "Νομοθεσία" in category: return "badge-fek"
    return "badge-gen"

# Run Manual Scan (Backend)
def run_bot_update_manual():
    # Κώδικας σάρωσης (παραλείπεται για συντομία - είναι ίδιος με πριν)
    pass 

# --- 4. UI ---
# HEADER
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
    st.info("Φόρτωση βάσης δεδομένων... (Αν είναι η πρώτη φορά, τρέξτε Scan από το Admin)")
else:
    df = df.iloc[::-1].reset_index(drop=True) # Sort latest first

    # --- MAIN NAVIGATION (TABS) ---
    tabs = st.tabs(["🏠 Όλα (Ροή)", "📐 Μηχανικοί", "⚖️ Νομικοί / Συμβ.", "📜 Νομοθεσία (ΦΕΚ)", "⚙️ Admin"])

    # --- TAB 1: HOME (ΟΛΑ) ---
    with tabs[0]:
        # HERO ITEM
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

        # GRID FOR LATEST
        st.markdown("### 🔔 Πρόσφατη Ενημέρωση")
        cols = st.columns(3)
        for i, col in enumerate(cols):
            if i + 1 < len(df):
                row = df.iloc[i+1]
                badge = get_badge_class(row['category'])
                with col:
                    st.markdown(f"""
                    <div class="news-card">
                        <span class="cat-badge {badge}">{row['category'].split(':')[0]}</span>
                        <div style="font-weight:700; font-size:1.1rem; margin-bottom:10px;">
                            <a href="{row['link']}" target="_blank">{row['title']}</a>
                        </div>
                        <div style="font-size:0.9rem; color:#64748B;">{row['content'][:100]}...</div>
                    </div>
                    """, unsafe_allow_html=True)

    # --- TAB 2: ENGINEERS ---
    with tabs[1]:
        st.caption("Ειδήσεις για Πολεοδομία, Έργα, Εξοικονομώ & Τεχνική Νομοθεσία")
        eng_df = df[df['category'].str.contains("Μηχανικ|Πολεοδομ|Ενέργεια|Έργα|Θεσμικά", case=False)]
        
        for idx, row in eng_df.iterrows():
            st.markdown(f"""
            <div style="padding:15px; border-bottom:1px solid #E2E8F0;">
                <span class="cat-badge badge-eng">{row['category']}</span>
                <span style="font-size:1.1rem; font-weight:700; margin-left:10px;">
                    <a href="{row['link']}" target="_blank">{row['title']}</a>
                </span>
                <div style="color:#64748B; font-size:0.9rem; margin-top:5px;">{row['law']} • {row['last_update']}</div>
            </div>
            """, unsafe_allow_html=True)

    # --- TAB 3: LAWYERS / NOTARIES ---
    with tabs[2]:
        st.caption("Νομικά Θέματα, Δικαστήρια, Κτηματολόγιο, Συμβόλαια")
        law_df = df[df['category'].str.contains("Νομικ|Συμβολαιο|Δικηγόρ|Φορολογ", case=False)]
        
        for idx, row in law_df.iterrows():
            st.markdown(f"""
            <div style="padding:15px; border-bottom:1px solid #E2E8F0;">
                <span class="cat-badge badge-law">{row['category']}</span>
                <span style="font-size:1.1rem; font-weight:700; margin-left:10px;">
                    <a href="{row['link']}" target="_blank">{row['title']}</a>
                </span>
                <div style="color:#64748B; font-size:0.9rem; margin-top:5px;">{row['law']} • {row['last_update']}</div>
            </div>
            """, unsafe_allow_html=True)

    # --- TAB 4: LEGISLATION (FEK) ---
    with tabs[3]:
        st.info("📜 Εδώ εμφανίζονται αποκλειστικά ΦΕΚ, Εγκύκλιοι και Νομοσχέδια.")
        fek_df = df[df['category'].str.contains("Νομοθεσία|ΦΕΚ", case=False)]
        
        for idx, row in fek_df.iterrows():
            st.markdown(f"""
            <div style="background:#F0FDF4; padding:20px; border-radius:10px; margin-bottom:10px; border:1px solid #BBF7D0;">
                <span style="color:#16A34A; font-weight:800;">ΦΕΚ / ΑΠΟΦΑΣΗ</span>
                <div style="font-size:1.2rem; font-weight:700; margin-top:5px;">
                    <a href="{row['link']}" target="_blank" style="color:#14532D!important;">{row['title']}</a>
                </div>
                <div style="margin-top:10px;">{row['content']}</div>
            </div>
            """, unsafe_allow_html=True)

    # --- TAB 5: ADMIN ---
    with tabs[4]:
        pw = st.text_input("Κωδικός", type="password")
        if pw == st.secrets.get("admin_password", ""):
            if st.button("🚀 Force Scan (Σάρωση Τώρα)"):
                st.info("Η εντολή δόθηκε (Backend Placeholder)")
                # Εδώ καλείς τη function run_bot_update_manual αν θες να λειτουργεί και από το UI
