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

# --- 2. CSS (PROFESSIONAL & RESPONSIVE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
        background-color: #F8F9FA;
        color: #212529;
    }
    
    /* HEADER */
    .header-container {
        background: white;
        padding: 25px 0;
        border-bottom: 4px solid #003366;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .header-logo { font-size: 3.5rem; font-weight: 800; color: #003366; letter-spacing: -1px; line-height: 1; }
    .header-sub { color: #666; font-size: 1rem; text-transform: uppercase; letter-spacing: 2px; margin-top: 5px; font-weight: 600;}

    /* TICKER */
    .ticker-wrap {
        width: 100%; background-color: #003366; color: white; height: 42px;
        overflow: hidden; white-space: nowrap; display: flex; align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 25px;
    }
    .ticker-item {
        display: inline-block; padding-left: 100%;
        animation: ticker 75s linear infinite; font-weight: 600; font-size: 0.95rem;
    }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    /* SEARCH */
    .search-container { max-width: 700px; margin: 0 auto 30px auto; padding: 0 20px; }
    .stTextInput input { border-radius: 30px; border: 1px solid #ccc; padding: 12px 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .stTextInput input:focus { border-color: #003366; box-shadow: 0 0 8px rgba(0,51,102,0.15); }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] { background-color: white; padding: 15px; border-radius: 12px; gap: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
    .stTabs [data-baseweb="tab"] { height: 50px; color: #444 !important; font-weight: 700 !important; font-size: 1.05rem !important; border-radius: 5px; }
    .stTabs [aria-selected="true"] { color: #cc0000 !important; background-color: #FFF5F5 !important; border-bottom: 3px solid #cc0000 !important; }

    /* HERO */
    .hero-wrapper {
        position: relative; height: 480px; border-radius: 12px; overflow: hidden;
        box-shadow: 0 10px 20px rgba(0,0,0,0.15); background: #000; margin-bottom: 20px;
    }
    .hero-image { width: 100%; height: 100%; object-fit: cover; opacity: 0.85; transition: transform 6s ease; }
    .hero-image:hover { transform: scale(1.05); opacity: 0.95; }
    .hero-overlay {
        position: absolute; bottom: 0; left: 0; width: 100%; padding: 40px;
        background: linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 50%, transparent 100%);
    }
    .hero-cat { display: inline-block; background-color: #cc0000; color: white; padding: 5px 12px; font-size: 0.75rem; font-weight: 800; border-radius: 4px; margin-bottom: 12px; text-transform: uppercase;}
    .hero-title { color: white; font-size: 2.2rem; font-weight: 800; line-height: 1.15; text-shadow: 0 2px 4px rgba(0,0,0,0.5); margin-bottom: 10px; }
    .hero-title a { color: white !important; text-decoration: none; }
    .hero-meta { color: #ddd; font-size: 0.9rem; }

    /* LIST ITEMS */
    .list-item {
        background: white; padding: 20px; border-bottom: 1px solid #f0f0f0;
        border-left: 4px solid transparent; transition: all 0.2s;
    }
    .list-item:hover { background-color: #f8fafc; border-left: 4px solid #003366; transform: translateX(5px); }
    .list-title { font-size: 1.1rem; font-weight: 700; color: #1a1a1a; margin-bottom: 6px; line-height: 1.35; }
    .list-title a { color: #1a1a1a !important; text-decoration: none; }
    .list-title a:hover { color: #004B87 !important; }
    .list-summary { font-size: 0.9rem; color: #555; margin-bottom: 10px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .list-meta { font-size: 0.8rem; color: #888; display: flex; justify-content: space-between; align-items: center; }
    
    /* SHARE BUTTONS */
    .share-btn {
        text-decoration: none; font-size: 0.75rem; font-weight: 700; 
        padding: 4px 8px; border-radius: 4px; display: inline-block; margin-left: 5px;
    }
    .share-li { color: #0077b5; background: #eef6fa; } 
    .share-fb { color: #1877f2; background: #eef4fc; }
    .share-btn:hover { opacity: 0.8; }

    /* GRID CARDS */
    .grid-card {
        background: white; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; height: 100%;
        display: flex; flex-direction: column; transition: transform 0.2s, box-shadow 0.2s;
    }
    .grid-card:hover { transform: translateY(-5px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
    .grid-img { height: 180px; overflow: hidden; background: #f3f4f6; position: relative; }
    .grid-img img { width: 100%; height: 100%; object-fit: cover; }
    .grid-cat-badge {
        position: absolute; bottom: 10px; left: 10px; background: rgba(0,0,0,0.7); color: white;
        padding: 3px 8px; font-size: 0.7rem; font-weight: bold; border-radius: 3px;
    }
    .grid-content { padding: 18px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
    .grid-title { font-size: 1.1rem; font-weight: 700; color: #111; margin-bottom: 8px; line-height: 1.3; }
    .grid-text { font-size: 0.9rem; color: #555; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 15px; }
    .grid-footer { border-top: 1px solid #f0f0f0; padding-top: 10px; font-size: 0.8rem; color: #888; display: flex; justify-content: space-between; }

    /* FOOTER */
    .footer {
        margin-top: 50px; padding: 40px 0; background: #0F172A; color: white; text-align: center; border-radius: 10px 10px 0 0;
    }
    .footer a { color: #94A3B8; text-decoration: none; margin: 0 10px; }
    .footer a:hover { color: white; }
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

# --- 4. SIDEBAR WIDGETS ---
with st.sidebar:
    st.markdown("### ☁️ Καιρός")
    components.iframe("https://www.meteoblue.com/en/weather/widget/three/athens_greece_264371?geoloc=fixed&nocurrent=0&noforecast=0&days=4&tempunit=CELSIUS&windunit=KILOMETER_PER_HOUR&layout=image", height=240)
    
    st.markdown("---")
    st.markdown("### 📬 Ενημέρωση")
    st.caption("Λάβετε τα σημαντικότερα ΦΕΚ στο email σας.")
    email = st.text_input("Το Email σας", placeholder="name@company.com")
    if st.button("Εγγραφή", type="primary"):
        if email:
            st.success("✅ Εγγραφήκατε!")
            time.sleep(2)
    st.markdown("---")
    st.info("💡 **Tip:** Το NomoTechi χρησιμοποιεί AI για να κατηγοριοποιεί αυτόματα τη νομοθεσία.")

# --- 5. MAIN UI ---
st.markdown("""<div class="header-container"><div class="header-logo">🏛️ NomoTechi</div><div class="header-sub">Intelligence Platform for Engineers & Lawyers</div></div>""", unsafe_allow_html=True)

data = load_data()
df = pd.DataFrame(data)

# Search
st.markdown('<div class="search-container">', unsafe_allow_html=True)
search_query = st.text_input("", placeholder="🔍 Αναζήτηση σε τίτλους, κείμενα & ΦΕΚ...")
st.markdown('</div>', unsafe_allow_html=True)

if not df.empty and search_query:
    df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]

# Ticker
if not df.empty:
    latest_titles = "   +++   ".join([f"{row['title']} ({row['law']})" for idx, row in df.head(10).iterrows()])
    st.markdown(f"""<div class="ticker-wrap"><div class="ticker-item">{latest_titles}</div></div>""", unsafe_allow_html=True)

# --- 6. ΚΑΤΗΓΟΡΙΕΣ (NEW LOGIC - CORRECTED TABS) ---
tabs = st.tabs(["🏠 ΡΟΗ ΕΙΔΗΣΕΩΝ", "🏗️ ΜΗΧΑΝΙΚΟΣ & ΑΚΙΝΗΤΑ", "⚖️ ΝΟΜΙΚΑ & ΔΙΚΑΙΟΣΥΝΗ", "📜 ΦΕΚ/ΝΟΜΟΘΕΣΙΑ", "⚙️ ADMIN"])

if not df.empty:
    df = df.iloc[::-1].reset_index(drop=True)
    if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0

    def get_filtered_df(tab_name):
        if tab_name == "HOME": 
            return df
        if tab_name == "ENG": 
            # Ψάχνει ετικέτες ENGINEERS, Μηχανικοί, Έργα, Ακίνητα
            return df[df['category'].str.contains("ENGINEERS|Μηχανικ|ENG|Ακίνητα", case=False, na=False)]
        if tab_name == "LAW": 
            # Ψάχνει LEGAL, Νομικά, Δικαιοσύνη
            return df[df['category'].str.contains("LEGAL|Νομικ|LAW", case=False, na=False)]
        if tab_name == "FEK": 
            # Ψάχνει LEGISLATION, ΦΕΚ
            return df[df['category'].str.contains("LEGISLATION|Νομοθεσία|FEK", case=False, na=False)]
        return df

    def get_display_image(row):
        if 'image_url' in row and str(row['image_url']).startswith('http'):
            return row['image_url']
        return get_stock_image(row['category'], row['title'])

    def render_tab_content(tab_code):
        current_df = get_filtered_df(tab_code).reset_index(drop=True)
        if current_df.empty:
            st.info("Δεν βρέθηκαν αποτελέσματα για αυτή την κατηγορία.")
            return

        # HERO (Only on Home or when not searching)
        if not search_query:
            col_hero, col_list = st.columns([1.8, 1.2])
            
            with col_hero:
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
                        <div class="hero-meta">{hero_article['law']} • {hero_article['last_update']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([0.1, 0.8, 0.1])
                with c1:
                    if st.button("❮", key=f"p_{tab_code}"): st.session_state.slider_idx -= 1; st.rerun()
                with c3:
                    if st.button("❯", key=f"n_{tab_code}"): st.session_state.slider_idx += 1; st.rerun()

            with col_list:
                st.markdown("### ⚡ Top Stories")
                for idx, row in current_df.head(6).iterrows():
                    share_link = row['link']
                    st.markdown(f"""
                    <div class="list-item">
                        <div class="list-title"><a href="{row['link']}" target="_blank">{row['title']}</a></div>
                        <div class="list-summary">{row['content'][:120]}...</div>
                        <div class="list-meta">
                            <span>{row['last_update']}</span>
                            <div>
                                <a href="https://www.linkedin.com/sharing/share-offsite/?url={share_link}" target="_blank" class="share-btn share-li">in</a>
                                <a href="https://www.facebook.com/sharer/sharer.php?u={share_link}" target="_blank" class="share-btn share-fb">fb</a>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("---")

        # GRID
        st.subheader("📌 Τελευταία Νέα & Αποφάσεις")
        start_idx = 6 if not search_query else 0
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
                        with col:
                            st.markdown(f"""
                            <div class="grid-card">
                                <div class="grid-img">
                                    <img src="{card_img}" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200';">
                                    <div class="grid-cat-badge">{row['category'].split(',')[0]}</div>
                                </div>
                                <div class="grid-content">
                                    <div>
                                        <div class="grid-title">{row['title']}</div>
                                        <div class="grid-text">{row['content']}</div>
                                    </div>
                                    <div class="grid-footer">
                                        <span>{row['last_update']}</span>
                                        <a href="{row['link']}" target="_blank" style="color:#003366; font-weight:bold; text-decoration:none;">Διαβάστε &rarr;</a>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

    with tabs[0]: render_tab_content("HOME")
    with tabs[1]: render_tab_content("ENG")
    with tabs[2]: render_tab_content("LAW")
    with tabs[3]: render_tab_content("FEK")
    
    with tabs[4]: # ADMIN
        st.header("🔒 Διαχείριση Συστήματος")
        pw = st.text_input("Κωδικός", type="password")
        if pw == st.secrets.get("admin_password", ""):
            st.success("Authenticated")
            c1, c2 = st.columns(2)
            with c1: st.button("🚀 Bot Status: ACTIVE (GitHub AI)", disabled=True)
            with c2:
                if st.button("🧹 Clear Cache (Refresh)"): st.cache_data.clear(); st.rerun()
                if st.button("🔴 RESET DATABASE (Emergency Only)"): reset_database(); st.cache_data.clear(); st.rerun()
            st.dataframe(df)

    # FOOTER
    st.markdown("""
    <div class="footer">
        <p>© 2024 NomoTechi. Powered by Gemini AI.</p>
        <p>
            <a href="#">Όροι Χρήσης</a> | 
            <a href="#">Πολιτική Απορρήτου</a>
        </p>
    </div>
    """, unsafe_allow_html=True)

else:
    st.warning("Η βάση ενημερώνεται... Παρακαλώ περιμένετε 1 λεπτό και κάντε ανανέωση.")

