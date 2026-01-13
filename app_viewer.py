import streamlit as st
import pandas as pd
import gspread
import time
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import base64

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTechi | Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS (CLEAN & ARROW-FREE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Segoe+UI:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; background-color: #ffffff; color: #222; }
    
    /* UI Elements */
    div[data-baseweb="input"] { background-color: #003366 !important; border: 1px solid #004080; border-radius: 4px; }
    div[data-baseweb="input"] input { color: white !important; caret-color: white; font-weight: 500; }
    [data-testid="stSidebar"] button { color: #000 !important; }

    /* Hero Slider (No Arrows) */
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

    /* Dots */
    .msn-dots-container {
        position: absolute; bottom: 15px; left: 50%; transform: translateX(-50%); display: flex; gap: 6px; z-index: 10;
    }
    .msn-dot {
        width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.4); transition: 0.3s;
    }
    .msn-dot.active { background: #fff; transform: scale(1.4); box-shadow: 0 0 5px rgba(255,255,255,0.8); }

    /* Ticker */
    .ticker-wrap { background-color: #ffffff; border-top: 1px solid #f5f5f5; border-bottom: 1px solid #f5f5f5; height: 32px; overflow: hidden; white-space: nowrap; display: flex; align-items: center; margin-bottom: 20px; }
    .ticker-item { display: inline-block; padding-left: 100%; animation: ticker 80s linear infinite; font-size: 0.8rem; color: #333; font-weight: 600; }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    /* Content Cards */
    .list-item { padding: 15px; border-bottom: 1px solid #eee; margin-bottom: 5px; transition: 0.2s; }
    .list-item:hover { border-left: 3px solid #003366; background: #fafafa; }
    .list-title a { color: #111 !important; text-decoration: none; font-weight: 600; font-size: 1.05rem; }
    
    .grid-card { background: white; border: 1px solid #f5f5f5; border-radius: 4px; overflow: hidden; height: 100%; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display:flex; flex-direction:column; }
    .article-meta { font-size: 0.75rem; color: #888; text-align: right; margin-top: auto; padding-top: 10px; border-top: 1px solid #f9f9f9; }

    /* Badges */
    .badge-sos { background: #dc3545; color: white; padding: 2px 5px; border-radius: 3px; font-size: 0.6rem; font-weight: 700; margin-right: 5px; }
    .badge-law { background: #003366; color: white; padding: 2px 5px; border-radius: 3px; font-size: 0.6rem; font-weight: 700; margin-right: 5px; }
    .badge-real { background: #28a745; color: white; padding: 2px 5px; border-radius: 3px; font-size: 0.6rem; font-weight: 700; margin-right: 5px; }
    .badge-gen { background: #666; color: white; padding: 2px 5px; border-radius: 3px; font-size: 0.6rem; font-weight: 700; margin-right: 5px; }

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
        iframe[title="3rd party frame"] { filter: invert(1) hue-rotate(180deg) brightness(1.2); }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC, DATA & SMART DATES ---
if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0
if 'last_run' not in st.session_state: st.session_state.last_run = time.time()

# Autoplay (6s)
if time.time() - st.session_state.last_run > 6:
    st.session_state.slider_idx += 1
    st.session_state.last_run = time.time()
    st.rerun()

IMAGE_POOL = {
    "ENG": ["https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=1200"],
    "LAW": ["https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=1200"],
    "GENERAL": ["https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200"]
}

def format_smart_date(date_str):
    """
    Shows TIME if today, DATE if older.
    Assumes date_str format 'YYYY-MM-DD HH:MM:SS' or similar.
    """
    try:
        dt = pd.to_datetime(date_str)
        now = datetime.now()
        
        # Check if today
        if dt.date() == now.date():
            return f"🕒 {dt.strftime('%H:%M')}"
        else:
            return f"📅 {dt.strftime('%d/%m')}"
    except:
        return date_str # Fallback

def get_db_client():
    try: return gspread.service_account_from_dict(st.secrets["gcp_service_account"]).open("laws_database")
    except: return None

def load_data():
    sh = get_db_client()
    if not sh: return []
    try: 
        raw = sh.sheet1.get_all_records()
        df = pd.DataFrame(raw)
        
        # 1. REMOVE GARBAGE (headers in rows)
        df = df[df['title'].str.lower() != 'title']
        
        # 2. CONVERT DATE & FILTER OLDER THAN 30 DAYS
        df['datetime_obj'] = pd.to_datetime(df['last_update'], errors='coerce')
        cutoff_date = datetime.now() - timedelta(days=30)
        df = df[df['datetime_obj'] > cutoff_date]
        
        # 3. SORT NEWEST FIRST
        df = df.sort_values(by='datetime_obj', ascending=False)
        
        return df.to_dict('records')
    except: return []

def get_image(row):
    # Determine category for stock image fallback
    cat = "GENERAL"
    if "ENGINEERS" in str(row.get('category')): cat = "ENG"
    elif "LEGAL" in str(row.get('category')): cat = "LAW"
    
    img_url = row.get('image_url', '')
    if str(img_url).startswith('http'): return img_url
    return IMAGE_POOL.get(cat, IMAGE_POOL["GENERAL"])[0]

def render_badges(category_str):
    badges_html = ""
    if "SOS" in category_str: badges_html += '<span class="badge-sos">🚨 SOS</span>'
    if "JUDICIAL" in category_str: badges_html += '<span class="badge-law">⚖️ ΔΙΚΑΣΤΗΡΙΑ</span>'
    if "LEGAL" in category_str: badges_html += '<span class="badge-law">⚖️ ΝΟΜΙΚΟ</span>'
    if "REAL_ESTATE" in category_str: badges_html += '<span class="badge-real">🏠 REAL ESTATE</span>'
    if "LEGISLATION" in category_str: badges_html += '<span class="badge-gen">📜 ΝΟΜΟΘΕΣΙΑ</span>'
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
    replacements = {'ά':'α','έ':'ε','ή':'η','ί':'ι','ό':'ο','ύ':'υ','ώ':'ω'}
    text = text.translate(str.maketrans(replacements))
    return text.lower()

# --- 4. LAYOUT ---
with st.sidebar:
    nikas_url = "https://www.nikastechnical.gr"
    st.markdown(f"""
    <div style="background:white; border:1px solid #eee; padding:15px; border-radius:4px; text-align:center; margin-bottom:20px;">
        <div style="font-size:0.7rem; color:#666;">POWERED BY</div>
        <div style="font-size:2rem;">🏗️</div>
        <div style="font-size:0.8rem; margin-bottom:10px;">Construction Engineering</div>
        <a href="{nikas_url}" target="_blank" style="background:#111; color:white; padding:5px 10px; text-decoration:none; font-size:0.8rem; border-radius:3px;">VISIT US</a>
    </div>
    """, unsafe_allow_html=True)
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
search_query = st.text_input("", placeholder="🔍 Αναζήτηση (π.χ. Αυθαίρετα, Άρειος Πάγος)...")
st.markdown('</div>', unsafe_allow_html=True)

if search_query:
    clean_query = normalize_greek(search_query)
    mask = df.apply(lambda row: 
                    clean_query in normalize_greek(str(row['title'])) or 
                    clean_query in normalize_greek(str(row['content'])) or 
                    clean_query in normalize_greek(str(row['category'])), axis=1)
    df = df[mask]

# Ticker
if not df.empty:
    titles = "   +++   ".join([f"{r['title']}" for i, r in df.head(10).iterrows()])
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-item">{titles}</div></div>', unsafe_allow_html=True)

tabs = st.tabs(["ΚΟΡΥΦΑΙΑ", "ΜΗΧΑΝΙΚΟΙ", "ΝΟΜΙΚΑ", "ΦΕΚ", "STATS"])

# --- SLIDER FRAGMENT (NO ARROWS) ---
@st.fragment(run_every=6)
def show_hero_slider(curr_df):
    if curr_df.empty: return
    
    st.session_state.slider_idx += 1
    slide_len = min(5, len(curr_df))
    idx = st.session_state.slider_idx % slide_len
    row = curr_df.iloc[idx]
    hero_badges = render_badges(row['category'])
    smart_date = format_smart_date(row['last_update'])

    # Dots HTML
    dots = "".join([f'<div class="msn-dot {"active" if i==idx else ""}"></div>' for i in range(slide_len)])
    
    st.markdown(f"""
    <div class="hero-wrapper">
        <img src="{get_image(row)}" class="hero-image">
        <div class="hero-overlay">
            <div style="margin-bottom:5px;">{hero_badges}</div>
            <a href="{row['link']}" target="_blank" class="hero-title">{row['title']}</a>
            <div style="color:#ddd; margin-top:5px; font-size:0.8rem;">{smart_date}</div>
        </div>
        <div class="msn-dots-container">{dots}</div>
    </div>
    """, unsafe_allow_html=True)

def render_tab(tab_name):
    if tab_name == "HOME": curr = df
    else: curr = df[df['category'].str.contains(tab_name, case=False, na=False)]
    
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
                date_display = format_smart_date(r['last_update'])
                st.markdown(f"""<div class="list-item"><div class="list-title"><a href="{r['link']}" target="_blank">{r['title']}</a></div><div style="font-size:0.75rem; color:#888;">{date_display}</div></div>""", unsafe_allow_html=True)
        st.markdown("---")

    st.subheader("Ειδήσεις & Αποφάσεις")
    
    # Grid Logic with AI Summaries
    start = 5 if (tab_name == "HOME" and not search_query) else 0
    grid_items = curr.iloc[start:]
    
    if not grid_items.empty:
        rows = len(grid_items) // 3 + 1
        for i in range(rows):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                idx = i * 3 + j
                if idx < len(grid_items):
                    r = grid_items.iloc[idx]
                    date_display = format_smart_date(r['last_update'])
                    badges = render_badges(r['category'])
                    with col:
                        st.markdown('<div class="grid-card">', unsafe_allow_html=True)
                        st.image(get_image(r), use_column_width=True)
                        st.markdown(f"""<div style="padding:15px;">
                            <div style="font-weight:700; font-size:1.05rem; margin-bottom:5px;">{r['title']}</div>
                            <div style="margin-bottom:10px;">{badges}</div>
                            </div>""", unsafe_allow_html=True)
                        
                        # AI INTELLIGENCE CHECK (Expander)
                        with st.expander("🤖 Ανάλυση & Σύνοψη"):
                            st.write(r['content']) # This displays the AI summary from DB
                        
                        st.markdown(f"""
                            <div style="padding:0 15px 15px 15px;">
                                <a href="{r['link']}" target="_blank" style="text-decoration:none; color:#003366; font-weight:600; font-size:0.85rem;">Διαβάστε περισσότερα →</a>
                                <div class="article-meta">{date_display}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("") # Spacer

with tabs[0]: render_tab("HOME")
with tabs[1]: render_tab("ENGINEERS")
with tabs[2]: render_tab("LEGAL")
with tabs[3]: render_tab("FEK")
with tabs[4]: 
    st.metric("Total Articles", len(df))
    if st.secrets.get("admin_password") and st.text_input("Pass", type="password") == st.secrets["admin_password"]:
        if st.button("🔴 RESET DATABASE"): reset_database(); st.cache_data.clear(); st.rerun()
        st.dataframe(df)
