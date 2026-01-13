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

# --- 2. CSS (THE FINAL FIX v22) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Segoe+UI:wght@300;400;600&display=swap');
    
    /* =========================================
       === LIGHT MODE (DEFAULT) === 
       ========================================= */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; background-color: #f8f9fa; color: #222; }
    
    /* Arrow Fix */
    [data-testid="collapsedControl"] { display: block !important; opacity: 1 !important; color: #000000 !important; }
    [data-testid="stSidebar"] button { opacity: 1 !important; color: #000000 !important; }

    /* Top Branding */
    .top-powered-brand {
        font-family: 'Segoe UI', sans-serif; font-size: 0.75rem; font-weight: 400; color: #666;
        letter-spacing: 0.5px; margin-bottom: 2px; text-align: center; padding-top: 15px;
    }
    .top-powered-brand a { color: #444 !important; text-decoration: none; border-bottom: 1px solid transparent; transition: 0.3s; }
    .top-powered-brand a:hover { color: #000 !important; border-bottom: 1px solid #000; }

    /* Brand Card (NO BORDERS) */
    .brand-card {
        background: #ffffff;
        border: none !important; 
        outline: none !important;
        border-radius: 4px; 
        padding: 25px 15px;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        text-align: center;
    }
    .brand-btn { 
        display: block; width: 100%; text-align: center;
        background-color: #111; color: #fff !important;
        border: none; padding: 10px 0; 
        border-radius: 2px; font-size: 0.8rem; font-weight: 600;
        text-decoration: none; transition: 0.3s;
        font-family: 'Segoe UI', sans-serif; text-transform: uppercase; letter-spacing: 1px;
    }
    .brand-btn:hover { background-color: #444; color: #fff !important; }

    /* Header */
    .header-container { 
        background: white; padding: 0 0 25px 0; 
        border-bottom: 2px solid #003366; text-align: center; 
        box-shadow: none !important; margin-bottom: 15px; 
    }
    .header-logo { font-family: 'Merriweather', serif; font-size: 3rem; font-weight: 900; color: #003366; letter-spacing: -1px; }
    .header-sub { color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 2px; font-weight: 500; margin-top:5px;}
    
    .powered-footer { text-align: center; font-size: 0.75rem; color: #999; margin-top: 40px; border-top: 1px solid #eee; padding-top: 15px; }
    .powered-footer a { color: #333; text-decoration: none; font-weight: 600; }

    /* Cards (NO BORDERS) */
    .list-item { 
        background: white; padding: 20px; 
        border: none !important; 
        border-bottom: 1px solid #f5f5f5 !important;
        transition: 0.2s; margin-bottom: 5px; 
    }
    .list-item:hover { background-color: #fafafa; border-left: 3px solid #003366 !important; }
    .list-title { font-family: 'Segoe UI', sans-serif; font-size: 1.1rem; font-weight: 600; color: #111; margin-bottom: 5px; line-height: 1.4; }
    .list-title a { color: #111 !important; text-decoration: none; }
    .list-title a:hover { color: #003366 !important; }

    .grid-card { 
        background: white; 
        border: none !important; 
        outline: none !important;
        border-radius: 4px; 
        overflow: hidden; height: 100%; display: flex; flex-direction: column; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        transition: transform 0.2s; 
    }
    .grid-card:hover { transform: translateY(-3px); box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
    .grid-title { font-family: 'Segoe UI', sans-serif; font-size: 1.05rem; font-weight: 700; color: #111; margin-bottom: 8px; line-height: 1.35; }
    .article-date { font-size: 0.7rem; color: #aaa; text-align: right; margin-top: 10px; border-top: 1px solid #f9f9f9; padding-top: 5px; }

    /* Ticker Light */
    .ticker-wrap { background-color: #ffffff; border-top: 1px solid #f5f5f5; border-bottom: 1px solid #f5f5f5; height: 32px; overflow: hidden; white-space: nowrap; display: flex; align-items: center; margin-bottom: 20px; }
    .ticker-item { display: inline-block; padding-left: 100%; animation: ticker 80s linear infinite; font-size: 0.8rem; color: #333; font-weight: 600; }
    .ticker-label { position: absolute; left: 0; background: white; z-index: 10; padding: 5px 15px; font-size: 0.7rem; font-weight: 700; color: #cc0000; border-right: 1px solid #eee; height: 30px; line-height: 22px; }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    /* Hero Slider Overlay Styling (Restored) */
    .hero-wrapper { 
        position: relative; height: 450px; overflow: hidden; margin-bottom: 25px; 
        box-shadow: 0 5px 15px rgba(0,0,0,0.15); border-radius: 4px; border: none !important;
    }
    .hero-image { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.65); transition: transform 6s ease; }
    .hero-image:hover { transform: scale(1.05); filter: brightness(0.75); }
    .hero-overlay { 
        position: absolute; bottom: 0; left: 0; width: 100%; padding: 40px; 
        background: linear-gradient(to top, rgba(0,0,0,0.9), transparent); 
    }
    .hero-title { 
        font-family: 'Merriweather', serif; color: white !important; 
        font-size: 2.2rem; font-weight: 700; line-height: 1.2; 
        text-shadow: 0 2px 5px black; text-decoration: none; cursor: pointer;
    }
    .hero-title:hover { text-decoration: underline; color: #f0f0f0 !important; }

    /* Micro-Badges */
    .badge-sos { background-color: #dc3545; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.55rem; font-weight: 700; margin-right: 3px; display: inline-block; letter-spacing: 0.5px; }
    .badge-law { background-color: #003366; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.55rem; font-weight: 700; margin-right: 3px; display: inline-block; letter-spacing: 0.5px; }
    .badge-real { background-color: #28a745; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.55rem; font-weight: 700; margin-right: 3px; display: inline-block; letter-spacing: 0.5px; }
    .badge-leg { background-color: #444; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.55rem; font-weight: 700; margin-right: 3px; display: inline-block; letter-spacing: 0.5px; }

    .stTextInput input { border-radius: 2px; border: 1px solid #e0e0e0; padding: 10px; background-color: #fff; }

    /* =========================================
       === DARK MODE (INVERTED & FIXED) === 
       ========================================= */
    @media (prefers-color-scheme: dark) {
        html, body, [class*="css"] { background-color: #0e1117; color: #fafafa; }
        
        /* Arrow & Logo Invert */
        [data-testid="collapsedControl"], [data-testid="stSidebar"] button { color: #ffffff !important; }
        .brand-card img { filter: invert(1); } 

        /* Header Dark */
        .header-container { background: #0e1117 !important; border-bottom: 3px solid #4da6ff; }
        .header-logo { color: #fff !important; }
        .header-sub { color: #aaa !important; }
        .top-powered-brand { color: #888 !important; }
        .top-powered-brand a { color: #fff !important; }
        .top-powered-brand a:hover { border-bottom: 1px solid #fff; }

        /* Ticker Dark */
        .ticker-wrap { background-color: #262730 !important; border-color: #444 !important; }
        .ticker-item { color: #eee !important; }
        .ticker-label { background: #262730 !important; color: #ff4b4b !important; border-right: 1px solid #444 !important; }

        /* Brand Card Dark */
        .brand-card { background: #262730 !important; border: none !important; box-shadow: none !important; }
        .brand-sub { color: #ddd !important; }
        .brand-btn { background-color: #eee !important; color: #000 !important; }

        /* Cards Dark */
        .list-item { background: #262730 !important; border-bottom: 1px solid #444 !important; }
        .list-item:hover { background-color: #30333d !important; border-left: 3px solid #4da6ff !important; }
        .list-title, .list-title a { color: #fff !important; }
        
        .grid-card { background: #262730 !important; border: none !important; box-shadow: none !important; }
        .grid-title { color: #fff !important; }
        .grid-img { background: #333 !important; }
        
        .article-date { color: #777 !important; border-top: 1px solid #444 !important; }
        .powered-footer { color: #666 !important; border-top: 1px solid #333 !important; }
        .powered-footer a { color: #bbb !important; }

        /* --- TRADINGVIEW DARK MODE FIX (ONLY IN DARK MODE) --- */
        iframe[title="3rd party frame"] { 
            filter: invert(1) hue-rotate(180deg) !important;
        } 
        
        .stTextInput input { background-color: #262730; color: white; border: 1px solid #555; }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC & HELPERS ---
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

def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

def normalize_greek(text):
    if not isinstance(text, str): return ""
    replacements = {
        'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
        'Ά': 'Α', 'Έ': 'Ε', 'Ή': 'Η', 'Ί': 'Ι', 'Ό': 'Ο', 'Ύ': 'Υ', 'Ώ': 'Ω',
        'ϊ': 'ι', 'ϋ': 'υ', 'ΐ': 'ι', 'ΰ': 'υ'
    }
    text = text.translate(str.maketrans(replacements))
    return text.lower()

# --- 5. SIDEBAR ---
with st.sidebar:
    nikas_url = "https://www.nikastechnical.gr"
    logo_b64 = get_image_as_base64("logo.jpg")
    if not logo_b64: logo_b64 = get_image_as_base64("logo.png")
    img_html = f'<img src="data:image/jpeg;base64,{logo_b64}" style="width:100%; max-width:180px; margin:0 auto 15px auto; display:block;">' if logo_b64 else '<div style="font-size:2rem; margin-bottom:10px;">🏗️</div>'

    st.markdown(f"""
    <div class="brand-card">
        <div class="brand-label">POWERED BY</div>
        {img_html}
        <div class="brand-sub" style="font-family: 'Montserrat', sans-serif; font-size: 0.8rem; color: #000; margin-bottom: 15px;">Construction Engineering</div>
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
            elif status == "NO_SHEET": st.error("Σφάλμα Βάσης: Λείπει το φύλλο subscribers.")
        else: st.error("Άκυρο email.")

# --- 6. MAIN UI ---
st.markdown("""
<div class="header-container">
    <div class="top-powered-brand"><a href="https://www.nikastechnical.gr" target="_blank">Powered by NiKAS Technical | @nikas.tech</a></div>
    <div class="header-logo">🏛️ NomoTechi</div>
    <div class="header-sub">Intelligence Platform for Professionals</div>
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

# --- TICKER ---
if not df.empty:
    latest_titles = "   +++   ".join([f"{row['title']}" for idx, row in df.head(10).iterrows()])
    st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker-label">LATEST</div>
        <div class="ticker-item">{latest_titles}</div>
    </div>
    """, unsafe_allow_html=True)

tabs = st.tabs(["ΚΟΡΥΦΑΙΑ", "ΜΗΧΑΝΙΚΟΙ & ΑΚΙΝΗΤΑ", "ΝΟΜΙΚΑ & ΔΙΚΑΙΟΣΥΝΗ", "ΝΟΜΟΘΕΣΙΑ/ΦΕΚ", "ΣΤΑΤΙΣΤΙΚΑ"])

if df.empty and search_query:
    st.warning(f"⚠️ Δεν βρέθηκαν αποτελέσματα για: **'{search_query}'**")
elif not df.empty:
    df = df.iloc[::-1].reset_index(drop=True)
    if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0

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

    def render_badges(category_str):
        badges_html = ""
        if "SOS" in category_str: badges_html += '<span class="badge-sos">🚨 SOS</span>'
        if "JUDICIAL" in category_str: badges_html += '<span class="badge-law">⚖️ ΔΙΚΑΣΤΗΡΙΑ</span>'
        if "LEGAL" in category_str and "ENGINEERS" not in category_str: badges_html += '<span class="badge-law">⚖️ ΝΟΜΙΚΟ</span>'
        if "REAL_ESTATE" in category_str: badges_html += '<span class="badge-real">🏠 REAL ESTATE</span>'
        if "LEGISLATION" in category_str: badges_html += '<span class="badge-leg">📜 ΝΟΜΟΘΕΣΙΑ</span>'
        return badges_html

    def get_display_image(row):
        if 'image_url' in row and str(row['image_url']).startswith('http'): return row['image_url']
        return get_stock_image(row['category'], row['title'])

    def render_tab_content(tab_code):
        current_df = get_filtered_df(tab_code).reset_index(drop=True)
        if current_df.empty:
            st.info("Δεν υπάρχουν νέα σε αυτή την κατηγορία.")
            return

        if not search_query and tab_code == "HOME":
            # --- TRADINGVIEW ---
            st.markdown("", unsafe_allow_html=True)
            components.html("""
            <div class="tradingview-widget-container">
              <div class="tradingview-widget-container__widget"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
              {
              "symbols": [{"proName": "ATHEX:GD", "title": "Χ.Α.Α."}, {"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"}, {"proName": "FX_IDC:EURUSD", "title": "EUR/USD"}, {"proName": "XETRA:DAX", "title": "DAX"}],
              "showSymbolLogo": true, "colorTheme": "light", "isTransparent": true, "displayMode": "compact", "locale": "el"
              }
              </script>
            </div>
            """, height=70)
            st.markdown("", unsafe_allow_html=True)
            
            col_hero, col_list = st.columns([1.8, 1.2])
            with col_hero:
                slider_len = min(5, len(current_df))
                current_slide = st.session_state.slider_idx % slider_len
                hero_article = current_df.iloc[current_slide]
                hero_img = get_display_image(hero_article)
                hero_badges = render_badges(hero_article['category'])
                
                # --- HERO SLIDER OVERLAY (RESTORED) ---
                st.markdown(f"""
                <div class="hero-wrapper">
                    <img src="{hero_img}" class="hero-image" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200';">
                    <div class="hero-overlay">
                        <div>{hero_badges}</div>
                        <a href="{hero_article['link']}" target="_blank" style="text-decoration:none;">
                            <div class="hero-title">{hero_article['title']}</div>
                        </a>
                        <div style="color:#ddd; margin-top:5px; font-size:0.8rem;">{hero_article['last_update']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([0.1, 0.8, 0.1])
                with c1: 
                    if st.button("❮", key=f"prev_{tab_code}"): st.session_state.slider_idx -= 1; st.rerun()
                with c3: 
                    if st.button("❯", key=f"next_{tab_code}"): st.session_state.slider_idx += 1; st.rerun()

            with col_list:
                st.markdown("### Top Stories")
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
                            with st.container():
                                st.image(card_img, use_column_width=True)
                                st.markdown(f"**{row['title']}**")
                                st.markdown(badges, unsafe_allow_html=True)
                                with st.expander("Ανάλυση & Σύνοψη"):
                                    st.markdown(row['content'])
                                st.markdown(f"[🔗 Πηγή]({row['link']})")
                                st.markdown(f"""<div class="article-date">{row['last_update']}</div>""", unsafe_allow_html=True)
                                st.markdown("---")

    with tabs[0]: render_tab_content("HOME")
    with tabs[1]: render_tab_content("ENG")
    with tabs[2]: render_tab_content("LAW")
    with tabs[3]: render_tab_content("FEK")
    
    with tabs[4]: 
        st.header("📊 Market Intelligence")
        col1, col2, col3 = st.columns(3)
        col1.metric("Σύνολο Άρθρων", len(df))
        sos_count = len(df[df['category'].str.contains("SOS", na=False)])
        col2.metric("🚨 SOS / Προθεσμίες", sos_count)
        law_count = len(df[df['category'].str.contains("LEGISLATION", na=False)])
        col3.metric("📜 Νέα Νομοθεσία", law_count)
        st.markdown("### 📈 Κατανομή ανά Κατηγορία")
        cat_counts = df['category'].value_counts().head(10)
        st.bar_chart(cat_counts)
        st.markdown(f"""
        <div class="powered-footer">
            NomoTechi Platform © {datetime.now().year} • Powered by <a href="{nikas_url}" target="_blank">NiKAS Technical</a>
        </div>
        """, unsafe_allow_html=True)
        st.header("Admin")
        if st.secrets.get("admin_password") and st.text_input("Pass", type="password") == st.secrets["admin_password"]:
            if st.button("🧹 Clear Cache"): st.cache_data.clear(); st.rerun()
            if st.button("🔴 RESET DATABASE"): reset_database(); st.cache_data.clear(); st.rerun()
            st.dataframe(df)
