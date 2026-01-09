import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime
import time
import hashlib
import re

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTechi | Professional Hub",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    html, body, [class*="css"] {font-family: 'Segoe UI', sans-serif; background-color: #F8F9FA; color: #212529;}
    .header-container {background-color: white; padding: 20px 0; border-bottom: 5px solid #003366; text-align: center;}
    .header-logo {font-size: 3rem; font-weight: 900; color: #003366; line-height: 1;}
    .header-sub {color: #6c757d; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 5px;}
    .ticker-wrap {width: 100%; background-color: #003366; color: white; height: 45px; overflow: hidden; white-space: nowrap; display: flex; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;}
    .ticker-item {display: inline-block; padding-left: 100%; animation: ticker 60s linear infinite; font-weight: 600; font-size: 1rem;}
    @keyframes ticker {0% {transform: translate3d(0, 0, 0);} 100% {transform: translate3d(-100%, 0, 0);}}
    .stTabs [data-baseweb="tab-list"] {background-color: white; padding: 10px; border-radius: 8px; gap: 15px;}
    .stTabs [data-baseweb="tab"] {height: 55px; color: #333 !important; font-weight: 600 !important; font-size: 1rem !important;}
    .stTabs [aria-selected="true"] {color: #cc0000 !important; border-bottom: 3px solid #cc0000 !important; background-color: #FFF0F0 !important;}
    .hero-wrapper {position: relative; height: 450px; border-radius: 8px; overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.1); background: #000;}
    .hero-image {width: 100%; height: 100%; object-fit: cover; opacity: 0.8; transition: transform 5s ease;}
    .hero-image:hover {transform: scale(1.05); opacity: 0.9;}
    .hero-overlay {position: absolute; bottom: 0; left: 0; width: 100%; padding: 40px; background: linear-gradient(to top, rgba(0,0,0,0.95), rgba(0,0,0,0.5), transparent);}
    .hero-cat {display: inline-block; background-color: #cc0000; color: white; padding: 4px 10px; font-size: 0.75rem; font-weight: 700; border-radius: 3px; margin-bottom: 10px;}
    .hero-title {color: white; font-size: 2rem; font-weight: 700; line-height: 1.2; text-shadow: 0 2px 4px rgba(0,0,0,0.5);}
    .hero-title a {color: white !important; text-decoration: none;}
    .list-item {background: white; padding: 18px; border-bottom: 1px solid #eee; transition: 0.2s; border-left: 3px solid transparent;}
    .list-item:hover {background-color: #f1f5f9; border-left: 3px solid #003366;}
    .list-title {font-size: 1.05rem; font-weight: 600; color: #1a1a1a; margin-bottom: 4px;}
    .list-title a {color: #1a1a1a !important; text-decoration: none;}
    .list-title a:hover {color: #004B87 !important;}
    .list-summary {font-size: 0.9rem; color: #555; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;}
    .list-meta {font-size: 0.8rem; color: #888;}
    .grid-card {background: white; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; height: 100%; display: flex; flex-direction: column;}
    .grid-img {height: 160px; overflow: hidden; background: #eee;}
    .grid-img img {width: 100%; height: 100%; object-fit: cover; transition: 0.3s;}
    .grid-card:hover .grid-img img {transform: scale(1.05);}
    .grid-content {padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between;}
    .grid-title {font-size: 1.1rem; font-weight: 700; color: #222; margin-bottom: 8px; line-height: 1.3;}
    .grid-text {font-size: 0.9rem; color: #555; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 10px;}
    .search-container {max-width: 600px; margin: 20px auto; padding: 0 20px;}
    .stTextInput input {border-radius: 20px; border: 2px solid #ddd; padding: 10px 15px;}
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC ---
IMAGE_POOL = {
    "ENG": ["https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=1200","https://images.unsplash.com/photo-1503387762-592deb58ef4e?q=80&w=1200"],
    "ENERGY": ["https://images.unsplash.com/photo-1509391366360-2e959784a276?q=80&w=1200","https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?q=80&w=1200"],
    "LAW": ["https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=1200","https://images.unsplash.com/photo-1505664194779-8beaceb93744?q=80&w=1200"],
    "FEK": ["https://images.unsplash.com/photo-1618044733300-9472054094ee?q=80&w=1200","https://images.unsplash.com/photo-1555848962-6e79363ec58f?q=80&w=1200"],
    "GENERAL": ["https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200"]
}

def remove_accents(input_str):
    replacements = {'ά':'α','έ':'ε','ή':'η','ί':'ι','ό':'ο','ύ':'υ','ώ':'ω','Ά':'Α','Έ':'Ε','Ή':'Η','Ί':'Ι','Ό':'Ο','Ύ':'Υ','Ώ':'Ω','ϊ':'ι','ϋ':'υ'}
    for char, rep in replacements.items(): input_str = input_str.replace(char, rep)
    return input_str.lower()

def get_stock_image(category, title):
    if "Πολεοδομία" in category or "Έργα" in category: pool = IMAGE_POOL["ENG"]
    elif "Ενέργεια" in category or "Περιβάλλον" in category: pool = IMAGE_POOL["ENERGY"]
    elif "Νομικά" in category or "Συμβολαιο" in category: pool = IMAGE_POOL["LAW"]
    elif "Νομοθεσία" in category or "ΦΕΚ" in category: pool = IMAGE_POOL["FEK"]
    else: pool = IMAGE_POOL["GENERAL"]
    hash_obj = hashlib.md5(title.encode())
    index = int(hash_obj.hexdigest(), 16) % len(pool)
    return pool[index]

def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        return gc.open("laws_database").sheet1
    except: return None

def load_data():
    sheet = get_db_connection()
    return sheet.get_all_records() if sheet else []

def reset_database():
    sheet = get_db_connection()
    if not sheet: return False
    try:
        sheet.batch_clear(["A2:H5000"])
        return True
    except: return False

# --- 4. RENDER UI ---
st.markdown("""<div class="header-container"><div class="header-logo">🏛️ NomoTechi</div><div class="header-sub">Η Ενιαία Πύλη για Μηχανικούς, Δικηγόρους & Συμβολαιογράφους</div></div>""", unsafe_allow_html=True)

data = load_data()
df = pd.DataFrame(data)

st.markdown('<div class="search-container">', unsafe_allow_html=True)
search_query = st.text_input("", placeholder="🔍 Αναζήτηση ειδήσεων, ΦΕΚ, αποφάσεων...")
st.markdown('</div>', unsafe_allow_html=True)

if not df.empty and search_query:
    df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

if not df.empty:
    latest_titles = "   +++   ".join([f"{row['title']} ({row['law']})" for idx, row in df.head(10).iterrows()])
    st.markdown(f"""<div class="ticker-wrap"><div class="ticker-item">{latest_titles}</div></div><br>""", unsafe_allow_html=True)

tabs = st.tabs(["🏠 ΡΟΗ ΕΙΔΗΣΕΩΝ", "📐 ΜΗΧΑΝΙΚΟΙ & ΕΡΓΑ", "⚖️ ΝΟΜΙΚΑ & ΑΚΙΝΗΤΑ", "📜 ΦΕΚ & ΝΟΜΟΘΕΣΙΑ", "⚙️ ADMIN"])

if not df.empty:
    df = df.iloc[::-1].reset_index(drop=True)
    if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0

    def get_filtered_df(tab_name):
        if tab_name == "HOME": return df
        if tab_name == "ENG": return df[df['category'].str.contains("Μηχανικ|Πολεοδομ|Ενέργεια|Έργα|Θεσμικά", case=False)]
        if tab_name == "LAW": return df[df['category'].str.contains("Νομικ|Συμβολαιο|Δικηγόρ|Φορολογ", case=False)]
        if tab_name == "FEK": return df[df['category'].str.contains("Νομοθεσία|ΦΕΚ", case=False)]
        return df

    def get_display_image(row):
        if 'image_url' in row and str(row['image_url']).startswith('http'):
            return row['image_url']
        return get_stock_image(row['category'], row['title'])

    def render_tab_content(tab_code):
        current_df = get_filtered_df(tab_code).reset_index(drop=True)
        if current_df.empty:
            st.info("Δεν βρέθηκαν αποτελέσματα.")
            return

        if not search_query: 
            col_hero_wrap, col_list = st.columns([1.8, 1.2]) 
            
            with col_hero_wrap:
                slider_len = min(5, len(current_df))
                current_slide = st.session_state.slider_idx % slider_len
                hero_article = current_df.iloc[current_slide]
                hero_img = get_display_image(hero_article)
                
                st.markdown(f"""
                <div class="hero-wrapper">
                    <img src="{hero_img}" class="hero-image" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200';">
                    <div class="hero-overlay">
                        <div class="hero-cat">{hero_article['category']}</div>
                        <div class="hero-title">
                            <a href="{hero_article['link']}" target="_blank">{hero_article['title']}</a>
                        </div>
                        <div style="color:white; margin-top:5px; font-size:0.9rem;">{hero_article['law']} • {hero_article['last_update']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c_left, c_mid, c_right = st.columns([0.1, 0.8, 0.1])
                with c_left:
                    if st.button("❮", key=f"prev_{tab_code}"): st.session_state.slider_idx -= 1; st.rerun()
                with c_right:
                    if st.button("❯", key=f"next_{tab_code}"): st.session_state.slider_idx += 1; st.rerun()

            with col_list:
                st.markdown(f"### 📰 Top Stories")
                for idx, row in current_df.head(6).iterrows():
                    st.markdown(f"""
                    <div class="list-item">
                        <div class="list-title"><a href="{row['link']}" target="_blank">{row['title']}</a></div>
                        <div class="list-summary">{row['content'][:150]}...</div>
                        <div class="list-meta">
                            <span style="color:#cc0000; font-weight:bold;">{row['category'].split(':')[0]}</span> • {row['last_update']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("---")

        start_idx = 6 if not search_query else 0
        grid_df = current_df.iloc[start_idx:] 
        
        if not grid_df.empty:
            rows = len(grid_df) // 3 + 1
            for i in range(rows):
                c1, c2, c3 = st.columns(3)
                for j, col in enumerate([c1, c2, c3]):
                    idx = i * 3 + j
                    if idx < len(grid_df):
                        row = grid_df.iloc[idx]
                        card_img = get_display_image(row)
                        with col:
                            st.markdown(f"""
                            <div class="grid-card">
                                <div class="grid-img"><img src="{card_img}" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200';"></div>
                                <div class="grid-content">
                                    <div class="grid-cat">{row['category'].split(':')[0]}</div>
                                    <div class="grid-title">{row['title']}</div>
                                    <div class="grid-text">{row['content']}</div>
                                    <div style="margin-top:10px; font-size:0.75rem; color:#888;">
                                        {row['law']} | <a href="{row['link']}" target="_blank" style="color:#003366; font-weight:bold;">Διαβάστε</a>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

    with tabs[0]: render_tab_content("HOME")
    with tabs[1]: render_tab_content("ENG")
    with tabs[2]: render_tab_content("LAW")
    with tabs[3]: render_tab_content("FEK")
    
    with tabs[4]:
        st.header("Διαχείριση")
        pw = st.text_input("Κωδικός Διαχειριστή", type="password")
        if pw == st.secrets.get("admin_password", ""):
            st.success("Admin Access: OK")
            st.info("Για ενεργοποίηση, τρέξτε το Workflow από το GitHub.")
            c1, c2 = st.columns(2)
            with c1:
                st.button("🚀 Force Scan (GitHub Action)", disabled=True)
            with c2:
                if st.button("🧹 Clear Cache"): st.cache_data.clear(); st.rerun()
                if st.button("🔴 RESET DATABASE"): reset_database(); st.cache_data.clear(); st.rerun()
            st.dataframe(df)

else:
    st.warning("Η βάση είναι κενή. Τρέξτε το GitHub Workflow.")
