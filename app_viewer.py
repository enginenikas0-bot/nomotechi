import streamlit as st
import pandas as pd
import gspread
import time
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import base64
import unicodedata

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTech | Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS (UNIFIED DARK THEME) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Segoe+UI:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    
    /* --- HEADER (MATCHING TICKER COLOR) --- */
    .header-container { 
        background-color: #1e293b !important; /* DARK SLATE BLUE (Same as Ticker) */
        padding: 20px 0 25px 0; 
        border-bottom: 1px solid #334155; /* Subtle border match */
        text-align: center; 
        margin-bottom: 0px; 
        border-radius: 0 0 0 0;
    }
    /* Force White Text */
    .header-logo { 
        font-family: 'Merriweather', serif; 
        font-size: 2.5rem; 
        font-weight: 900; 
        color: #ffffff !important; 
        letter-spacing: -1px; 
        line-height: 1.2; 
    }
    .powered-text { font-size: 0.75rem; color: #94a3b8 !important; letter-spacing: 1px; }
    .sub-text { font-size: 0.75rem; color: #cbd5e1 !important; margin-top: 5px; }

    /* --- TICKER (ALWAYS DARK SLATE) --- */
    .ticker-container { 
        width: 100%; 
        overflow: hidden; 
        background-color: #1e293b !important; /* Matches Header */
        border-top: 1px solid #334155; 
        border-bottom: 1px solid #334155; 
        white-space: nowrap; 
        height: 42px; 
        display: flex; 
        align-items: center; 
        margin-bottom: 20px;
    }
    .ticker-content { display: inline-block; padding-left: 100%; animation: ticker-scroll 80s linear infinite; }
    .ticker-content:hover { animation-play-state: paused; }
    .ticker-text { 
        font-family: 'Segoe UI', sans-serif; 
        font-weight: 600; 
        color: #f1f5f9 !important; /* White-ish text */
        font-size: 0.9rem; 
    }
    @keyframes ticker-scroll { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    /* --- SIDEBAR (ALWAYS DARK) --- */
    [data-testid="stSidebar"] { background-color: #111827 !important; border-right: 1px solid #374151; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; font-weight: 500; }
    .sidebar-header { color: #ffffff !important; font-family: 'Montserrat', sans-serif; font-weight: 700; font-size: 1rem; margin-bottom: 10px; border-bottom: 2px solid #3b82f6; padding-bottom: 5px; display: inline-block; }
    .sidebar-card { background: #1f2937; border: 1px solid #374151; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; }
    .sidebar-logo { max-width: 120px; margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto; filter: brightness(1.1); }
    .sidebar-btn { display: block; width: 100%; background-color: #000000; color: white !important; text-decoration: none; padding: 10px 0; border-radius: 4px; font-size: 0.8rem; font-weight: 700; margin-top: 15px; transition: 0.2s; border: 1px solid #333; }
    .sidebar-btn:hover { background-color: #333333; color: white !important; border-color: #fff; }

    /* --- SEARCH BAR --- */
    div[data-baseweb="input"] { background-color: #f0f2f6 !important; border: 1px solid #ccc; border-radius: 4px; }
    .search-container div[data-baseweb="input"] { background-color: #003366 !important; border: 1px solid #004080; }
    .search-container div[data-baseweb="input"] input { color: white !important; caret-color: white; }

    /* --- SLIDER --- */
    .hero-wrapper { position: relative; height: 450px; overflow: hidden; border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); z-index: 1; }
    .hero-image { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.65); transition: 0.5s; }
    .hero-overlay { position: absolute; bottom: 0; left: 0; width: 100%; padding: 40px 20px 60px 20px; background: linear-gradient(to top, rgba(0,0,0,0.9), transparent); pointer-events: none; }
    .hero-title { font-family: 'Merriweather', serif; color: white !important; font-size: 1.8rem; font-weight: 700; line-height: 1.2; text-shadow: 0 2px 5px black; text-decoration: none; cursor: pointer; pointer-events: auto; }

    /* Visual Dots */
    .msn-dots-container { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 8px; z-index: 10; pointer-events: none; }
    .msn-dot { width: 8px; height: 8px; border-radius: 50%; background-color: rgba(255, 255, 255, 0.4); transition: all 0.3s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }
    .msn-dot.active { background-color: #ffffff; transform: scale(1.3); box-shadow: 0 0 8px rgba(255, 255, 255, 0.8); }

    /* Cards */
    .list-item { background: #1e293b; padding: 15px; border-radius: 6px; margin-bottom: 8px; border-left: 4px solid #3b82f6; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .list-title a { color: #ffffff !important; text-decoration: none; font-weight: 600; font-size: 1.05rem; }
    .list-date { color: #cbd5e1 !important; font-size: 0.75rem; margin-top: 5px; }
    
    .grid-card { background: white; border: 1px solid #f5f5f5; border-radius: 4px; overflow: hidden; height: 100%; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display:flex; flex-direction:column; }
    .article-meta { font-size: 0.75rem; color: #888; text-align: right; margin-top: auto; padding-top: 10px; border-top: 1px solid #f9f9f9; }

    /* Badges */
    .badge-sos { background: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-law { background: #003366; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-real { background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-fek { background: #666; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-tech { background: #e67e22; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }

    /* Dark Mode (System) Overrides */
    @media (prefers-color-scheme: dark) {
        html, body, [class*="css"] { background-color: #0e1117 !important; color: #fafafa !important; }
        .grid-card { background: #262730 !important; border: none !important; }
        .article-meta { border-top-color: #334155 !important; color: #94a3b8 !important; }
        
        /* Force Header/Ticker Consistency in Dark Mode */
        .header-container { background-color: #1e293b !important; }
        .ticker-container { background-color: #1e293b !important; }
        
        /* Inputs in dark mode */
        div[data-baseweb="input"] { background-color: #262730 !important; border-color: #444 !important; }
        div[data-baseweb="input"] input { color: white !important; }
        .search-container div[data-baseweb="input"] { background-color: #003366 !important; } 
        [data-testid="collapsedControl"] { color: white !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC ---
SOURCE_HINTS = {
    "ENG": ["pomida", "ypodomes", "b2green", "tee", "pedmede", "michanikos", "elinyae"],
    "LAW": ["dikastiko", "lawspot", "syntagma", "lawnet", "dsa", "ethemis"],
    "FEK": ["e-nomothesia", "taxheaven", "capital"]
}

def normalize_text(text):
    if not isinstance(text, str): return ""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

def analyze_content(row):
    title = str(row.get('title', '')).upper()
    content = str(row.get('content', '')).upper()
    source = str(row.get('source', '')).lower()
    full_text = title + " " + content
    tags = []

    kw_eng = ['ΜΗΧΑΝΙΚ', 'ΕΡΓΑ', 'ΑΚΙΝΗΤ', 'REAL ESTATE', 'ΕΞΟΙΚΟΝΟΜΩ', 'ΑΝΑΚΑΙΝΙΖΩ', 'ΚΤΗΜΑΤΟΛΟΓΙΟ', 'ΑΥΘΑΙΡΕΤΑ', 'ΔΟΜΗΣΗ', 'ΥΠΟΔΟΜΕΣ', 'ΕΝΕΡΓΕΙΑ', 'ΠΕΑ', 'BUILDING', 'ΝΟΚ', 'ΟΙΚΟΔΟΜ', 'ΠΕΧΩΔΕ', 'ΥΠΕΝ', 'ΑΔΕΙΕΣ', 'ΚΑΤΑΣΚΕΥ', 'ΕΡΓΟΛΗΠΤ']
    kw_law = ['ΔΙΚΑΣΤ', 'ΑΡΕΙΟΣ ΠΑΓΟΣ', 'ΣΤΕ', 'ΔΙΚΗΓΟΡ', 'ΣΥΝΤΑΓΜΑ', 'ΔΙΚΗ', 'COURT', 'ΕΙΣΑΓΓΕΛ', 'ΑΓΩΓΗ', 'ΕΦΕΤΕΙΟ', 'ΠΡΩΤΟΔΙΚΕΙΟ', 'ΠΟΙΝΙΚ', 'ΑΣΤΙΚΟ', 'ΝΟΜΟΛΟΓΙΑ']
    kw_fek = ['ΦΕΚ', 'ΝΟΜΟΣ', 'ΑΠΟΦΑΣΗ', 'ΕΓΚΥΚΛΙΟΣ', 'ΔΙΑΤΑΞΗ', 'ΤΡΟΠΟΛΟΓΙΑ', 'ΥΠΟΥΡΓΙΚΗ', 'ΠΡΟΕΔΡΙΚΟ ΔΙΑΤΑΓΜΑ']

    has_eng = any(k in full_text for k in kw_eng)
    has_law = any(k in full_text for k in kw_law)
    has_fek = any(k in full_text for k in kw_fek)
    
    src_type = "GEN"
    for cat, keywords in SOURCE_HINTS.items():
        if any(k in source for k in keywords):
            src_type = cat
            break

    if has_fek or src_type == "FEK": tags.append("FEK")
    if src_type == "ENG" or has_eng: tags.append("ENG")
    if (src_type == "LAW" or has_law) and not has_eng: tags.append("LAW")
    if "SOS" in title or "ΠΡΟΘΕΣΜΙΑ" in title: tags.append("SOS")
    if not tags: tags.append("GENERAL")
    
    return tags

def get_db_client():
    try: return gspread.service_account_from_dict(st.secrets["gcp_service_account"]).open("laws_database")
    except: return None

def load_data():
    sh = get_db_client()
    if not sh: return []
    try: 
        raw = sh.sheet1.get_all_records()
        df = pd.DataFrame(raw)
        df = df[df['title'].str.lower() != 'title']
        df['datetime_obj'] = pd.to_datetime(df['last_update'], errors='coerce')
        cutoff = datetime.now() - timedelta(days=30)
        df = df[df['datetime_obj'] > cutoff]
        df = df.sort_values(by='datetime_obj', ascending=False)
        records = df.to_dict('records')
        for r in records: r['smart_tags'] = analyze_content(r)
        return records
    except: return []

def format_smart_date(date_str):
    try:
        dt = pd.to_datetime(date_str)
        now = datetime.now()
        if dt.date() == now.date(): return f"{dt.strftime('%d/%m/%y')} - {dt.strftime('%H:%M')}"
        return dt.strftime("%d/%m/%y")
    except: return str(date_str)

IMAGE_POOL = {
    "ENG": ["https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=1200"],
    "LAW": ["https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=1200"],
    "GENERAL": ["https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200"]
}

def get_image(row):
    tags = row.get('smart_tags', [])
    img = row.get('image_url', '')
    if str(img).startswith('http'): return img
    if "ENG" in tags: return IMAGE_POOL["ENG"][0]
    if "LAW" in tags: return IMAGE_POOL["LAW"][0]
    return IMAGE_POOL["GENERAL"][0]

def render_badges(row):
    tags = row.get('smart_tags', [])
    text = (str(row.get('title')) + " " + str(row.get('content'))).upper()
    badges_html = ""
    if "SOS" in tags: badges_html += '<span class="badge-sos">🚨 SOS</span>'
    if "ENG" in tags:
        if "REAL ESTATE" in text or "ΑΚΙΝΗΤ" in text: badges_html += '<span class="badge-real">🏠 REAL ESTATE</span>'
        else: badges_html += '<span class="badge-tech">🏗️ ΤΕΧΝΙΚΟ</span>'
    if "LAW" in tags: badges_html += '<span class="badge-law">⚖️ ΔΙΚΑΙΟΣΥΝΗ</span>'
    if "FEK" in tags: badges_html += '<span class="badge-fek">📜 ΝΟΜΟΘΕΣΙΑ</span>'
    return badges_html

def save_subscriber(email):
    sh = get_db_client()
    if not sh: return "DB_ERROR"
    try: 
        sh.worksheet("subscribers").append_row([email, str(datetime.now())])
        return "OK"
    except: return "WRITE_ERROR"

@st.cache_data
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f: data = f.read()
        return base64.b64encode(data).decode()
    except: return None

def reset_database(): return False

# --- 4. UI ---
with st.sidebar:
    logo_b64 = get_image_as_base64("logo.jpg")
    img_html = f'<img src="data:image/jpeg;base64,{logo_b64}" class="sidebar-logo">' if logo_b64 else '<div style="font-size:3rem; margin-bottom:10px;">🏗️</div>'
    
    st.markdown(f"""
    <div class="sidebar-card">
        <div style="font-size:0.7rem; color:#9ca3af; letter-spacing:1px; margin-bottom:10px;">POWERED BY</div>
        {img_html}
        <div style="font-weight:700; color:#f3f4f6; margin-top:10px; font-size:0.9rem;">NiKAS Technical</div>
        <div style="font-size:0.75rem; color:#9ca3af; margin-bottom:15px;">Construction Engineering</div>
        <a href="https://www.nikastechnical.gr" target="_blank" class="sidebar-btn">ΕΠΙΣΚΕΦΘΕΙΤΕ ΜΑΣ</a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-header">☁️ Καιρός Εργοταξίου</div>', unsafe_allow_html=True)
    components.iframe("https://www.meteoblue.com/en/weather/widget/three/athens_greece_264371?geoloc=fixed&nocurrent=0&noforecast=0&days=4&tempunit=CELSIUS&windunit=KILOMETER_PER_HOUR&layout=image", height=310)
    st.markdown("---")

    st.markdown('<div class="sidebar-header">📬 Ενημέρωση</div>', unsafe_allow_html=True)
    email = st.text_input("Email", placeholder="me@example.com", label_visibility="collapsed")
    if st.button("ΕΓΓΡΑΦΗ", type="primary"):
        if "@" in email and "." in email:
            status = save_subscriber(email)
            if status == "OK": st.success("✅ Εγγραφήκατε!")
            else: st.error("Σφάλμα σύνδεσης.")
        else:
            st.warning("Μη έγκυρο email.")

st.markdown("""
<div class="header-container">
    <div class="powered-text" style="margin-bottom:5px;">Powered by NiKAS Technical</div>
    <div class="header-logo">🏛️ NomoTech</div>
    <div class="sub-text" style="margin-top:5px;">Intelligence Platform</div>
</div>
""", unsafe_allow_html=True)

raw_data = load_data()
if not raw_data: st.warning("⏳ Φόρτωση..."); st.stop()
df = pd.DataFrame(raw_data)

st.markdown('<div class="search-container">', unsafe_allow_html=True)
search_query = st.text_input("", placeholder="🔍 Αναζήτηση...")
st.markdown('</div>', unsafe_allow_html=True)

if search_query:
    q_clean = normalize_text(search_query)
    q_words = q_clean.split()
    def search_algorithm(row):
        row_text = normalize_text(str(row['title']) + " " + str(row['content']) + " " + str(row.get('smart_tags', '')))
        return all(word in row_text for word in q_words)
    df = df[df.apply(search_algorithm, axis=1)]

if not df.empty:
    titles = "   +++   ".join([f"{r['title']}" for i, r in df.head(10).iterrows()])
    st.markdown(f"""
    <div class="ticker-container">
        <div class="ticker-content">
            <span class="ticker-text">{titles}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

tabs = st.tabs(["ΚΟΡΥΦΑΙΑ", "ΜΗΧΑΝΙΚΟΙ & ΑΚΙΝΗΤΑ", "ΝΟΜΙΚΑ & ΔΙΚΑΙΟΣΥΝΗ", "ΝΟΜΟΘΕΣΙΑ/ΦΕΚ", "ΣΤΑΤΙΣΤΙΚΑ"])

@st.fragment(run_every=6)
def show_hero_slider(curr_df):
    if curr_df.empty: return
    
    if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0
    st.session_state.slider_idx += 1

    slide_len = min(5, len(curr_df))
    idx = st.session_state.slider_idx % slide_len
    row = curr_df.iloc[idx]
    
    badges = render_badges(row)
    date_d = format_smart_date(row['last_update'])

    dots_html = ""
    for i in range(slide_len):
        active_cls = "active" if i == idx else ""
        dots_html += f'<div class="msn-dot {active_cls}"></div>'

    st.markdown(f"""
    <div class="hero-wrapper">
        <img src="{get_image(row)}" class="hero-image">
        <div class="hero-overlay">
            <div style="margin-bottom:5px;">{badges}</div>
            <a href="{row['link']}" target="_blank" class="hero-title">{row['title']}</a>
            <div style="color:#ddd; margin-top:5px; font-size:0.8rem;">{date_d}</div>
        </div>
        <div class="msn-dots-container">
            {dots_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_tab(tab_name):
    if tab_name == "HOME": 
        curr = df
    elif tab_name == "ENG":
        curr = df[df['smart_tags'].apply(lambda x: 'ENG' in x)]
    elif tab_name == "LAW":
        curr = df[df['smart_tags'].apply(lambda x: 'LAW' in x)]
    elif tab_name == "FEK":
        curr = df[df['smart_tags'].apply(lambda x: 'FEK' in x)]
    else:
        curr = pd.DataFrame()

    if curr.empty: st.info("Δεν βρέθηκαν άρθρα."); return

    if tab_name == "HOME" and not search_query:
        # JS WIDGET FOR MOBILE
        components.html("""
        <div id="tv-widget-container"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
        {
          "symbols": [{"proName": "ATHEX:GD", "title": "ATHEX"}, {"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"}, {"proName": "FX_IDC:EURUSD", "title": "EUR/USD"}],
          "colorTheme": window.matchMedia('(prefers-color-scheme: dark)').matches ? "dark" : "light",
          "isTransparent": true,
          "displayMode": "compact",
          "locale": "el"
        }
        </script>
        """, height=70)

        c_hero, c_list = st.columns([1.8, 1.2])
        with c_hero:
            show_hero_slider(curr) 
        
        with c_list:
            st.markdown("### Top Stories")
            for i, r in curr.head(5).iterrows():
                d = format_smart_date(r['last_update'])
                st.markdown(f"""
                <div class="list-item">
                    <div class="list-title">
                        <a href="{r['link']}" target="_blank">{r['title']}</a>
                    </div>
                    <div class="list-date">{d}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("---")

    st.subheader("Ειδήσεις & Αποφάσεις")
    cols = st.columns(3)
    start = 5 if (tab_name == "HOME" and not search_query) else 0
    
    grid_items = curr.iloc[start:]
    if not grid_items.empty:
        rows = len(grid_items) // 3 + 1
        for i in range(rows):
            c_cols = st.columns(3)
            for j, col in enumerate(c_cols):
                idx = i * 3 + j
                if idx < len(grid_items):
                    r = grid_items.iloc[idx]
                    d = format_smart_date(r['last_update'])
                    b = render_badges(r)
                    with col:
                        st.markdown('<div class="grid-card">', unsafe_allow_html=True)
                        st.image(get_image(r), use_column_width=True)
                        st.markdown(f"""<div style="padding:15px;">
                            <div style="font-weight:700; font-size:1.05rem; margin-bottom:5px;">{r['title']}</div>
                            <div style="margin-bottom:10px;">{b}</div>
                            </div>""", unsafe_allow_html=True)
                        
                        with st.expander("🤖 Ανάλυση & Σύνοψη"):
                            st.write(r['content'])
                        
                        st.markdown(f"""
                            <div style="padding:0 15px 15px 15px;">
                                <a href="{r['link']}" target="_blank" style="text-decoration:none; color:#003366; font-weight:600; font-size:0.85rem;">Διαβάστε περισσότερα →</a>
                                <div class="article-meta">{d}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("")

with tabs[0]: render_tab("HOME")
with tabs[1]: render_tab("ENG")
with tabs[2]: render_tab("LAW")
with tabs[3]: render_tab("FEK")
with tabs[4]: 
    st.metric("Total Articles", len(df))
    if st.secrets.get("admin_password") and st.text_input("Pass", type="password") == st.secrets["admin_password"]:
        if st.button("🔴 RESET DATABASE"): reset_database(); st.cache_data.clear(); st.rerun()
        st.dataframe(df)
