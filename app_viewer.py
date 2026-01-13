import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime
import time
import hashlib
import re
import base64
import streamlit.components.v1 as components

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTechi | Intelligence Platform",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS (THE FINAL COMPLETE THEME) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Segoe+UI:wght@300;400;600&display=swap');
    
    /* GLOBAL RESET */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; background-color: #ffffff; color: #222; }
    
    /* SEARCH BAR */
    div[data-baseweb="input"] { background-color: #003366 !important; border: 1px solid #004080 !important; border-radius: 4px; }
    div[data-baseweb="input"] input { color: white !important; caret-color: white; font-weight: 500; }
    div[data-baseweb="input"] input::placeholder { color: #b3cce6 !important; }

    /* SIDEBAR */
    [data-testid="collapsedControl"], [data-testid="stSidebar"] button { color: #000 !important; }

    /* BRANDING & HEADER */
    .brand-card { background: #ffffff; border: 1px solid #f0f0f0; border-radius: 4px; padding: 20px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .brand-btn { display: block; width: 100%; background: #111; color: #fff !important; padding: 10px; text-decoration: none; font-weight: 600; font-size: 0.8rem; border-radius: 2px; transition: 0.3s; }
    .brand-btn:hover { background: #444; }

    .header-container { background: white; padding: 0 0 20px 0; border-bottom: 2px solid #003366; text-align: center; margin-bottom: 20px; }
    .header-logo { font-family: 'Merriweather', serif; font-size: 3rem; font-weight: 900; color: #003366; letter-spacing: -1px; }
    
    /* --- TICKER (RESTORED) --- */
    .ticker-wrap { background-color: #ffffff; border-top: 1px solid #f5f5f5; border-bottom: 1px solid #f5f5f5; height: 32px; overflow: hidden; white-space: nowrap; display: flex; align-items: center; margin-bottom: 20px; }
    .ticker-item { display: inline-block; padding-left: 100%; animation: ticker 80s linear infinite; font-size: 0.8rem; color: #333; font-weight: 600; }
    .ticker-label { position: absolute; left: 0; background: white; z-index: 10; padding: 5px 15px; font-size: 0.7rem; font-weight: 700; color: #cc0000; border-right: 1px solid #eee; height: 30px; line-height: 22px; }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    /* --- HERO SLIDER (MSN STYLE) --- */
    .hero-wrapper { 
        position: relative; height: 450px; overflow: hidden; 
        border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        z-index: 1; 
    }
    .hero-image { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.65); transition: 0.5s; }
    .hero-overlay { 
        position: absolute; bottom: 0; left: 0; width: 100%; padding: 40px; 
        background: linear-gradient(to top, rgba(0,0,0,0.9), transparent); pointer-events: none;
    }
    .hero-title { 
        font-family: 'Merriweather', serif; color: white !important; 
        font-size: 2.2rem; font-weight: 700; line-height: 1.2; 
        text-shadow: 0 2px 5px black; text-decoration: none; cursor: pointer; pointer-events: auto;
    }
    
    /* --- DOTS (TINY) --- */
    .msn-dots-container {
        position: absolute; bottom: 15px; left: 50%; transform: translateX(-50%);
        display: flex; gap: 6px; z-index: 10;
    }
    .msn-dot {
        width: 6px; height: 6px; border-radius: 50%;
        background-color: rgba(255,255,255,0.4); transition: 0.3s;
    }
    .msn-dot.active {
        background-color: #fff; transform: scale(1.3); box-shadow: 0 0 4px rgba(255,255,255,0.8);
    }

    /* --- FLOATING ARROWS (ZERO HEIGHT TRICK) --- */
    .floating-arrows {
        position: absolute;
        width: 100%;
        height: 0px !important; 
        z-index: 999;
        pointer-events: none; 
    }
    
    /* The Buttons */
    .floating-arrows button {
        pointer-events: auto !important;
        position: relative;
        top: 200px; /* Push down to middle of image */
        
        /* Glass Style */
        background-color: rgba(255, 255, 255, 0.25) !important;
        backdrop-filter: blur(4px);
        color: white !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        border-radius: 4px !important;
        width: 40px !important; height: 40px !important;
        display: flex; align-items: center; justify-content: center;
        transition: 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .floating-arrows button:hover {
        background-color: white !important;
        color: black !important;
        transform: scale(1.1);
    }
    .floating-arrows button p { font-size: 20px !important; line-height: 1; margin-bottom: 2px; }

    /* --- LIST ITEMS & CARDS --- */
    .list-item { background: white; padding: 15px; border-bottom: 1px solid #f0f0f0; margin-bottom: 5px; transition: 0.2s; }
    .list-item:hover { border-left: 3px solid #003366; background: #fafafa; }
    .list-title a { color: #111 !important; text-decoration: none; font-weight: 600; font-size: 1.05rem; }
    
    .grid-card { background: white; border: 1px solid #f5f5f5; border-radius: 4px; overflow: hidden; height: 100%; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .article-date { font-size: 0.7rem; color: #aaa; text-align: right; margin-top: 10px; border-top: 1px solid #f9f9f9; padding-top: 5px; }

    /* --- BADGES --- */
    .badge-sos { background: #dc3545; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.6rem; font-weight: bold; margin-right: 5px; }
    .badge-law { background: #003366; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.6rem; font-weight: bold; margin-right: 5px; }
    .badge-real { background: #28a745; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.6rem; font-weight: bold; margin-right: 5px; }

    /* --- DARK MODE --- */
    @media (prefers-color-scheme: dark) {
        html, body, [class*="css"] { background-color: #0e1117; color: #fafafa; }
        div[data-baseweb="input"] { background: #262730 !important; border: 1px solid #444 !important; }
        
        .tv-light-container { display: none !important; } .tv-dark-container { display: block !important; }
        
        .list-item { background: #262730 !important; border-bottom: 1px solid #444; }
        .list-item:hover { background: #30333d !important; }
        .list-title a { color: #fff !important; }
        
        .ticker-wrap { background: #262730 !important; border-color: #444; }
        .ticker-item { color: #ddd; }
        .ticker-label { background: #262730 !important; border-right: 1px solid #444; }
        
        [data-testid="collapsedControl"], [data-testid="stSidebar"] button { color: white !important; }
        .brand-card { background: #262730 !important; border: none !important; }
        .brand-card img { filter: invert(1); }
        .header-container { background: #0e1117 !important; border-bottom: 3px solid #4da6ff; }
        .header-logo { color: white !important; }
        
        iframe[title="3rd party frame"] { filter: invert(1) hue-rotate(180deg) brightness(1.2); }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. AUTO-PLAY LOGIC ---
if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0
if 'last_run' not in st.session_state: st.session_state.last_run = time.time()

# 6 Second Auto Timer
if time.time() - st.session_state.last_run > 6:
    st.session_state.slider_idx += 1
    st.session_state.last_run = time.time()
    st.rerun()

# --- 4. HELPERS & DATA ---
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

def get_db_client():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        return gc.open("laws_database")
    except Exception as e: return None

def save_subscriber(email):
    sh = get_db_client()
    if not sh: return "DB_ERROR"
    try: worksheet = sh.worksheet("subscribers")
    except: return "NO_SHEET"
    try:
        emails = worksheet.col_values(1)
        if email in emails: return "EXISTS"
        worksheet.append_row([email, str(datetime.now().strftime("%Y-%m-%d %H:%M"))])
        return "OK"
    except Exception as e: return "WRITE_ERROR"

def load_data():
    sh = get_db_client()
    if not sh: return []
    try: return sh.sheet1.get_all_records()
    except: return []

def reset_database():
    sh = get_db_client()
    if not sh: return False
    try:
        sh.sheet1.batch_clear(["A2:H5000"])
        sh.sheet1.append_row(['id', 'source', 'title', 'content', 'link', 'last_update', 'category', 'image_url'])
        return True
    except: return False

@st.cache_data
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return None

def normalize_greek(text):
    if not isinstance(text, str): return ""
    replacements = {'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω'}
    text = text.translate(str.maketrans(replacements))
    return text.lower()

def render_badges(category_str):
    badges_html = ""
    if "SOS" in category_str: badges_html += '<span class="badge-sos">🚨 SOS</span>'
    if "JUDICIAL" in category_str: badges_html += '<span class="badge-law">⚖️ ΔΙΚΑΣΤΗΡΙΑ</span>'
    if "LEGAL" in category_str: badges_html += '<span class="badge-law">⚖️ ΝΟΜΙΚΟ</span>'
    if "REAL_ESTATE" in category_str: badges_html += '<span class="badge-real">🏠 REAL ESTATE</span>'
    if "LEGISLATION" in category_str: badges_html += '<span class="badge-sos">📜 ΝΟΜΟΘΕΣΙΑ</span>'
    return badges_html

def get_display_image(row):
    if 'image_url' in row and str(row['image_url']).startswith('http'): return row['image_url']
    return get_stock_image(row['category'], row['title'])

# --- 5. SIDEBAR ---
with st.sidebar:
    nikas_url = "https://www.nikastechnical.gr"
    logo_b64 = get_image_as_base64("logo.jpg")
    img_html = f'<img src="data:image/jpeg;base64,{logo_b64}" style="width:100%; max-width:180px; margin:0 auto 15px auto; display:block;">' if logo_b64 else '<div style="font-size:2rem; margin-bottom:10px;">🏗️</div>'

    st.markdown(f"""
    <div class="brand-card">
        <div style="font-size:0.7rem; color:#666; margin-bottom:10px;">POWERED BY</div>
        {img_html}
        <div style="font-family: 'Montserrat', sans-serif; font-size: 0.8rem; margin-bottom: 15px;">Construction Engineering</div>
        <a href="{nikas_url}" target="_blank" class="brand-btn">ΕΠΙΣΚΕΦΘΕΙΤΕ ΜΑΣ</a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### ⏳ Προθεσμίες")
    st.info("⚠️ **31/12:** Λήξη Κτηματολογίου")
    st.info("⚠️ **31/01:** MyDATA Διαβίβαση")
    st.markdown("---")
    st.markdown("### ☁️ Καιρός")
    components.iframe("https://www.meteoblue.com/en/weather/widget/three/athens_greece_264371?geoloc=fixed&nocurrent=0&noforecast=0&days=4&tempunit=CELSIUS&windunit=KILOMETER_PER_HOUR&layout=image", height=240)
    st.markdown("---")
    st.markdown("### 📬 Newsletter")
    email = st.text_input("Email", placeholder="me@example.com")
    if st.button("Εγγραφή"):
        if "@" in email and "." in email:
            status = save_subscriber(email)
            if status == "OK": st.success("✅ Εγγραφήκατε!"); time.sleep(2); st.rerun()
            elif status == "EXISTS": st.warning("Είστε ήδη μέλος.")
            elif status == "NO_SHEET": st.error("Σφάλμα Βάσης.")
        else: st.error("Άκυρο email.")

# --- 6. MAIN UI ---
st.markdown("""
<div class="header-container">
    <div style="font-size:0.75rem; color:#666; margin-bottom:5px;">Intelligence Platform</div>
    <div class="header-logo">🏛️ NomoTechi</div>
    <div style="font-size:0.8rem; color:#888;">Powered by NiKAS Technical</div>
</div>
""", unsafe_allow_html=True)

raw_data = load_data()
if not raw_data:
    st.warning("⏳ Φόρτωση δεδομένων ή η βάση είναι κενή...")
    st.stop()
df = pd.DataFrame(raw_data)

st.markdown('<div class="search-container">', unsafe_allow_html=True)
search_query = st.text_input("", placeholder="🔍 Αναζήτηση (π.χ. Αυθαίρετα, Άρειος Πάγος)...")
st.markdown('</div>', unsafe_allow_html=True)

if search_query:
    clean_query = normalize_greek(search_query)
    mask = df.apply(lambda row: 
                    clean_query in normalize_greek(str(row['title'])) or 
                    clean_query in normalize_greek(str(row['content'])) or 
                    clean_query in normalize_greek(str(row['category'])), axis=1)
    df = df[mask]

# --- TICKER (RESTORED) ---
if not df.empty:
    latest_titles = "   +++   ".join([f"{row['title']}" for idx, row in df.head(10).iterrows()])
    st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker-label">LATEST</div>
        <div class="ticker-item">{latest_titles}</div>
    </div>
    """, unsafe_allow_html=True)

tabs = st.tabs(["ΚΟΡΥΦΑΙΑ", "ΜΗΧΑΝΙΚΟΙ & ΑΚΙΝΗΤΑ", "ΝΟΜΙΚΑ & ΔΙΚΑΙΟΣΥΝΗ", "ΝΟΜΟΘΕΣΙΑ/ΦΕΚ", "ΣΤΑΤΙΣΤΙΚΑ"])

def get_filtered_df(tab_name):
    if tab_name == "HOME": return df 
    if tab_name == "ENG": 
        return df[df['category'].str.contains("ENGINEERS|REAL_ESTATE|Μηχανικ|Ακίνητα", case=False, na=False)]
    if tab_name == "LAW": 
        legal_mask = df['category'].str.contains("LEGAL|JUDICIAL|Νομικ|Δικαιοσύνη", case=False, na=False)
        eng_mask = df['category'].str.contains("ENGINEERS|REAL_ESTATE|Μηχανικ|Ακίνητα", case=False, na=False)
        return df[legal_mask & ~eng_mask]
    if tab_name == "FEK": 
        return df[df['category'].str.contains("LEGISLATION|Νομοθεσία|ΦΕΚ", case=False, na=False)]
    return df

def render_tab_content(tab_code):
    current_df = get_filtered_df(tab_code).reset_index(drop=True)
    if current_df.empty:
        st.info("Δεν υπάρχουν νέα σε αυτή την κατηγορία.")
        return

    if not search_query and tab_code == "HOME":
        # --- TRADINGVIEW (Single Component) ---
        components.html("""
        <style> body{margin:0; overflow:hidden;} .light{display:block;} .dark{display:none;} @media(prefers-color-scheme:dark){.light{display:none;} .dark{display:block;}} </style>
        <div class="light"><div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>{"symbols":[{"proName":"ATHEX:GD","title":"ATHEX"},{"proName":"FOREXCOM:SPXUSD","title":"S&P 500"},{"proName":"FX_IDC:EURUSD","title":"EUR/USD"}],"colorTheme":"light","isTransparent":true,"displayMode":"compact","locale":"el"}</script></div></div>
        <div class="dark"><div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>{"symbols":[{"proName":"ATHEX:GD","title":"ATHEX"},{"proName":"FOREXCOM:SPXUSD","title":"S&P 500"},{"proName":"FX_IDC:EURUSD","title":"EUR/USD"}],"colorTheme":"dark","isTransparent":true,"displayMode":"compact","locale":"el"}</script></div></div>
        """, height=70)

        c_hero, c_list = st.columns([1.8, 1.2])
        
        with c_hero:
            # Slider Logic
            slide_len = min(5, len(current_df))
            idx = st.session_state.slider_idx % slide_len
            row = current_df.iloc[idx]
            hero_img = get_display_image(row)
            hero_badges = render_badges(row['category'])

            # --- ARROWS (THE GHOST OVERLAY) ---
            # Render buttons FIRST. Zero height container.
            st.markdown('<div class="floating-arrows">', unsafe_allow_html=True)
            b_col1, b_col2, b_col3 = st.columns([1, 10, 1])
            with b_col1:
                if st.button("❮", key="prev"):
                    st.session_state.slider_idx -= 1
                    st.session_state.last_run = time.time() # Reset Autoplay
                    st.rerun()
            with b_col3:
                if st.button("❯", key="next"):
                    st.session_state.slider_idx += 1
                    st.session_state.last_run = time.time() # Reset Autoplay
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            # --- HERO IMAGE & DOTS ---
            dots = "".join([f'<div class="msn-dot {"active" if i==idx else ""}"></div>' for i in range(slide_len)])
            
            st.markdown(f"""
            <div class="hero-wrapper">
                <img src="{hero_img}" class="hero-image">
                <div class="hero-overlay">
                    <div style="margin-bottom:5px;">{hero_badges}</div>
                    <a href="{row['link']}" target="_blank" class="hero-title">{row['title']}</a>
                    <div style="color:#ddd; margin-top:5px; font-size:0.8rem;">{row['last_update']}</div>
                </div>
                <div class="msn-dots-container">{dots}</div>
            </div>
            """, unsafe_allow_html=True)

        with c_list:
            st.markdown("### Top Stories")
            for i, r in current_df.head(5).iterrows():
                st.markdown(f"""
                <div class="list-item">
                    <div class="list-title"><a href="{r['link']}" target="_blank">{r['title']}</a></div>
                    <div style="font-size:0.75rem; color:#888;">{r['last_update']}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("---")

    st.subheader("Ειδήσεις & Αποφάσεις")
    
    # Grid
    grid_df = current_df.iloc[5:] if tab_code == "HOME" else current_df
    if not grid_df.empty:
        rows = len(grid_df) // 3 + 1
        for i in range(rows):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                idx = i * 3 + j
                if idx < len(grid_df):
                    row = grid_df.iloc[idx]
                    img = get_display_image(row)
                    badges = render_badges(row['category'])
                    with col:
                        # Card Container
                        st.markdown(f"""
                        <div class="grid-card">
                            <img src="{img}" style="width:100%; height:180px; object-fit:cover;">
                            <div style="padding:15px;">
                                <div style="font-weight:700; margin-bottom:5px; font-size:1.05rem;">{row['title']}</div>
                                <div style="margin-bottom:10px;">{badges}</div>
                                <div style="font-size:0.8rem; color:#666; margin-bottom:10px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">{row['content'][:150]}...</div>
                                <a href="{row['link']}" target="_blank" style="text-decoration:none; color:#003366; font-weight:600; font-size:0.85rem;">Διαβάστε περισσότερα →</a>
                                <div class="article-date">{row['last_update']}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("") # Spacer

with tabs[0]: render_tab_content("HOME")
with tabs[1]: render_tab_content("ENG")
with tabs[2]: render_tab_content("LAW")
with tabs[3]: render_tab_content("FEK")
with tabs[4]: 
    st.header("📊 Market Intelligence")
    col1, col2, col3 = st.columns(3)
    col1.metric("Σύνολο Άρθρων", len(df))
    col2.metric("SOS", len(df[df['category'].str.contains("SOS", na=False)]))
    col3.metric("Νομοθεσία", len(df[df['category'].str.contains("LEGISLATION", na=False)]))
    
    st.markdown("### Admin")
    if st.secrets.get("admin_password") and st.text_input("Pass", type="password") == st.secrets["admin_password"]:
        if st.button("🧹 Clear Cache"): st.cache_data.clear(); st.rerun()
        if st.button("🔴 RESET DATABASE"): reset_database(); st.cache_data.clear(); st.rerun()
        st.dataframe(df)
