import streamlit as st
import pandas as pd
import gspread
import time
import unicodedata
import base64
from datetime import datetime, timedelta
import os
import streamlit.components.v1 as components

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTech | Enterprise",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS & STYLING (v6.4 - GHOST BUTTON TECHNIQUE) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@400;600;700&family=Roboto+Mono:wght@400;500;700&display=swap');
    
    /* 1. BLACKOUT GLOBAL */
    .stApp, html, body, [class*="css"] {{
        background-color: #000000 !important;
        font-family: 'Inter', sans-serif !important;
        color: #e0e0e0 !important;
    }}

    /* 2. SIDEBAR STYLING */
    section[data-testid="stSidebar"] {{
        background-color: #050505 !important;
        border-right: 1px solid #222 !important;
        width: 350px !important;
    }}
    
    /* === ΤΟ ΚΟΛΠΟ ΜΕ ΤΟ GHOST BUTTON === */
    /* Μετακινούμε το αληθινό κουμπί του Streamlit πάνω από το δικό μας και το κάνουμε αόρατο */
    [data-testid="collapsedControl"] {{
        display: block !important;
        position: fixed !important;
        top: 45px !important;      /* Το ύψος που είναι το δικό μας κουμπί */
        left: 15px !important;     /* Η θέση που είναι το δικό μας κουμπί */
        width: 50px !important;
        height: 40px !important;
        opacity: 0 !important;     /* ΑΟΡΑΤΟ */
        z-index: 100000 !important; /* Πάνω από όλα */
        cursor: pointer !important;
    }}

    /* Typography Sidebar */
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {{
        font-family: 'Inter', sans-serif !important;
        color: #fff !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        font-size: 1rem !important;
        margin-top: 20px !important;
    }}
    
    /* Inputs Sidebar */
    section[data-testid="stSidebar"] .stNumberInput input,
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] .stTextArea textarea {{
        background-color: #111 !important;
        color: #fff !important;
        border: 1px solid #333 !important;
        border-radius: 4px !important;
    }}

    /* Branding Card */
    .sidebar-brand {{
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 20px 0;
        border-bottom: 1px solid #222;
        margin-bottom: 20px;
    }}
    .sidebar-brand img {{
        width: 80px;
        height: 80px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid #333;
        margin-bottom: 10px;
    }}
    .sidebar-brand-title {{
        font-family: 'Playfair Display', serif;
        font-size: 1.2rem;
        color: #fff;
        letter-spacing: 1px;
    }}
    .sidebar-brand-sub {{
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 2px;
    }}

    /* 3. HIDE DEFAULTS */
    header[data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}
    [data-testid="stDecoration"] {{ display: none !important; }}

    /* 4. MARKET TICKER */
    .market-row {{
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 35px;
        background-color: #000;
        border-bottom: 1px solid #222;
        z-index: 9999;
        display: flex; align-items: center; overflow: hidden;
    }}
    .scrolling-wrapper {{ display: flex; white-space: nowrap; animation: scroll-text 75s linear infinite; }}
    @keyframes scroll-text {{ 0% {{ transform: translateX(0%); }} 100% {{ transform: translateX(-50%); }} }}
    .m-item {{ font-family: 'Roboto Mono', monospace; font-size: 0.75rem; color: #ccc; padding: 0 20px; display: inline-flex; align-items: center; gap: 5px; }}
    .m-val {{ color: #fff; font-weight: 700; }}
    .m-green {{ color: #4ade80; }} .m-red {{ color: #f87171; }}

    /* 5. CUSTOM BUTTONS */
    [data-testid="stHorizontalBlock"]:nth-of-type(1) button {{
        background-color: #000000 !important;
        border: 1px solid #000000 !important;
        color: white !important;
        border-radius: 4px !important;
        padding: 0 !important;
        margin: 0 !important;
        transition: none !important;
        box-shadow: none !important;
    }}

    /* HAMBURGER (Left) - VISUAL ONLY */
    [data-testid="stHorizontalBlock"]:nth-of-type(1) [data-testid="column"]:nth-of-type(1) button {{
        width: 40px !important;
        height: 38px !important;
        font-size: 1.6rem !important;
        line-height: 1 !important;
        color: #ffffff !important;
        display: flex; align-items: center; justify-content: center;
        pointer-events: none !important; /* Δεν πατιέται το ίδιο, πατιέται το "φάντασμα" από πάνω */
    }}
    
    /* USER BUTTON (Right) */
    [data-testid="stHorizontalBlock"]:nth-of-type(1) [data-testid="column"]:nth-of-type(3) button {{
        height: 28px !important;
        min-height: 28px !important;
        width: 100% !important;
        min-width: 100px !important;
        margin-top: 5px !important;
        background-image: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    [data-testid="stHorizontalBlock"]:nth-of-type(1) [data-testid="column"]:nth-of-type(3) button p {{
        font-family: 'Inter', sans-serif !important;
        font-size: 10px !important;
        font-weight: 300 !important;
        letter-spacing: 1px !important;
        color: #ffffff !important;
        text-transform: none !important;
        white-space: nowrap !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    /* NO HOVER */
    [data-testid="stHorizontalBlock"]:nth-of-type(1) button:hover {{
        background-color: #000000 !important;
        border-color: #000000 !important;
        color: #ffffff !important;
    }}
    [data-testid="stHorizontalBlock"]:nth-of-type(1) button:hover * {{ color: #ffffff !important; }}
    [data-testid="stHorizontalBlock"]:nth-of-type(1) button:active,
    [data-testid="stHorizontalBlock"]:nth-of-type(1) button:focus {{
        background-color: #000000 !important;
        border-color: #000000 !important;
        color: #ffffff !important;
        box-shadow: none !important;
    }}

    /* 6. DATE DISPLAY */
    .date-container {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        margin-bottom: -38px;
        position: relative;
        z-index: 1;
        padding-right: 5px;
        height: 40px;
    }}
    .date-text {{
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        color: #888;
        font-weight: 400;
        letter-spacing: 0.5px;
        padding-top: 12px; 
    }}

    /* 7. GENERAL UI */
    .block-container {{ padding-top: 4px !important; }}
    [data-testid="stHorizontalBlock"]:nth-of-type(1) {{
        align-items: center !important;
        gap: 0 !important;
        padding-top: 10px !important;
    }}
    .header-area {{ margin-top: 15px; padding-bottom: 10px; margin-bottom: 20px; display: flex; align-items: center; gap: 15px; }}
    .logo-img-custom {{ width: 90px; height: auto; border-radius: 0px; }}
    .brand-title {{ font-family: 'Playfair Display', serif !important; font-size: 3rem; line-height: 1; color: white; letter-spacing: 1px; }}
    .brand-sub {{ font-family: 'Inter', sans-serif !important; font-size: 0.8rem; color: #888; margin-top: 5px; letter-spacing: 0.5px; }}

    div[data-baseweb="input"] {{ background-color: #000 !important; border: 1px solid #333 !important; border-radius: 2px !important; height: 35px !important; max-width: 250px !important; }}
    .stTextInput input {{ color: #ccc !important; font-size: 0.85rem !important; }}

    .news-card {{ margin-bottom: 25px; border: 1px solid transparent; padding: 10px; transition: border 0.3s; }}
    .news-card:hover {{ border: 1px solid #222; background: #050505; }}
    .news-thumb {{ width: 100%; height: 160px; object-fit: cover; margin-bottom: 8px; filter: grayscale(20%); border-radius: 2px; border: 1px solid #222; }}
    .news-title {{ font-size: 1rem; font-weight: 700; color: white; line-height: 1.4; text-decoration: none; display: block;}}
    
    .bg-eng {{ background: #ea580c; color: white; }} .bg-law {{ background: #1e3a8a; color: white; }} .bg-fek {{ background: #e9e9d0; color: #000; }} .bg-sos {{ background: #dc2626; color: white; }} .bg-gen {{ background: #9ca3af; color: black; }}
    .meta-tag {{ font-family: 'Roboto Mono', monospace; font-size: 0.6rem; padding: 2px 6px; font-weight: 700; margin-right: 5px; display: inline-block; border-radius: 2px; }}
    
    button[data-baseweb="tab"] {{ font-family: 'Inter', sans-serif; font-size: 0.8rem; font-weight: 600; color: #777; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: #fff; border-bottom-color: #fff; }}
    
    .hero-container {{ position: relative; height: 450px; background: #000; overflow: hidden; border-radius: 2px; border: 1px solid #222; }}
    .hero-img {{ width: 100%; height: 100%; object-fit: cover; opacity: 0.85; }}
    .hero-text-box {{ position: absolute; bottom: 0; left: 0; width: 100%; padding: 30px; background: linear-gradient(to top, black, transparent); }}
    .slider-dots {{ position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%); display: flex; gap: 5px; }}
    .dot {{ width: 6px; height: 6px; background-color: #444; border-radius: 50%; display: inline-block; }}
    .dot.active {{ background-color: #fff; }}

    .side-row {{ height: 112px; border-bottom: 1px solid #222; display: flex; align-items: flex-start; gap: 12px; padding: 10px 5px; }}
    .side-thumb {{ width: 80px; height: 70px; object-fit: cover; filter: grayscale(20%); border-radius: 2px; margin-top: 5px; flex-shrink: 0; border: 1px solid #222; }}
    .side-content {{ display: flex; flex-direction: column; justify-content: space-between; height: 100%; width: 100%; }}
    a.side-link-title {{ font-family: 'Inter', sans-serif !important; font-size: 0.85rem !important; font-weight: 600 !important; color: #e0e0e0 !important; text-decoration: none !important; line-height: 1.3 !important; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 5px; }}
    a.side-link-title:hover {{ color: #fff !important; }}
    .side-meta-date {{ font-family: 'Roboto Mono', monospace; font-size: 0.65rem; color: #888; margin-top: auto; letter-spacing: -0.5px; }}
</style>
""", unsafe_allow_html=True)

# --- 3. HELPERS & LOGIC ---

def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f: data = f.read()
        return base64.b64encode(data).decode()
    except: return None

main_logo_b64 = get_image_as_base64("LOGONOMO.JPG")
nikas_logo_b64 = get_image_as_base64("logo.jpg") 

def get_greek_date():
    days = {
        "Monday": "Δευτέρα", "Tuesday": "Τρίτη", "Wednesday": "Τετάρτη",
        "Thursday": "Πέμπτη", "Friday": "Παρασκευή", "Saturday": "Σάββατο", "Sunday": "Κυριακή"
    }
    months = {
        "January": "Ιανουαρίου", "February": "Φεβρουαρίου", "March": "Μαρτίου",
        "April": "Απριλίου", "May": "Μαΐου", "June": "Ιουνίου",
        "July": "Ιουλίου", "August": "Αυγούστου", "September": "Σεπτεμβρίου",
        "October": "Οκτωβρίου", "November": "Νοεμβρίου", "December": "Δεκεμβρίου"
    }
    
    now = datetime.utcnow() + timedelta(hours=2)
    day_name = days[now.strftime("%A")]
    day_num = now.day
    month_name = months[now.strftime("%B")]
    year = now.year
    time_str = now.strftime("%H:%M")
    
    return f"{day_name} {day_num} {month_name} {year} | {time_str}"

def normalize_text(text):
    if not isinstance(text, str): return ""
    return "".join([c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)]).lower()

def analyze_content_deep(row):
    title = normalize_text(str(row.get('title', '')))
    ai_category = str(row.get('category', '')).upper()
    content_body = str(row.get('content', '')).upper() 
    
    tags = set()
    trash_keywords = ["super league", "κυπελλο", "τζοκερ", "λοττο", "lotto", "joker", "survivor", "masterchef", "eurovision", "ζωδια", "gossip"]
    if any(kw in title for kw in trash_keywords): return ["TRASH"]

    if "ENG" in ai_category or "ENG" in content_body: tags.add("ENG")
    if "LAW" in ai_category or "LAW" in content_body: tags.add("LAW")
    if "FEK" in ai_category or "FEK" in content_body: tags.add("FEK")
    
    eng_keywords = ["μηχανικ", "ακινητ", "εργα", "αυθαιρετ", "κτιρι", "ενεργειακ", "κτηματολογ", "πολεοδομ", "real estate", "κατασκευ", "νοκ", "γοκ", "τεε", "άδεια", "οικοδομ"]
    if any(kw in title for kw in eng_keywords): tags.add("ENG")

    law_keywords = ["δικαστ", "δικηγορ", "συμβολαιογραφ", "αρεο", "παγο", "στε", "εισαγγελ", "ποινικ", "αστικ", "δικη", "νομικ", "δικαιο"]
    if any(kw in title for kw in law_keywords): tags.add("LAW")
    
    leg_keywords = ["φεκ", "νομος", "κυα", "εγκυκλιος", "τροπολογια", "αποφαση"]
    if any(kw in title for kw in leg_keywords): tags.add("FEK")

    if "SOS" in title.upper(): tags.add("SOS")
    if not tags: tags.add("GENERAL")
    return list(tags)

@st.cache_data(ttl=600)
def load_data():
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        raw = gc.open("laws_database").sheet1.get_all_records()
        df = pd.DataFrame(raw)
        df['datetime_obj'] = pd.to_datetime(df['last_update'], errors='coerce')
        df = df.sort_values(by='datetime_obj', ascending=False)
        records = df.to_dict('records')
        clean_records = []
        for r in records: 
            tags = analyze_content_deep(r)
            if "TRASH" not in tags: 
                r['smart_tags'] = tags
                clean_records.append(r)
        return pd.DataFrame(clean_records)
    except: return pd.DataFrame()

def get_img(row):
    i = str(row.get('image_url', '')).strip()
    if not i.startswith('http'):
        tags = row.get('smart_tags', [])
        if "ENG" in tags: return "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=1200"
        if "LAW" in tags: return "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=1200"
        return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200"
    return i

def get_formatted_time(dt):
    if pd.isnull(dt): return ""
    now = datetime.utcnow() + timedelta(hours=2)
    diff = now - dt
    if now.date() == dt.date():
        minutes = int(diff.total_seconds() // 60)
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h{mins}m ago" if hours > 0 else f"{mins}m ago"
    else:
        return dt.strftime("%d/%m/%y")

def get_tags_html(row):
    tags = row.get('smart_tags', [])
    html = ""
    if "ENG" in tags: html += '<span class="meta-tag bg-eng">ENG</span>'
    if "LAW" in tags: html += '<span class="meta-tag bg-law">LAW</span>'
    if "FEK" in tags: html += '<span class="meta-tag bg-fek">FEK</span>'
    if "SOS" in tags: html += '<span class="meta-tag bg-sos">SOS</span>'
    if not html: html = '<span class="meta-tag bg-gen">GEN</span>'
    return html

# --- 4. THE ULTIMATE SIDEBAR (TOOLBOX) ---
with st.sidebar:
    # A. BRANDING CARD
    logo_src = f"data:image/jpeg;base64,{nikas_logo_b64}" if nikas_logo_b64 else "https://via.placeholder.com/80?text=NiKAS"
    st.markdown(f"""
    <div class="sidebar-brand">
        <img src="{logo_src}">
        <div class="sidebar-brand-title">NiKAS Technical</div>
        <div class="sidebar-brand-sub">ENGINEERING & CONSULTING</div>
    </div>
    """, unsafe_allow_html=True)
    
    # B. WEATHER WIDGET (Meteoblue iFrame Fix)
    # Χρησιμοποιούμε μια έτοιμη λύση iframe που λειτουργεί παντού
    # Βάλαμε background-color στο iframe container για να μην είναι μαύρο-σε-μαύρο αν αργήσει
    st.markdown("### 🌤️ Live Καιρός (Αθήνα)")
    st.markdown("""
        <div style="background-color:#1e1e1e; border-radius:4px; overflow:hidden;">
            <iframe src="https://www.meteoblue.com/en/weather/widget/three/athens_greece_264371?geoloc=fixed&days=4&tempunit=CELSIUS&windunit=KILOMETER_PER_HOUR&layout=dark" 
            frameborder="0" scrolling="NO" allowtransparency="true" 
            sandbox="allow-same-origin allow-scripts allow-popups allow-popups-to-escape-sandbox" 
            style="width: 100%; height: 240px"></iframe>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # C. QUICK TOOLS
    st.markdown("### 🧮 Quick Calculator (ΦΠΑ)")
    amount = st.number_input("Καθαρό Ποσό (€)", min_value=0.0, step=10.0)
    if amount > 0:
        fpa = amount * 0.24
        total = amount + fpa
        st.info(f"ΦΠΑ (24%): €{fpa:.2f}")
        st.success(f"**Τελικό: €{total:.2f}**")
        
    st.markdown("---")
    
    st.markdown("### 📅 Ημερολόγιο")
    st.date_input("Επιλογή Ημ/νίας", label_visibility="collapsed")
    
    st.markdown("---")
    
    st.markdown("### 📝 Notes")
    st.text_area("Σημειώσεις...", height=100, label_visibility="collapsed")
    
    st.caption("© 2026 NiKAS Technical")


# --- 5. TOP SECTION (UI) ---

# A. MARKET TICKER
items = ""
data = [("ATHEX","1,425","+0.4%","u"),("S&P500","5,110","+0.2%","u"),("EUR/USD","1.08","+0.0%","u"),("BTC","68K","+2.5%","u"),("GOLD","2,155","+0.9%","u")]
for n,v,c,d in data:
    col = "m-green" if d=="u" else "m-red"
    arr = "▲" if d=="u" else "▼"
    items += f'<div class="m-item"><span>{n}</span><span class="m-val">{v}</span><span class="{col}">{arr}{c}</span></div>'
st.markdown(f"""<div class="market-row"><div class="scrolling-wrapper">{items*10}</div></div>""", unsafe_allow_html=True)

# B. NAV BAR
c_nav_l, c_nav_m, c_nav_r = st.columns([1, 20, 1.7])

with c_nav_l:
    # Το κουμπί υπάρχει ΜΟΝΟ για εμφάνιση.
    # Το κλικ το "κλέβει" το αόρατο κουμπί του Streamlit που μετακινήσαμε από πάνω του με CSS.
    st.button("☰", key="nav_menu")

with c_nav_r:
    st.button("Sign in/up", key="nav_user", help="Account") 

# --- 6. MAIN CONTENT ---
c1, c2 = st.columns([1.5, 0.3])

logo_html = f'<img src="data:image/jpeg;base64,{main_logo_b64}" class="logo-img-custom">' if main_logo_b64 else '<div style="color:red;">LOGO</div>'

with c1:
    st.markdown(f"""
    <div class="header-area">
        {logo_html}
        <div style="display:flex; flex-direction:column; justify-content:center;">
            <div class="brand-title">NomoTech</div>
            <div class="brand-sub">Powered by NiKAS Technical</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("<div style='height:45px'></div>", unsafe_allow_html=True)
    q = st.text_input("Search", placeholder="Search", label_visibility="collapsed")

df = load_data()
if df.empty: 
    st.warning("Φόρτωση βάσης δεδομένων...")
    st.stop()

# Search Logic
if q:
    w = normalize_text(q).split()
    df = df[df.apply(lambda r: all(x in normalize_text(str(r['title'])+str(r['content'])) for x in w), axis=1)]

# Latest News Ticker
if not df.empty:
    txt = "   ///   ".join([f"{r['title']}" for i,r in df.head(10).iterrows()]) * 3
    st.markdown(f"""
    <div style="width:100%; overflow:hidden; background:#080808; border-top:1px solid #333; border-bottom:1px solid #333; height:40px; display:flex; align-items:center; margin-bottom:25px;">
        <div style="white-space:nowrap; animation: scroll-text 60s linear infinite;">
            <span style="font-family:'Inter'; font-weight:500; color:#e0e0e0; font-size:0.9rem;">{txt}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- DATE DISPLAY INJECTION ---
date_str = get_greek_date()
st.markdown(f'<div class="date-container"><span class="date-text">{date_str}</span></div>', unsafe_allow_html=True)

tabs = st.tabs(["LATEST", "ΜΗΧΑΝΙΚΟΙ&ΑΚΙΝΗΤΑ", "ΝΟΜΙΚΑ&ΔΙΚΑΙΟΣΥΝΗ", "ΦΕΚ/ΝΟΜΟΘΕΣΙΑ", "ANALYTICS"])

@st.fragment(run_every=5.0)
def render_hero(dataset):
    if dataset.empty: return
    if 'idx' not in st.session_state: st.session_state.idx = 0
    st.session_state.idx += 1
    
    current_idx = st.session_state.idx % len(dataset)
    r = dataset.iloc[current_idx]
    
    tags_html = get_tags_html(r)
    
    safe_len = min(len(dataset), 10)
    dots_html = ""
    for i in range(safe_len):
        active_class = "active" if i == (current_idx % safe_len) else ""
        dots_html += f'<span class="dot {active_class}"></span>'

    st.markdown(f"""
    <div class="hero-container">
        <img src="{get_img(r)}" class="hero-img">
        <div class="hero-text-box">
            <div style="margin-bottom:8px;">{tags_html}</div>
            <a href="{r['link']}" target="_blank" style="color:white; font-size:1.6rem; font-weight:700; text-decoration:none; line-height:1.2;">{r['title']}</a>
        </div>
        <div class="slider-dots">{dots_html}</div>
    </div>
    """, unsafe_allow_html=True)

def render_newsroom(dataset, is_home=False):
    if dataset.empty: st.info("No data found."); return
    start = 0
    if is_home and not q:
        feat = dataset.head(13)
        side = dataset.iloc[0:4]
        bot = dataset.iloc[4:13]
        start = 13
        
        c_hero, c_list = st.columns([2.3, 1])
        with c_hero: render_hero(feat)
        with c_list:
            st.markdown('<div style="border-bottom:2px solid white; color:white; font-weight:700; margin-bottom:0px;">LATEST UPDATES</div>', unsafe_allow_html=True)
            for _, r in side.iterrows():
                st.markdown(f"""
                <div class="side-row">
                    <img src="{get_img(r)}" class="side-thumb">
                    <div class="side-content">
                        <a href="{r['link']}" target="_blank" class="side-link-title">{r['title']}</a>
                        <div class="side-meta-date">{get_formatted_time(r['datetime_obj'])}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        if not bot.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            for i in range((len(bot)//3)+1):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    idx = i*3+j
                    if idx < len(bot):
                        r = bot.iloc[idx]
                        with col:
                             st.markdown(f"""
                             <div class="side-row" style="border-top:1px solid #222;">
                                <img src="{get_img(r)}" class="side-thumb">
                                <div class="side-content">
                                    <a href="{r['link']}" target="_blank" class="side-link-title">{r['title']}</a>
                                    <div class="side-meta-date">{get_formatted_time(r['datetime_obj'])}</div>
                                </div>
                             </div>
                             """, unsafe_allow_html=True)
        st.markdown('<div style="border-bottom:2px solid #333; color:white; font-weight:800; font-size:1.4rem; margin:40px 0 20px 0;">ARCHIVE</div>', unsafe_allow_html=True)

    grid = dataset.iloc[start:]
    if grid.empty and not is_home: st.write("No more news."); return

    for i in range((len(grid)//3)+1):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = i*3+j
            if idx < len(grid):
                r = grid.iloc[idx]
                tags_html = get_tags_html(r)
                with col:
                    st.markdown(f"""<div class="news-card"><a href="{r['link']}" target="_blank" style="text-decoration:none;"><img src="{get_img(r)}" class="news-thumb"><div style="margin-bottom:5px;">{tags_html}</div><span class="news-title">{r['title']}</span><div style="font-size:0.7rem; color:#666; margin-top:5px; border-top:1px solid #222; padding-top:5px;">{str(r['source']).upper()[:10]} • {get_formatted_time(r['datetime_obj'])}</div></a></div>""", unsafe_allow_html=True)

with tabs[0]: render_newsroom(df, is_home=True)
with tabs[1]: render_newsroom(df[df['smart_tags'].apply(lambda x: 'ENG' in x)])
with tabs[2]: render_newsroom(df[df['smart_tags'].apply(lambda x: 'LAW' in x)])
with tabs[3]: render_newsroom(df[df['smart_tags'].apply(lambda x: 'FEK' in x)])
with tabs[4]: 
    st.markdown("### 📊 Στατιστικά")
    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(df['source'].value_counts())
    with col2:
        st.write(f"Total Articles: {len(df)}")
        if st.secrets.get("admin_password") and st.text_input("Password", type="password") == st.secrets["admin_password"]:
            st.dataframe(df)
