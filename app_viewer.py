import streamlit as st
import pandas as pd
import gspread
import time
import base64
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTechi",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS (THE FINAL CORRECTED THEME) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Segoe+UI:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; background-color: #ffffff; color: #222; }
    
    /* Search Bar */
    div[data-baseweb="input"] { background-color: #003366 !important; border: 1px solid #004080; border-radius: 4px; }
    div[data-baseweb="input"] input { color: white !important; caret-color: white; font-weight: 500; }
    div[data-baseweb="input"] input::placeholder { color: #b3cce6 !important; }
    
    /* Sidebar */
    [data-testid="collapsedControl"], [data-testid="stSidebar"] button { color: #000 !important; }

    /* --- HERO SLIDER --- */
    .hero-wrapper { 
        position: relative; height: 450px; overflow: hidden; 
        border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        z-index: 1; margin-top: -50px; /* Pull image up to cover any gap */
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

    /* --- NAV BUTTONS CONTAINER (The Fix) --- */
    /* This container floats ON TOP of the image space */
    .nav-overlay-container {
        position: relative;
        height: 0px !important;
        width: 100%;
        z-index: 999;
        pointer-events: none; /* Let clicks pass through middle */
    }

    /* LEFT BUTTON POSITIONING */
    div[data-testid="column"]:nth-of-type(1) .nav-btn button {
        position: absolute;
        top: 200px !important; /* Vertically centered (approx 450/2) */
        left: 10px !important; /* Left Edge */
    }

    /* RIGHT BUTTON POSITIONING */
    div[data-testid="column"]:nth-of-type(3) .nav-btn button {
        position: absolute;
        top: 200px !important; /* Vertically centered */
        right: 10px !important; /* Right Edge */
    }

    /* SHARED BUTTON STYLING (Glass Effect) */
    .nav-btn button {
        pointer-events: auto !important;
        background-color: rgba(255, 255, 255, 0.15) !important;
        backdrop-filter: blur(4px);
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 8px !important;
        width: 40px !important; height: 60px !important; /* Rectangular vertical */
        display: flex; align-items: center; justify-content: center;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    .nav-btn button:hover {
        background-color: rgba(255, 255, 255, 0.9) !important;
        color: #000 !important;
        transform: scale(1.1);
    }
    .nav-btn button p { font-size: 24px !important; line-height: 1; margin-top: -4px; }

    /* --- DOTS --- */
    .msn-dots-container {
        position: absolute; bottom: 15px; left: 50%; transform: translateX(-50%); display: flex; gap: 6px; z-index: 10;
    }
    .msn-dot {
        width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.4); transition: 0.3s;
    }
    .msn-dot.active { background: #fff; transform: scale(1.4); box-shadow: 0 0 5px rgba(255,255,255,0.8); }

    /* --- TICKER --- */
    .ticker-wrap { background-color: #ffffff; border-top: 1px solid #f5f5f5; border-bottom: 1px solid #f5f5f5; height: 32px; overflow: hidden; white-space: nowrap; display: flex; align-items: center; margin-bottom: 20px; }
    .ticker-item { display: inline-block; padding-left: 100%; animation: ticker 80s linear infinite; font-size: 0.8rem; color: #333; font-weight: 600; }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    /* Standard Elements */
    .list-item { padding: 15px; border-bottom: 1px solid #eee; margin-bottom: 5px; transition: 0.2s; }
    .list-title a { color: #111 !important; text-decoration: none; font-weight: 600; font-size: 1.05rem; }
    .brand-card { background: #ffffff; border: 1px solid #f0f0f0; border-radius: 4px; padding: 20px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .header-container { background: white; padding: 0 0 20px 0; border-bottom: 2px solid #003366; text-align: center; margin-bottom: 20px; }

    /* Badges */
    .badge-sos { background: #dc3545; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.6rem; font-weight: bold; margin-right: 5px; }
    .badge-law { background: #003366; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.6rem; font-weight: bold; margin-right: 5px; }
    .badge-real { background: #28a745; color: white; padding: 1px 4px; border-radius: 2px; font-size: 0.6rem; font-weight: bold; margin-right: 5px; }

    /* Dark Mode */
    @media (prefers-color-scheme: dark) {
        html, body, [class*="css"] { background-color: #0e1117; color: #fafafa; }
        div[data-baseweb="input"] { background: #262730 !important; border: 1px solid #444 !important; }
        .tv-light-container { display: none !important; } .tv-dark-container { display: block !important; }
        .list-item { background: #262730 !important; border-bottom: 1px solid #444; }
        .list-title a { color: #fff !important; }
        .ticker-wrap { background: #262730 !important; border-color: #444; }
        .ticker-item { color: #ddd; }
        [data-testid="collapsedControl"], [data-testid="stSidebar"] button { color: white !important; }
        .brand-card { background: #262730 !important; border: none !important; }
        .brand-card img { filter: invert(1); }
        .header-container { background: #0e1117 !important; border-bottom: 3px solid #4da6ff; }
        iframe[title="3rd party frame"] { filter: invert(1) hue-rotate(180deg) brightness(1.2); }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC & DATA ---
if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0
if 'last_run' not in st.session_state: st.session_state.last_run = time.time()

# 6 Second Auto Timer
if time.time() - st.session_state.last_run > 6:
    st.session_state.slider_idx += 1
    st.session_state.last_run = time.time()
    st.rerun()

IMAGE_POOL = ["https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=1200", "https://images.unsplash.com/photo-1503387762-592deb58ef4e?q=80&w=1200"]

def get_db_client():
    try: return gspread.service_account_from_dict(st.secrets["gcp_service_account"]).open("laws_database")
    except: return None

def load_data():
    sh = get_db_client()
    if not sh: return []
    try: 
        raw = sh.sheet1.get_all_records()
        df = pd.DataFrame(raw)
        df = df[df['title'].str.lower() != 'title'] # Cleanup
        return df.iloc[::-1].to_dict('records') # Newest first
    except: return []

def get_image(row):
    return row.get('image_url') if str(row.get('image_url')).startswith('http') else IMAGE_POOL[0]

def render_badges(category_str):
    badges_html = ""
    if "SOS" in category_str: badges_html += '<span class="badge-sos">🚨 SOS</span>'
    if "JUDICIAL" in category_str: badges_html += '<span class="badge-law">⚖️ ΔΙΚΑΣΤΗΡΙΑ</span>'
    if "LEGAL" in category_str: badges_html += '<span class="badge-law">⚖️ ΝΟΜΙΚΟ</span>'
    if "REAL_ESTATE" in category_str: badges_html += '<span class="badge-real">🏠 REAL ESTATE</span>'
    if "LEGISLATION" in category_str: badges_html += '<span class="badge-sos">📜 ΝΟΜΟΘΕΣΙΑ</span>'
    return badges_html

def save_subscriber(email):
    sh = get_db_client()
    if not sh: return "DB_ERROR"
    try: sh.worksheet("subscribers").append_row([email, str(datetime.now())]); return "OK"
    except: return "WRITE_ERROR"

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
        with open(file_path, "rb") as f: data = f.read()
        return base64.b64encode(data).decode()
    except: return None

def normalize_greek(text):
    if not isinstance(text, str): return ""
    return text.lower()

# --- 4. LAYOUT ---
with st.sidebar:
    st.markdown('<div class="brand-card"><div style="font-size:0.7rem; color:#666;">POWERED BY</div><div style="font-size:2rem;">🏗️</div><div style="font-size:0.8rem;">Construction Engineering</div></div>', unsafe_allow_html=True)
    st.markdown("### 📬 Newsletter")
    email = st.text_input("Email", placeholder="me@example.com")
    if st.button("Εγγραφή"): save_subscriber(email)

st.markdown("""
<div class="header-container">
    <div style="font-size:0.75rem; color:#666; margin-bottom:5px;">Intelligence Platform</div>
    <div style="font-size:3rem; font-weight:900; color:#003366; font-family:'Merriweather', serif;">🏛️ NomoTechi</div>
    <div style="font-size:0.8rem; color:#888;">Powered by NiKAS Technical</div>
</div>
""", unsafe_allow_html=True)

raw_data = load_data()
if not raw_data: st.warning("⏳ Φόρτωση..."); st.stop()
df = pd.DataFrame(raw_data)

st.markdown('<div class="search-container">', unsafe_allow_html=True)
search_query = st.text_input("", placeholder="🔍 Αναζήτηση...")
st.markdown('</div>', unsafe_allow_html=True)

# Ticker
if not df.empty:
    titles = "   +++   ".join([f"{r['title']}" for i, r in df.head(10).iterrows()])
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-item">{titles}</div></div>', unsafe_allow_html=True)

tabs = st.tabs(["ΚΟΡΥΦΑΙΑ", "ΜΗΧΑΝΙΚΟΙ", "ΝΟΜΙΚΑ", "ΦΕΚ", "STATS"])

# --- THE SLIDER FRAGMENT (AUTOPLAY + GREEN ZONE NAV) ---
@st.fragment(run_every=6)
def show_hero_slider(curr_df):
    if curr_df.empty: return
    
    st.session_state.slider_idx += 1
    slide_len = min(5, len(curr_df))
    idx = st.session_state.slider_idx % slide_len
    row = curr_df.iloc[idx]
    hero_badges = render_badges(row['category'])

    # --- NAVIGATION BUTTONS (The "Green Zone" Fix) ---
    # We place these in a zero-height container BEFORE the image
    st.markdown('<div class="nav-overlay-container">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 10, 1])
    with c1:
        st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
        if st.button("❮", key="nav_prev"): 
            st.session_state.slider_idx -= 2 
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
        if st.button("❯", key="nav_next"): 
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- IMAGE & DOTS ---
    dots = "".join([f'<div class="msn-dot {"active" if i==idx else ""}"></div>' for i in range(slide_len)])
    st.markdown(f"""
    <div class="hero-wrapper">
        <img src="{get_image(row)}" class="hero-image">
        <div class="hero-overlay">
            <div style="margin-bottom:5px;">{hero_badges}</div>
            <a href="{row['link']}" target="_blank" class="hero-title">{row['title']}</a>
            <div style="color:#ddd; margin-top:5px; font-size:0.8rem;">{row['last_update']}</div>
        </div>
        <div class="msn-dots-container">{dots}</div>
    </div>
    """, unsafe_allow_html=True)

def render_tab(tab_name):
    if tab_name == "HOME": curr = df
    else: curr = df[df['category'].str.contains(tab_name, case=False, na=False)]
    
    if curr.empty: st.info("No articles."); return

    if tab_name == "HOME" and not search_query:
        # Widget
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
                st.markdown(f"""<div class="list-item"><div class="list-title"><a href="{r['link']}" target="_blank">{r['title']}</a></div><div style="font-size:0.75rem; color:#888;">{r['last_update']}</div></div>""", unsafe_allow_html=True)
        st.markdown("---")

    st.subheader("Ειδήσεις & Αποφάσεις")
    cols = st.columns(3)
    start = 5 if (tab_name == "HOME" and not search_query) else 0
    for i, r in enumerate(curr.iloc[start:].head(9).itertuples()):
        with cols[i%3]:
            st.image(get_image(r._asdict()), use_column_width=True)
            st.markdown(f"**{r.title}**")
            st.caption(r.last_update)
            st.markdown(f"[Link]({r.link})")
            st.markdown("---")

with tabs[0]: render_tab("HOME")
with tabs[1]: render_tab("ENGINEERS")
with tabs[2]: render_tab("LEGAL")
with tabs[3]: render_tab("FEK")
with tabs[4]: 
    st.metric("Total", len(df))
    if st.secrets.get("admin_password") and st.text_input("Pass", type="password") == st.secrets["admin_password"]:
        if st.button("🧹 Clear Cache"): st.cache_data.clear(); st.rerun()
        if st.button("🔴 RESET DATABASE"): reset_database(); st.cache_data.clear(); st.rerun()
        st.dataframe(df)
