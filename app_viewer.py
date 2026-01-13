import streamlit as st
import pandas as pd
import gspread
import time
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import base64

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTech | Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS (FINAL CLEAN THEME) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Segoe+UI:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; background-color: #ffffff; color: #222; }
    
    /* Input */
    div[data-baseweb="input"] { background-color: #003366 !important; border: 1px solid #004080; border-radius: 4px; }
    div[data-baseweb="input"] input { color: white !important; caret-color: white; font-weight: 500; }
    
    /* Header */
    .header-container { background: white; padding: 10px 0 25px 0; border-bottom: 2px solid #003366; text-align: center; margin-bottom: 20px; }
    .header-logo { font-family: 'Merriweather', serif; font-size: 3rem; font-weight: 900; color: #003366; letter-spacing: -1px; line-height: 1.2; }

    /* Slider (No Arrows) */
    .hero-wrapper { position: relative; height: 450px; overflow: hidden; border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); z-index: 1; }
    .hero-image { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.65); transition: 0.5s; }
    .hero-overlay { position: absolute; bottom: 0; left: 0; width: 100%; padding: 40px; background: linear-gradient(to top, rgba(0,0,0,0.9), transparent); pointer-events: none; }
    .hero-title { font-family: 'Merriweather', serif; color: white !important; font-size: 2.2rem; font-weight: 700; line-height: 1.2; text-shadow: 0 2px 5px black; text-decoration: none; cursor: pointer; pointer-events: auto; }

    /* Invisible Click Zones */
    .click-zone-container { position: absolute; top: 0; left: 0; width: 100%; height: 450px; z-index: 999; pointer-events: none; }
    .click-zone-container button { pointer-events: auto !important; background: transparent !important; color: transparent !important; border: none !important; height: 450px !important; width: 100% !important; transition: 0.2s; }
    .click-zone-container button:hover { background: rgba(255,255,255,0.05) !important; cursor: pointer; }

    /* Dots */
    .msn-dots-container { position: absolute; bottom: 15px; left: 50%; transform: translateX(-50%); display: flex; gap: 6px; z-index: 10; }
    .msn-dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.4); transition: 0.3s; }
    .msn-dot.active { background: #fff; transform: scale(1.4); box-shadow: 0 0 5px rgba(255,255,255,0.8); }

    /* Badges */
    .badge-sos { background: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-law { background: #003366; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-real { background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-fek { background: #666; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-tech { background: #e67e22; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }

    /* Dark Mode */
    @media (prefers-color-scheme: dark) {
        html, body, [class*="css"] { background-color: #0e1117; color: #fafafa; }
        div[data-baseweb="input"] { background: #262730 !important; border: 1px solid #444 !important; }
        .tv-light-container { display: none !important; } .tv-dark-container { display: block !important; }
        .list-item { background: #262730 !important; border-bottom: 1px solid #444; }
        .list-title a { color: #fff !important; }
        .ticker-wrap { background: #262730 !important; border-color: #444; }
        .ticker-item { color: #ddd; }
        .grid-card { background: #262730 !important; border: none !important; }
        [data-testid="collapsedControl"], [data-testid="stSidebar"] button { color: white !important; }
        .header-container { background: #0e1117 !important; border-bottom: 3px solid #4da6ff; }
        .header-logo { color: #fff; }
        iframe[title="3rd party frame"] { filter: invert(1) hue-rotate(180deg) brightness(1.2); }
    }
    
    /* Misc */
    .ticker-wrap { background: white; border-top: 1px solid #eee; border-bottom: 1px solid #eee; height: 32px; overflow: hidden; }
    .ticker-item { padding-left: 100%; animation: ticker 80s linear infinite; font-size: 0.8rem; font-weight: 600; line-height:30px; }
    @keyframes ticker { 100% { transform: translate3d(-100%, 0, 0); } }
    .list-item { padding: 15px; border-bottom: 1px solid #eee; margin-bottom: 5px; transition: 0.2s; }
    .list-item:hover { border-left: 3px solid #003366; background: #fafafa; }
    .list-title a { color: #111 !important; text-decoration: none; font-weight: 600; font-size: 1.05rem; }
    .grid-card { background: white; border: 1px solid #f5f5f5; border-radius: 4px; overflow: hidden; height: 100%; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .article-meta { font-size: 0.75rem; color: #888; text-align: right; margin-top: auto; padding-top: 10px; border-top: 1px solid #f9f9f9; }
</style>
""", unsafe_allow_html=True)

# --- 3. THE BRAIN: INTELLIGENT CLASSIFICATION ---
# SOURCE MAP (Updated with Michanikos & Ethemis)
SOURCE_HINTS = {
    # ΜΗΧΑΝΙΚΟΙ & ΑΚΙΝΗΤΑ
    "ENG": ["pomida", "ypodomes", "b2green", "tee", "pedmede", "michanikos", "elinyae"],
    # ΝΟΜΙΚΑ & ΔΙΚΑΙΟΣΥΝΗ
    "LAW": ["dikastiko", "lawspot", "syntagma", "lawnet", "dsa", "ethemis"],
    # ΝΟΜΟΘΕΣΙΑ/ΦΕΚ
    "FEK": ["e-nomothesia", "taxheaven", "capital"]
}

def analyze_content(row):
    """
    PRIORITY BASED CLASSIFICATION ENGINE
    1. Reads Full Text (Title + Content).
    2. Identifies Subject Matter (Engineering vs Legal).
    3. Resolves Conflicts (Technical Legal -> Engineering).
    """
    title = str(row.get('title', '')).upper()
    content = str(row.get('content', '')).upper()
    source = str(row.get('source', '')).lower()
    full_text = title + " " + content
    
    tags = []

    # --- STEP 1: DETECT KEYWORDS ---
    
    # ENGINEERS / REAL ESTATE / TECHNICAL
    kw_eng = [
        'ΜΗΧΑΝΙΚ', 'ΕΡΓΑ', 'ΑΚΙΝΗΤ', 'REAL ESTATE', 'ΕΞΟΙΚΟΝΟΜΩ', 'ΑΝΑΚΑΙΝΙΖΩ', 'ΚΤΗΜΑΤΟΛΟΓΙΟ', 
        'ΑΥΘΑΙΡΕΤΑ', 'ΔΟΜΗΣΗ', 'ΥΠΟΔΟΜΕΣ', 'ΕΝΕΡΓΕΙΑ', 'ΠΕΑ', 'BUILDING', 'ΝΟΚ', 'ΟΙΚΟΔΟΜ', 
        'ΠΕΧΩΔΕ', 'ΥΠΕΝ', 'ΑΔΕΙΕΣ', 'ΚΑΤΑΣΚΕΥ', 'ΕΡΓΟΛΗΠΤ'
    ]
    
    # PURE LEGAL / JUSTICE
    kw_law = [
        'ΔΙΚΑΣΤ', 'ΑΡΕΙΟΣ ΠΑΓΟΣ', 'ΣΤΕ', 'ΔΙΚΗΓΟΡ', 'ΣΥΝΤΑΓΜΑ', 'ΔΙΚΗ', 'COURT', 'ΕΙΣΑΓΓΕΛ', 
        'ΑΓΩΓΗ', 'ΕΦΕΤΕΙΟ', 'ΠΡΩΤΟΔΙΚΕΙΟ', 'ΠΟΙΝΙΚ', 'ΑΣΤΙΚΟ', 'ΝΟΜΟΛΟΓΙΑ'
    ]
    
    # LEGISLATION (FEK)
    kw_fek = [
        'ΦΕΚ', 'ΝΟΜΟΣ', 'ΑΠΟΦΑΣΗ', 'ΕΓΚΥΚΛΙΟΣ', 'ΔΙΑΤΑΞΗ', 'ΤΡΟΠΟΛΟΓΙΑ', 'ΥΠΟΥΡΓΙΚΗ', 'ΠΡΟΕΔΡΙΚΟ ΔΙΑΤΑΓΜΑ'
    ]

    has_eng = any(k in full_text for k in kw_eng)
    has_law = any(k in full_text for k in kw_law)
    has_fek = any(k in full_text for k in kw_fek)
    
    # Check Source Hint
    src_type = "GEN"
    for cat, keywords in SOURCE_HINTS.items():
        if any(k in source for k in keywords):
            src_type = cat
            break

    # --- STEP 2: APPLY LOGIC & RESOLVE CONFLICTS ---

    # 1. FEK / LEGISLATION (The Library)
    # Adds to FEK tab regardless of subject
    if has_fek or src_type == "FEK":
        tags.append("FEK")

    # 2. ENGINEERS & REAL ESTATE (The Priority)
    # If source is ENG OR text has ENG keywords -> It goes to ENG.
    # This captures "Legal decisions about Building" into ENG.
    if src_type == "ENG" or has_eng:
        tags.append("ENG")

    # 3. LEGAL & JUSTICE (The Filter)
    # If source is LAW or has LAW keywords...
    if src_type == "LAW" or has_law:
        # CRITICAL: Only add to LAW tab if it is NOT about technical stuff.
        # If it has ENG keywords, we assume it's "Technical Law" and it's already in ENG tab.
        # We exclude it from pure "Justice" tab to keep that clean for lawyers/judges.
        if not has_eng:
            tags.append("LAW")
    
    # SOS Tagging
    if "SOS" in title or "ΠΡΟΘΕΣΜΙΑ" in title or "ΠΑΡΑΤΑΣΗ" in title:
        tags.append("SOS")

    if not tags: tags.append("GENERAL")
    
    return tags

# --- 4. DATA LOADING ---
def get_db_client():
    try: return gspread.service_account_from_dict(st.secrets["gcp_service_account"]).open("laws_database")
    except: return None

def load_data():
    sh = get_db_client()
    if not sh: return []
    try: 
        raw = sh.sheet1.get_all_records()
        df = pd.DataFrame(raw)
        
        # Cleanup Garbage Rows
        df = df[df['title'].str.lower() != 'title']
        
        # Date Filter (30 Days)
        df['datetime_obj'] = pd.to_datetime(df['last_update'], errors='coerce')
        cutoff = datetime.now() - timedelta(days=30)
        df = df[df['datetime_obj'] > cutoff]
        
        # Sort Newest First
        df = df.sort_values(by='datetime_obj', ascending=False)
        
        # --- APPLY INTELLIGENCE ---
        records = df.to_dict('records')
        for r in records:
            r['smart_tags'] = analyze_content(r)
            
        return records
    except: return []

# --- 5. HELPERS ---
IMAGE_POOL = {
    "ENG": ["https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=1200"],
    "LAW": ["https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=1200"],
    "GENERAL": ["https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200"]
}

def format_smart_date(date_str):
    try:
        dt = pd.to_datetime(date_str)
        now = datetime.now()
        if dt.date() == now.date():
            return f"{dt.strftime('%d/%m/%y')} - {dt.strftime('%H:%M')}"
        else:
            return dt.strftime("%d/%m/%y")
    except: return str(date_str)

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
        if "REAL ESTATE" in text or "ΑΚΙΝΗΤ" in text:
            badges_html += '<span class="badge-real">🏠 REAL ESTATE</span>'
        else:
            badges_html += '<span class="badge-tech">🏗️ ΤΕΧΝΙΚΟ</span>'
            
    if "LAW" in tags:
        badges_html += '<span class="badge-law">⚖️ ΔΙΚΑΙΟΣΥΝΗ</span>'
        
    if "FEK" in tags:
        badges_html += '<span class="badge-fek">📜 ΝΟΜΟΘΕΣΙΑ/ΦΕΚ</span>'
        
    return badges_html

def save_subscriber(email):
    sh = get_db_client()
    if not sh: return "ERROR"
    try: sh.worksheet("subscribers").append_row([email, str(datetime.now())]); return "OK"
    except: return "ERROR"

def reset_database(): return False

# --- 6. LOGIC & AUTO-PLAY ---
if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0
if 'last_run' not in st.session_state: st.session_state.last_run = time.time()

if time.time() - st.session_state.last_run > 6:
    st.session_state.slider_idx += 1
    st.session_state.last_run = time.time()
    st.rerun()

# --- 7. UI LAYOUT ---
with st.sidebar:
    nikas_url = "https://www.nikastechnical.gr"
    st.markdown(f"""
    <div class="brand-card">
        <div style="font-size:0.7rem; color:#666;">POWERED BY</div>
        <div style="font-size:2rem;">🏗️</div>
        <div style="font-size:0.8rem; margin-bottom:10px;">Construction Engineering</div>
        <a href="{nikas_url}" target="_blank" class="brand-btn">ΕΠΙΣΚΕΦΘΕΙΤΕ ΜΑΣ</a>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### 📬 Newsletter")
    email = st.text_input("Email", placeholder="me@example.com")
    if st.button("Εγγραφή"): save_subscriber(email)

# Header
st.markdown("""
<div class="header-container">
    <div style="font-size:0.8rem; color:#888; margin-bottom:5px;">Powered by NiKAS Technical</div>
    <div class="header-logo">🏛️ NomoTech</div>
    <div style="font-size:0.75rem; color:#666; margin-top:5px;">Intelligence Platform</div>
</div>
""", unsafe_allow_html=True)

raw_data = load_data()
if not raw_data: st.warning("⏳ Φόρτωση..."); st.stop()
df = pd.DataFrame(raw_data)

st.markdown('<div class="search-container">', unsafe_allow_html=True)
search_query = st.text_input("", placeholder="🔍 Αναζήτηση...")
st.markdown('</div>', unsafe_allow_html=True)

if search_query:
    q = search_query.upper()
    df = df[df.apply(lambda r: q in str(r['title']).upper() or q in str(r['content']).upper(), axis=1)]

# Ticker
if not df.empty:
    titles = "   +++   ".join([f"{r['title']}" for i, r in df.head(10).iterrows()])
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-item">{titles}</div></div>', unsafe_allow_html=True)

tabs = st.tabs(["ΚΟΡΥΦΑΙΑ", "ΜΗΧΑΝΙΚΟΙ & ΑΚΙΝΗΤΑ", "ΝΟΜΙΚΑ & ΔΙΚΑΙΟΣΥΝΗ", "ΝΟΜΟΘΕΣΙΑ/ΦΕΚ", "ΣΤΑΤΙΣΤΙΚΑ"])

# --- SLIDER FRAGMENT ---
@st.fragment(run_every=6)
def show_hero_slider(curr_df):
    if curr_df.empty: return
    st.session_state.slider_idx += 1
    slide_len = min(5, len(curr_df))
    idx = st.session_state.slider_idx % slide_len
    row = curr_df.iloc[idx]
    
    badges = render_badges(row)
    date_d = format_smart_date(row['last_update'])

    # Invisible Click Zones
    st.markdown('<div class="click-zone-container">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 6, 1]) 
    with c1:
        if st.button(" ", key="inv_prev"): st.session_state.slider_idx -= 2; st.rerun()
    with c3:
        if st.button(" ", key="inv_next"): st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    dots = "".join([f'<div class="msn-dot {"active" if i==idx else ""}"></div>' for i in range(slide_len)])
    st.markdown(f"""
    <div class="hero-wrapper">
        <img src="{get_image(row)}" class="hero-image">
        <div class="hero-overlay">
            <div style="margin-bottom:5px;">{badges}</div>
            <a href="{row['link']}" target="_blank" class="hero-title">{row['title']}</a>
            <div style="color:#ddd; margin-top:5px; font-size:0.8rem;">{date_d}</div>
        </div>
        <div class="msn-dots-container">{dots}</div>
    </div>
    """, unsafe_allow_html=True)

def render_tab(tab_name):
    # --- INTELLIGENT FILTERING ---
    if tab_name == "HOME": 
        curr = df
    elif tab_name == "ENG":
        curr = df[df['smart_tags'].apply(lambda x: 'ENG' in x)]
    elif tab_name == "LAW":
        # Only Pure Law (Excluding technical stuff which is already in ENG)
        curr = df[df['smart_tags'].apply(lambda x: 'LAW' in x and 'ENG' not in x)]
    elif tab_name == "FEK":
        curr = df[df['smart_tags'].apply(lambda x: 'FEK' in x)]
    else:
        curr = pd.DataFrame()

    if curr.empty: st.info("Δεν βρέθηκαν άρθρα."); return

    if tab_name == "HOME" and not search_query:
        # TradingView
        components.html("""
        <style> body{margin:0; overflow:hidden;} .light{display:block;} .dark{display:none;} @media(prefers-color-scheme:dark){.light{display:none;} .dark{display:block;}} </style>
        <div class="light"><div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>{"symbols":[{"proName":"ATHEX:GD","title":"ATHEX"},{"proName":"FOREXCOM:SPXUSD","title":"S&P 500"},{"proName":"FX_IDC:EURUSD","title":"EUR/USD"}],"colorTheme":"light","isTransparent":true,"displayMode":"compact","locale":"el"}</script></div></div>
        <div class="dark"><div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>{"symbols":[{"proName":"ATHEX:GD","title":"ATHEX"},{"proName":"FOREXCOM:SPXUSD","title":"S&P 500"},{"proName":"FX_IDC:EURUSD","title":"EUR/USD"}],"colorTheme":"dark","isTransparent":true,"displayMode":"compact","locale":"el"}</script></div></div>
        """, height=70)

        c_hero, c_list = st.columns([1.8, 1.2])
        with c_hero:
            show_hero_slider(curr) 
        
        with c_list:
            st.markdown("### Top Stories")
            for i, r in curr.head(5).iterrows():
                d = format_smart_date(r['last_update'])
                st.markdown(f"""<div class="list-item"><div class="list-title"><a href="{r['link']}" target="_blank">{r['title']}</a></div><div style="font-size:0.75rem; color:#888;">{d}</div></div>""", unsafe_allow_html=True)
        st.markdown("---")

    st.subheader("Ειδήσεις & Αποφάσεις")
    cols = st.columns(3)
    start = 5 if (tab_name == "HOME" and not search_query) else 0
    
    # Grid Iteration
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
