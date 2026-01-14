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

# --- 2. CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Segoe+UI:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    
    .header-container { background-color: #1e293b !important; padding: 20px 0 25px 0; border-bottom: 1px solid #334155; text-align: center; margin-bottom: 0px; border-radius: 0; }
    .header-logo { font-family: 'Merriweather', serif; font-size: 2.5rem; font-weight: 900; color: #ffffff !important; letter-spacing: -1px; line-height: 1.2; }
    .powered-text { font-size: 0.75rem; color: #94a3b8 !important; letter-spacing: 1px; }

    .ticker-container { width: 100%; overflow: hidden; background-color: #1e293b !important; border-top: 1px solid #334155; border-bottom: 1px solid #334155; white-space: nowrap; height: 42px; display: flex; align-items: center; margin-bottom: 20px; }
    .ticker-content { display: inline-block; padding-left: 100%; animation: ticker-scroll 80s linear infinite; }
    .ticker-text { font-family: 'Segoe UI', sans-serif; font-weight: 600; color: #f1f5f9 !important; font-size: 0.9rem; }
    @keyframes ticker-scroll { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    [data-testid="stSidebar"] { background-color: #111827 !important; border-right: 1px solid #374151; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff !important; font-weight: 500; }
    .sidebar-card { background: #1f2937; border: 1px solid #374151; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; }
    .sidebar-btn { display: block; width: 100%; background-color: #000000; color: white !important; text-decoration: none; padding: 10px 0; border-radius: 4px; font-size: 0.8rem; font-weight: 700; margin-top: 15px; transition: 0.2s; border: 1px solid #333; }
    
    div[data-baseweb="input"] { background-color: #0f172a !important; border: 1px solid #334155 !important; border-radius: 4px; }
    .search-container div[data-baseweb="input"] input { color: #e2e8f0 !important; caret-color: #3b82f6; font-weight: 500; }

    .hero-wrapper { position: relative; height: 412px; overflow: hidden; border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); z-index: 1; margin-bottom: 10px; }
    .hero-image { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.65); transition: 0.5s; }
    .hero-overlay { position: absolute; bottom: 0; left: 0; width: 100%; padding: 40px 20px 60px 20px; background: linear-gradient(to top, rgba(0,0,0,0.9), transparent); pointer-events: none; }
    .hero-title { font-family: 'Merriweather', serif; color: white !important; font-size: 1.8rem; font-weight: 700; line-height: 1.2; text-shadow: 0 2px 5px black; text-decoration: none; cursor: pointer; pointer-events: auto; }
    
    .msn-dots-container { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 8px; z-index: 10; pointer-events: none; }
    .msn-dot { width: 8px; height: 8px; border-radius: 50%; background-color: rgba(255, 255, 255, 0.4); transition: all 0.3s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }
    .msn-dot.active { background-color: #ffffff; transform: scale(1.3); box-shadow: 0 0 8px rgba(255, 255, 255, 0.8); }

    .mini-card { background: #111827; border: 1px solid #374151; border-radius: 8px; margin-bottom: 8px; height: 95px; display: flex; flex-direction: row; overflow: hidden; transition: transform 0.2s; }
    .mini-card:hover { transform: scale(1.02); border-color: #3b82f6; }
    .mini-text-content { flex: 1; padding: 10px 10px; display: flex; flex-direction: column; justify-content: flex-start; }
    
    .mini-meta-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
    .mini-source { font-size: 0.65rem; color: #9ca3af; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; line-height: 1; }
    
    .mini-ago { 
        font-size: 0.75rem; 
        color: #3b82f6; 
        font-weight: 700; 
        background: transparent !important; 
        border: none !important; 
        padding: 0 !important;
        text-align: right;
        min-width: 60px;
    }

    .mini-title a { color: #f3f4f6 !important; text-decoration: none; font-weight: 600; font-size: 0.78rem; line-height: 1.2; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
    .mini-image-box { width: 100px; height: 100%; background-size: cover; background-position: center; background-repeat: no-repeat; border-left: 1px solid #374151; flex-shrink: 0; }

    .grid-card { background: white; border: 1px solid #f5f5f5; border-radius: 4px; overflow: hidden; height: 100%; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display:flex; flex-direction:column; }
    .article-meta { font-size: 0.75rem; color: #888; text-align: right; margin-top: auto; padding-top: 10px; border-top: 1px solid #f9f9f9; }

    .badge-sos { background: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-law { background: #003366; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-real { background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-fek { background: #666; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }
    .badge-tech { background: #e67e22; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.65rem; font-weight: 700; margin-right: 5px; }

    /* --- RESPONSIVE VISIBILITY --- */
    @media (max-width: 900px) {
        .desktop-show { display: none !important; }
        .mobile-show { display: block !important; }
    }
    @media (min-width: 901px) {
        .mobile-show { display: none !important; }
        .desktop-show { display: block !important; }
    }
    
    @media (prefers-color-scheme: dark) {
        html, body, [class*="css"] { background-color: #0e1117 !important; color: #fafafa !important; }
        .grid-card { background: #262730 !important; border: none !important; }
        .article-meta { border-top-color: #334155 !important; color: #94a3b8 !important; }
        .header-container, .ticker-container { background-color: #1e293b !important; }
        [data-testid="collapsedControl"] { color: white !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC ---
def normalize_text(text):
    if not isinstance(text, str): return ""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

def analyze_content_deep(row):
    title = normalize_text(str(row.get('title', '')))
    content = normalize_text(str(row.get('content', '')))
    source = normalize_text(str(row.get('source', '')))
    ai_category = str(row.get('category', '')).upper()
    tags = set()

    trash_keywords = ["ολυμπιακος", "παναθηναικος", "αεκ", "παοκ", "αρης", "super league", "κυπελλο", "τζοκερ", "λοττο", "lotto", "joker", "κληρωση", "survivor", "masterchef", "eurovision", "ζωδια", "gossip"]
    if any(kw in title for kw in trash_keywords): return ["TRASH"]

    if any(s in source for s in ["michanikos", "ypodomes", "b2green", "pomida", "pedmede", "elinyae", "tee"]): tags.add("ENG")
    elif "ENG" in ai_category: tags.add("ENG")

    if any(s in source for s in ["dikastiko", "lawspot", "ethemis", "dsa", "lawnet", "syntagma"]): tags.add("LAW")
    elif "LAW" in ai_category: tags.add("LAW")
    
    if "e-nomothesia" in source or "taxheaven" in source: tags.add("FEK")
    elif "FEK" in ai_category: tags.add("FEK")

    if "sos" in title: tags.add("SOS")
    if not tags: tags.add("GENERAL")
    return list(tags)

def get_db_client():
    try: return gspread.service_account_from_dict(st.secrets["gcp_service_account"]).open("laws_database")
    except: return None

@st.cache_data(ttl=0) 
def load_data():
    sh = get_db_client()
    if not sh: return []
    try: 
        raw = sh.sheet1.get_all_records()
        df = pd.DataFrame(raw)
        df['datetime_obj'] = pd.to_datetime(df['last_update'], errors='coerce')
        cutoff = datetime.now() - timedelta(days=30)
        df = df[df['datetime_obj'] > cutoff]
        df = df.sort_values(by='datetime_obj', ascending=False)
        records = df.to_dict('records')
        clean_records = []
        for r in records: 
            tags = analyze_content_deep(r)
            if "TRASH" not in tags: 
                r['smart_tags'] = tags
                clean_records.append(r)
        return clean_records
    except: return []

def get_relative_time(dt):
    if pd.isnull(dt): return ""
    now = datetime.now()
    diff = now - dt
    if diff.days > 0: return f"{diff.days}ημ. πριν"
    seconds = diff.total_seconds()
    if seconds < 60: return "Τώρα"
    minutes = int(seconds // 60)
    if minutes < 60: return f"{minutes}λ. πριν"
    hours = int(minutes // 60)
    return f"{hours}ώ. πριν"

def format_smart_date(date_obj):
    if pd.isnull(date_obj): return ""
    now = datetime.now()
    if date_obj.date() == now.date(): return f"Σήμερα, {date_obj.strftime('%H:%M')}"
    return date_obj.strftime("%d/%m/%y")

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
    badges_html = ""
    if "SOS" in tags: badges_html += '<span class="badge-sos">🚨 SOS</span>'
    if "ENG" in tags: badges_html += '<span class="badge-tech">🏗️ ΤΕΧΝΙΚΟ</span>'
    if "LAW" in tags: badges_html += '<span class="badge-law">⚖️ ΝΟΜΙΚΟ</span>'
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

def reset_database():
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        sh = gc.open("laws_database")
        wks = sh.sheet1
        wks.clear()
        wks.append_row(["id", "source", "title", "content", "link", "last_update", "category", "image_url"])
        return True
    except: return False

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
    
    if st.button("🔄 ΕΛΕΓΧΟΣ ΓΙΑ ΝΕΑ (LIVE)", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
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
        else: st.warning("Μη έγκυρο email.")

st.markdown("""
<div class="header-container">
    <div class="powered-text" style="margin-bottom:5px;">Powered by NiKAS Technical</div>
    <div class="header-logo">🏛️ NomoTech</div>
    <div class="sub-text" style="margin-top:5px;">Intelligence Platform</div>
</div>
""", unsafe_allow_html=True)

raw_data = load_data()
if not raw_data: st.warning("⏳ Φόρτωση ή Κενή Βάση..."); st.stop()
df = pd.DataFrame(raw_data)

st.markdown('<div class="search-container">', unsafe_allow_html=True)
search_query = st.text_input("", placeholder="Αναζήτηση...", label_visibility="collapsed")
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

# --- 5s SLIDER + LIVE FLOW ---
@st.fragment(run_every=5) 
def render_live_flow(curr_df):
    if curr_df.empty: return
    if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0
    st.session_state.slider_idx += 1
    slide_len = min(12, len(curr_df)) 
    idx = st.session_state.slider_idx % slide_len
    row = curr_df.iloc[idx]
    badges = render_badges(row)
    
    dots_html = ""
    for i in range(min(10, slide_len)):
        active_cls = "active" if i == idx else ""
        dots_html += f'<div class="msn-dot {active_cls}"></div>'

    # --- HTML GENERATOR FOR FLOW ITEMS ---
    # ΔΙΟΡΘΩΣΗ: Αφαιρέσαμε τα κενά (indentation) για να μην το βλέπει το Markdown ως Code Block
    flow_html = '<h5>ΡΟΗ</h5>'
    for i, r in curr_df.head(6).iterrows():
        src_label = str(r['source']).upper()[:12]
        img_url = get_image(r)
        rel_time = get_relative_time(r['datetime_obj'])
        flow_html += f"""
<div class="mini-card">
<div class="mini-text-content">
<div class="mini-meta-row">
<div class="mini-source">{src_label}</div>
<div class="mini-ago">{rel_time}</div>
</div>
<div class="mini-title">
<a href="{r['link']}" target="_blank">{r['title']}</a>
</div>
</div>
<div class="mini-image-box" style="background-image: url('{img_url}');"></div>
</div>"""

    c_hero, c_right = st.columns([2.2, 1])
    with c_hero:
        # 1. HERO IMAGE (Always Visible)
        st.markdown(f"""
        <div class="hero-wrapper">
            <img src="{get_image(row)}" class="hero-image">
            <div class="hero-overlay">
                <div style="margin-bottom:5px;">{badges}</div>
                <a href="{row['link']}" target="_blank" class="hero-title">{row['title']}</a>
            </div>
            <div class="msn-dots-container">{dots_html}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. MOBILE FLOW (Visible ONLY on Mobile)
        st.markdown(f'<div class="mobile-show">{flow_html}</div>', unsafe_allow_html=True)

        # 3. BOTTOM GRID (Visible Everywhere)
        bottom_items = curr_df.iloc[6:12]
        if not bottom_items.empty:
            rows_b = (len(bottom_items) + 2) // 3 
            for i in range(rows_b):
                cols_b = st.columns(3) 
                for j, col_b in enumerate(cols_b):
                    idx_b = i * 3 + j
                    if idx_b < len(bottom_items):
                        r = bottom_items.iloc[idx_b]
                        src_label = str(r['source']).upper()[:12]
                        img_url = get_image(r)
                        rel_time = get_relative_time(r['datetime_obj'])
                        with col_b:
                            st.markdown(f"""
                            <div class="mini-card">
                                <div class="mini-text-content">
                                    <div class="mini-meta-row">
                                        <div class="mini-source">{src_label}</div>
                                        <div class="mini-ago">{rel_time}</div>
                                    </div>
                                    <div class="mini-title">
                                        <a href="{r['link']}" target="_blank">{r['title']}</a>
                                    </div>
                                </div>
                                <div class="mini-image-box" style="background-image: url('{img_url}');"></div>
                            </div>
                            """, unsafe_allow_html=True)

    with c_right:
        # 4. DESKTOP FLOW (Visible ONLY on Desktop)
        st.markdown(f'<div class="desktop-show">{flow_html}</div>', unsafe_allow_html=True)
        
    st.markdown("---")

def render_tab(tab_name):
    if tab_name == "HOME": curr = df
    elif tab_name == "ENG": curr = df[df['smart_tags'].apply(lambda x: 'ENG' in x)]
    elif tab_name == "LAW": curr = df[df['smart_tags'].apply(lambda x: 'LAW' in x)]
    elif tab_name == "FEK": curr = df[df['smart_tags'].apply(lambda x: 'FEK' in x)]
    else: curr = pd.DataFrame()

    if curr.empty: st.info("Δεν βρέθηκαν άρθρα."); return

    if tab_name == "HOME" and not search_query:
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
        render_live_flow(curr)

    st.subheader("Ειδήσεις & Αποφάσεις")
    cols = st.columns(3)
    start = 12 if (tab_name == "HOME" and not search_query) else 0 
    
    grid_items = curr.iloc[start:]
    if not grid_items.empty:
        rows = len(grid_items) // 3 + 1
        for i in range(rows):
            c_cols = st.columns(3)
            for j, col in enumerate(c_cols):
                idx = i * 3 + j
                if idx < len(grid_items):
                    r = grid_items.iloc[idx]
                    d = format_smart_date(r['datetime_obj'])
                    b = render_badges(r)
                    with col:
                        st.markdown('<div class="grid-card">', unsafe_allow_html=True)
                        st.image(get_image(r), use_column_width=True)
                        st.markdown(f"""<div style="padding:15px;">
                            <div style="font-weight:700; font-size:1.05rem; margin-bottom:5px;">{r['title']}</div>
                            <div style="margin-bottom:10px;">{b}</div>
                            </div>""", unsafe_allow_html=True)
                        
                        with st.expander("🤖 Επαγγελματική Ανάλυση"):
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
    st.subheader("📊 Στατιστικά Βάσης Δεδομένων")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Άρθρα ανά Πηγή**")
        source_counts = df['source'].value_counts()
        st.bar_chart(source_counts)
    with col2:
        st.markdown("**Ροή Ειδήσεων (Τελευταίες 30 ημέρες)**")
        date_counts = df.groupby(df['datetime_obj'].dt.date).size()
        st.bar_chart(date_counts)
    st.metric("Σύνολο Αρχειοθετημένων Άρθρων", len(df))
    if st.secrets.get("admin_password") and st.text_input("Pass", type="password") == st.secrets["admin_password"]:
        if st.button("🔴 RESET DATABASE"): 
            reset_database()
            st.cache_data.clear()
            st.rerun()
        st.dataframe(df)
