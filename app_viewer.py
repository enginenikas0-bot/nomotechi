import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime
import time
import hashlib
import re
import streamlit.components.v1 as components

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTechi | Intelligence Platform",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS (SLIDER, MENU LABEL & STYLING) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Segoe+UI:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
        background-color: #f4f4f4;
        color: #111;
    }

    /* --- SIDEBAR LABEL (Η ΤΑΜΠΕΛΑ ΠΟΥ ΖΗΤΗΣΕΣ) --- */
    .sidebar-hint {
        position: fixed;
        top: 18px;
        left: 60px;
        z-index: 99999;
        font-weight: 800;
        font-size: 0.9rem;
        color: #cc0000;
        background: rgba(255, 255, 255, 0.9);
        padding: 5px 10px;
        border-radius: 4px;
        border: 1px solid #cc0000;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        pointer-events: none; /* Να μην εμποδίζει το κλικ */
    }

    /* BADGES */
    .badge-sos {
        background-color: #dc3545; color: white; padding: 2px 6px; border-radius: 4px;
        font-size: 0.7rem; font-weight: bold; margin-right: 5px; vertical-align: middle;
    }
    .badge-law {
        background-color: #003366; color: white; padding: 2px 6px; border-radius: 4px;
        font-size: 0.7rem; font-weight: bold; margin-right: 5px; vertical-align: middle;
    }

    /* HEADER */
    .header-container {
        background: white; padding: 20px 0; border-bottom: 5px solid #003366; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; margin-top: 20px;
    }
    .header-logo { font-family: 'Merriweather', serif; font-size: 3.5rem; font-weight: 900; color: #003366; letter-spacing: -1px; }
    .header-sub { color: #555; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; margin-top:5px;}

    /* TICKER */
    .ticker-wrap {
        width: 100%; background-color: #003366; color: white; height: 40px;
        overflow: hidden; white-space: nowrap; display: flex; align-items: center; margin-bottom: 20px;
    }
    .ticker-item {
        display: inline-block; padding-left: 100%;
        animation: ticker 40s linear infinite; font-weight: 600; font-size: 0.9rem;
    }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    /* LISTS & CARDS */
    .list-item {
        background: white; padding: 20px; border-bottom: 1px solid #ddd; border-left: 4px solid transparent;
        transition: 0.2s; margin-bottom: 5px;
    }
    .list-item:hover { border-left: 4px solid #cc0000; background-color: #fffdfd; }
    .list-title { font-family: 'Merriweather', serif; font-size: 1.15rem; font-weight: 700; color: #111; margin-bottom: 5px; line-height: 1.4; }
    .list-title a { color: #111 !important; text-decoration: none; }
    .list-title a:hover { color: #cc0000 !important; }
    
    .grid-card {
        background: white; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; height: 100%;
        display: flex; flex-direction: column; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: transform 0.2s;
    }
    .grid-card:hover { transform: translateY(-3px); box-shadow: 0 8px 16px rgba(0,0,0,0.1); }
    .grid-img { height: 170px; overflow: hidden; background: #eee; position: relative; }
    .grid-img img { width: 100%; height: 100%; object-fit: cover; }
    .grid-content { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
    .grid-title { font-family: 'Merriweather', serif; font-size: 1.05rem; font-weight: 700; color: #000; margin-bottom: 8px; line-height: 1.35; }

    /* HERO SLIDER */
    .hero-wrapper { position: relative; height: 450px; overflow: hidden; margin-bottom: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); border-radius: 8px; }
    .hero-image { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.7); transition: transform 6s ease; }
    .hero-image:hover { transform: scale(1.05); filter: brightness(0.8); }
    .hero-overlay { position: absolute; bottom: 0; left: 0; width: 100%; padding: 30px; background: linear-gradient(to top, rgba(0,0,0,0.9), transparent); }
    .hero-title { font-family: 'Merriweather', serif; color: white; font-size: 2.2rem; font-weight: 700; line-height: 1.2; text-shadow: 0 2px 5px black; }
    .hero-title a { color: white !important; text-decoration: none; }
    
    /* SLIDER BUTTONS */
    .slider-btn { 
        background-color: rgba(255,255,255,0.2); color: white; border: 1px solid white; 
        font-size: 1.5rem; cursor: pointer; border-radius: 50%; width: 40px; height: 40px;
        display: flex; justify-content: center; align-items: center; transition: 0.3s;
    }
    .slider-btn:hover { background-color: white; color: black; }

    /* SEARCH & TABS */
    .stTextInput input { border-radius: 0px; border: 1px solid #999; padding: 10px; }
    .stTabs [data-baseweb="tab-list"] { background-color: white; padding: 10px; border-bottom: 2px solid #ddd; gap: 20px; }
    .stTabs [data-baseweb="tab"] { font-weight: 700 !important; font-size: 1rem !important; color: #444 !important; }
    .stTabs [aria-selected="true"] { color: #003366 !important; border-bottom: 3px solid #003366 !important; background: transparent !important;}
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

def get_stock_image(category, title):
    if "ENGINEERS" in category or "Μηχανικ" in category: pool = IMAGE_POOL["ENG"]
    elif "LEGAL" in category or "Νομικ" in category: pool = IMAGE_POOL["LAW"]
    elif "LEGISLATION" in category or "ΦΕΚ" in category: pool = IMAGE_POOL["FEK"]
    elif "Ενέργεια" in category: pool = IMAGE_POOL["ENERGY"]
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

# --- 4. SIDEBAR ---
# Εδώ είναι η ετικέτα που θα εμφανιστεί δίπλα στο βελάκι
st.markdown('<div class="sidebar-hint">⬅️ MENOY & ΕΡΓΑΛΕΙΑ</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⏳ Προθεσμίες (Timeline)")
    st.info("⚠️ **31/12:** Λήξη Κτηματολογίου (Δήλωση)")
    st.info("⚠️ **31/01:** MyDATA Διαβίβαση")
    st.markdown("---")
    st.markdown("### ☁️ Καιρός")
    components.iframe("https://www.meteoblue.com/en/weather/widget/three/athens_greece_264371?geoloc=fixed&nocurrent=0&noforecast=0&days=4&tempunit=CELSIUS&windunit=KILOMETER_PER_HOUR&layout=image", height=240)

# --- 5. MAIN UI ---
st.markdown("""<div class="header-container"><div class="header-logo">🏛️ NomoTechi</div><div class="header-sub">Intelligence Platform for Professionals</div></div>""", unsafe_allow_html=True)

data = load_data()
df = pd.DataFrame(data)

# Search
st.markdown('<div class="search-container">', unsafe_allow_html=True)
search_query = st.text_input("", placeholder="🔍 Αναζήτηση (π.χ. 'Αυθαίρετα', 'Άρειος Πάγος')...")
st.markdown('</div>', unsafe_allow_html=True)

if not df.empty and search_query:
    df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

# Ticker
if not df.empty:
    latest_titles = "   +++   ".join([f"{row['title']}" for idx, row in df.head(10).iterrows()])
    st.markdown(f"""<div class="ticker-wrap"><div class="ticker-item">{latest_titles}</div></div>""", unsafe_allow_html=True)

# --- 6. ΚΑΤΗΓΟΡΙΕΣ & SLIDER RESTORED ---
tabs = st.tabs(["🏠 ΚΟΡΥΦΑΙΑ", "🏗️ ΜΗΧΑΝΙΚΟΙ & ΑΚΙΝΗΤΑ", "⚖️ ΝΟΜΙΚΑ & ΔΙΚΑΙΟΣΥΝΗ", "📜 ΝΟΜΟΘΕΣΙΑ/ΦΕΚ", "⚙️ ADMIN"])

if not df.empty:
    df = df.iloc[::-1].reset_index(drop=True)
    if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0

    def get_filtered_df(tab_name):
        if tab_name == "HOME": return df 
        if tab_name == "ENG": return df[df['category'].str.contains("ENGINEERS|REAL_ESTATE|Μηχανικ|Ακίνητα", case=False, na=False)]
        if tab_name == "LAW": return df[df['category'].str.contains("LEGAL|JUDICIAL|Νομικ|Δικαιοσύνη", case=False, na=False)]
        if tab_name == "FEK": return df[df['category'].str.contains("LEGISLATION|Νομοθεσία|ΦΕΚ", case=False, na=False)]
        return df

    def render_badges(category_str):
        badges_html = ""
        if "SOS" in category_str: badges_html += '<span class="badge-sos">🚨 SOS</span>'
        if "JUDICIAL" in category_str or "LEGAL" in category_str: badges_html += '<span class="badge-law">⚖️ ΝΟΜΟΛΟΓΙΑ</span>'
        if "REAL_ESTATE" in category_str: badges_html += '<span style="background:#28a745;color:white;padding:2px 6px;border-radius:4px;font-size:0.7rem;font-weight:bold;margin-right:5px;">🏠 REAL ESTATE</span>'
        return badges_html

    def get_display_image(row):
        if 'image_url' in row and str(row['image_url']).startswith('http'):
            return row['image_url']
        return get_stock_image(row['category'], row['title'])

    def render_tab_content(tab_code):
        current_df = get_filtered_df(tab_code).reset_index(drop=True)
        if current_df.empty:
            st.info("Δεν βρέθηκαν αποτελέσματα.")
            return

        # --- SLIDER (ΕΔΩ ΕΙΝΑΙ ΠΑΛΙ!) ---
        # Εμφανίζεται μόνο στην Αρχική και αν δεν ψάχνουμε
        if not search_query and tab_code == "HOME":
            col_hero, col_list = st.columns([1.8, 1.2])
            with col_hero:
                slider_len = min(5, len(current_df))
                current_slide = st.session_state.slider_idx % slider_len
                hero_article = current_df.iloc[current_slide]
                hero_img = get_display_image(hero_article)
                hero_badges = render_badges(hero_article['category'])
                
                st.markdown(f"""
                <div class="hero-wrapper">
                    <img src="{hero_img}" class="hero-image" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200';">
                    <div class="hero-overlay">
                        <div>{hero_badges}</div>
                        <div class="hero-title"><a href="{hero_article['link']}" target="_blank">{hero_article['title']}</a></div>
                        <div style="color:#ddd; margin-top:5px;">{hero_article['last_update']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # ΚΟΥΜΠΙΑ SLIDER (❮ ❯)
                c1, c2, c3 = st.columns([0.1, 0.8, 0.1])
                with c1: 
                    if st.button("❮", key="prev"): st.session_state.slider_idx -= 1; st.rerun()
                with c3: 
                    if st.button("❯", key="next"): st.session_state.slider_idx += 1; st.rerun()

            with col_list:
                st.markdown("### ⚡ Τελευταία Ροή")
                for idx, row in current_df.head(6).iterrows():
                    badges = render_badges(row['category'])
                    st.markdown(f"""
                    <div class="list-item">
                        <div>{badges}</div>
                        <div class="list-title"><a href="{row['link']}" target="_blank">{row['title']}</a></div>
                        <div style="font-size:0.85rem; color:#666;">{row['last_update']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("---")

        # GRID FOR ALL TABS
        st.subheader("📌 Ειδήσεις & Αποφάσεις")
        start_idx = 6 if (not search_query and tab_code=="HOME") else 0
        grid_df = current_df.iloc[start_idx:]
        
        if not grid_df.empty:
            rows = len(grid_df) // 3 + 1
            for i in range(rows):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    idx = i * 3 + j
                    if idx < len(grid_df):
                        row = grid_df.iloc[idx]
                        card_img = get_display_image(row)
                        badges = render_badges(row['category'])
                        with col:
                            st.markdown(f"""
                            <div class="grid-card">
                                <div class="grid-img"><img src="{card_img}" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200';"></div>
                                <div class="grid-content">
                                    <div>
                                        <div>{badges}</div>
                                        <div class="grid-title">{row['title']}</div>
                                        <div style="font-size:0.9rem; color:#555; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">{row['content']}</div>
                                    </div>
                                    <div style="margin-top:10px; padding-top:10px; border-top:1px solid #eee;">
                                        <a href="{row['link']}" target="_blank" style="color:#cc0000; font-weight:bold; text-decoration:none;">Διαβάστε Περισσότερα &rarr;</a>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

    with tabs[0]: render_tab_content("HOME")
    with tabs[1]: render_tab_content("ENG")
    with tabs[2]: render_tab_content("LAW")
    with tabs[3]: render_tab_content("FEK")
    
    with tabs[4]: 
        st.header("Admin")
        if st.secrets.get("admin_password") and st.text_input("Pass", type="password") == st.secrets["admin_password"]:
            if st.button("🧹 Clear Cache"): st.cache_data.clear(); st.rerun()
            if st.button("🔴 RESET DATABASE"): reset_database(); st.cache_data.clear(); st.rerun()
            st.dataframe(df)

else:
    st.warning("Φόρτωση δεδομένων... Παρακαλώ περιμένετε.")
