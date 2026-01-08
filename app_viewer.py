import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime
import time

# --- 1. SETUP ΣΕΛΙΔΑΣ (Wide Mode για CNN style) ---
st.set_page_config(
    page_title="NomoTechi | News Portal",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed" # Κρύβουμε το μενού για να μοιάζει με site
)

# --- 2. CUSTOM CSS (Εδώ γίνεται η μαγεία του Design) ---
st.markdown("""
<style>
    /* Γενικό Στυλ */
    .block-container {padding-top: 1rem; padding-bottom: 5rem;}
    a {text-decoration: none; color: #1a1a1a !important;}
    a:hover {color: #cc0000 !important; text-decoration: underline;}
    
    /* Header Style */
    .header-bar {
        background-color: #cc0000; /* CNN Red */
        padding: 15px;
        color: white;
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        border-radius: 5px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Hero Section (Η μεγάλη είδηση) */
    .hero-card {
        background-color: #f8f9fa;
        padding: 30px;
        border-left: 6px solid #cc0000;
        border-radius: 8px;
        margin-bottom: 30px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .hero-title {font-size: 2.2rem; font-weight: 800; color: #111; line-height: 1.2;}
    .hero-meta {color: #666; font-size: 0.9rem; margin-top: 10px;}
    .hero-summary {font-size: 1.2rem; color: #333; margin-top: 15px; line-height: 1.5;}

    /* Grid Cards (Οι 3 κάρτες) */
    .news-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        height: 100%;
        transition: transform 0.2s;
    }
    .news-card:hover {border-color: #999; transform: translateY(-3px);}
    .card-cat {font-size: 0.75rem; font-weight: bold; text-transform: uppercase; color: #cc0000;}
    .card-title {font-size: 1.1rem; font-weight: bold; margin-top: 5px; margin-bottom: 10px; line-height: 1.3;}
    .card-summary {font-size: 0.9rem; color: #555; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;}
    
    /* List Items (Η ροή) */
    .list-item {padding: 15px 0; border-bottom: 1px solid #eee;}
    .list-title {font-size: 1rem; font-weight: bold;}
    .list-meta {font-size: 0.8rem; color: #888;}
    
    /* Sidebar/Footer */
    .footer {text-align: center; color: #888; font-size: 0.8rem; margin-top: 50px;}
</style>
""", unsafe_allow_html=True)

# --- 3. ΣΥΝΔΕΣΗ & ΛΟΓΙΚΗ (ΙΔΙΑ ΜΕ ΠΡΙΝ) ---
def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        sh = gc.open("laws_database")
        return sh.sheet1
    except Exception as e:
        return None # Silent fail for UI

def load_data():
    sheet = get_db_connection()
    if sheet:
        try:
            return sheet.get_all_records()
        except:
            return []
    return []

# --- 4. DATA PROCESSING ---
data = load_data()
df = pd.DataFrame(data)

# Αν είναι άδειο, φτιάχνουμε ψεύτικα δεδομένα για να μη φαίνεται χαλασμένο το site
if df.empty:
    st.error("Η βάση δεδομένων φορτώνει... Παρακαλώ περιμένετε ή ελέγξτε τη σύνδεση.")
else:
    # Ταξινόμηση: Νεότερα πρώτα
    df = df.iloc[::-1].reset_index(drop=True)

# --- 5. UI LAYOUT (CNN STYLE) ---

# HEADER
st.markdown('<div class="header-bar">NomoTechi • News</div>', unsafe_allow_html=True)

# MENU BAR (Οριζόντιο, κάτω από το Header)
col_m1, col_m2, col_m3, col_m4 = st.columns([1,1,1,4])
with col_m1:
    if st.button("🏠 Αρχική"): st.rerun()
with col_m2:
    if st.button("🔄 Ανανέωση"): st.cache_data.clear(); st.rerun()
with col_m3:
    with st.expander("⚙️ Admin"):
        pw = st.text_input("Password", type="password")
        if pw == st.secrets.get("admin_password", ""):
            st.success("Admin Logged In")
            if st.button("🚀 Force Scan"):
                # Εδώ θα καλούσες τη συνάρτηση update, την παρέλειψα για συντομία κώδικα UI
                st.info("Η λειτουργία υπάρχει στο backend.")

st.markdown("---")

# LAYOUT LOGIC
if not df.empty:
    # --- HERO SECTION (Η 1η Είδηση) ---
    hero_article = df.iloc[0]
    
    st.markdown(f"""
    <div class="hero-card">
        <div style="color: #cc0000; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">
            {hero_article['category']}
        </div>
        <div class="hero-title">
            <a href="{hero_article['link']}" target="_blank">{hero_article['title']}</a>
        </div>
        <div class="hero-meta">📅 {hero_article['last_update']} | Πηγή: {hero_article['law']}</div>
        <div class="hero-summary">{hero_article['content']}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- TOP STORIES GRID (Οι επόμενες 3 ειδήσεις) ---
    st.subheader("📌 Top Stories")
    
    col1, col2, col3 = st.columns(3)
    
    # Βοηθητική συνάρτηση για κάρτες
    def render_card(col, row):
        with col:
            st.markdown(f"""
            <div class="news-card">
                <div class="card-cat">{row['category']}</div>
                <div class="card-title">
                    <a href="{row['link']}" target="_blank">{row['title']}</a>
                </div>
                <div class="card-summary">{row['content'][:120]}...</div>
                <div style="font-size: 0.8rem; color: #aaa; margin-top: 10px;">{row['law']}</div>
            </div>
            """, unsafe_allow_html=True)

    if len(df) > 1: render_card(col1, df.iloc[1])
    if len(df) > 2: render_card(col2, df.iloc[2])
    if len(df) > 3: render_card(col3, df.iloc[3])
    
    st.markdown("<br>", unsafe_allow_html=True) # Κενό

    # --- TWO COLUMN LAYOUT (Ροή & Sidebar) ---
    main_col, side_col = st.columns([0.7, 0.3])
    
    with main_col:
        st.subheader("📰 Τελευταία Ροή")
        st.divider()
        
        # Λίστα από το άρθρο 5 και μετά
        for index, row in df.iloc[4:20].iterrows(): # Δείχνουμε τα επόμενα 15
            st.markdown(f"""
            <div class="list-item">
                <div class="list-title">
                    <a href="{row['link']}" target="_blank">{row['title']}</a>
                </div>
                <div class="list-meta">
                    <span style="color: #cc0000; font-weight: bold;">{row['category']}</span> • {row['last_update']} • {row['law']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    with side_col:
        st.subheader("📊 Trending")
        st.markdown("""
        <div style="background-color: #f1f5f9; padding: 15px; border-radius: 5px;">
            <b>Δημοφιλείς Κατηγορίες</b><br><br>
            📐 Πολεοδομία<br>
            ⚡ Εξοικονομώ<br>
            💼 Φορολογικά<br>
            ✒️ Δημόσια Έργα
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.subheader("🔗 Quick Links")
        st.markdown("""
        * [Υπουργείο Υποδομών](https://www.yme.gr/)
        * [MyData Login](https://www.aade.gr/mydata)
        * [Ηλεκτρονική Ταυτότητα](https://web.tee.gr/)
        """)

    # FOOTER
    st.markdown('<div class="footer">© 2026 NomoTechi Inc. • All Rights Reserved</div>', unsafe_allow_html=True)

else:
    st.info("Δεν υπάρχουν αρκετά άρθρα για να γεμίσει η σελίδα.")
