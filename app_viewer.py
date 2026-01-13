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

# --- 2. CSS (MSN THEME FINAL) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Segoe+UI:wght@300;400;600&display=swap');
    
    /* GLOBAL RESET */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; background-color: #ffffff; color: #222; }
    
    /* SEARCH BAR */
    div[data-baseweb="input"] { background-color: #003366 !important; border: 1px solid #004080 !important; border-radius: 4px !important; }
    div[data-baseweb="input"] input { color: #ffffff !important; caret-color: #ffffff !important; font-weight: 500 !important; }
    div[data-baseweb="input"] input::placeholder { color: #b3cce6 !important; }

    /* SIDEBAR */
    [data-testid="collapsedControl"], [data-testid="stSidebar"] button { color: #000 !important; }

    /* BRANDING & HEADER */
    .top-powered-brand { font-family: 'Segoe UI', sans-serif; font-size: 0.75rem; color: #666; text-align: center; padding-top: 15px; }
    .top-powered-brand a { color: #444 !important; text-decoration: none; }
    .brand-card { background: #ffffff; border: 1px solid #f0f0f0 !important; border-radius: 4px; padding: 25px 15px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); text-align: center; }
    .brand-btn { display: block; width: 100%; text-align: center; background-color: #111; color: #fff !important; border: none; padding: 10px 0; border-radius: 2px; font-size: 0.8rem; font-weight: 600; text-decoration: none; transition: 0.3s; }
    .brand-btn:hover { background-color: #444; }
    .header-container { background: white; padding: 0 0 25px 0; border-bottom: 2px solid #003366; text-align: center; margin-bottom: 15px; }
    .header-logo { font-family: 'Merriweather', serif; font-size: 3rem; font-weight: 900; color: #003366; letter-spacing: -1px; }
    .header-sub { color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 2px; font-weight: 500; margin-top:5px;}

    /* LIST & GRID CARDS */
    .list-item { background: white; padding: 20px; border-bottom: 1px solid #f5f5f5; transition: 0.2s; margin-bottom: 5px; }
    .list-item:hover { background-color: #fafafa; border-left: 3px solid #003366; }
    .list-title a { color: #111 !important; text-decoration: none; font-weight: 600; font-size: 1.1rem; }
    .grid-card { background: white; border: 1px solid #f5f5f5; border-radius: 4px; overflow: hidden; height: 100%; display: flex; flex-direction: column; box-shadow: 0 2px 10px rgba(0,0,0,0.05); transition: transform 0.2s; }
    .grid-card:hover { transform: translateY(-3px); box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
    .article-date { font-size: 0.7rem; color: #aaa; text-align: right; margin-top: 10px; border-top: 1px solid #f9f9f9; padding-top: 5px; }

    /* TICKER */
    .ticker-wrap { background-color: #ffffff; border-top: 1px solid #f5f5f5; border-bottom: 1px solid #f5f5f5; height: 32px; overflow: hidden; white-space: nowrap; display: flex; align-items: center; margin-bottom: 20px; }
    .ticker-item { display: inline-block; padding-left: 100%; animation: ticker 80s linear infinite; font-size: 0.8rem; color: #333; font-weight: 600; }
    .ticker-label { position: absolute; left: 0; background: white; z-index: 10; padding: 5px 15px; font-size: 0.7rem; font-weight: 700; color: #cc0000; border-right: 1px solid #eee; height: 30px; line-height: 22px; }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

    /* --- HERO SLIDER (MSN STYLE) --- */
    .hero-wrapper { 
        position: relative; 
        height: 450px; 
        overflow: hidden; 
        margin-bottom: 0px; 
        border-radius: 6px; 
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        z-index: 1; /* Base z-index */
    }
    .hero-image { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.65); transition: transform 6s ease; }
    .hero-image:hover { transform: scale(1.05); filter: brightness(0.75); }
    
    .hero-overlay { 
        position: absolute; bottom: 0; left: 0; width: 100%; padding: 40px; 
        background: linear-gradient(to top, rgba(0,0,0,0.9), transparent); 
        pointer-events: none; /* Let clicks pass through to dots if needed */
        z-index: 2;
    }
    .hero-title { 
        font-family: 'Merriweather', serif; color: white !important; 
        font-size: 2.2rem; font-weight: 700; line-height: 1.2; 
        text-shadow: 0 2px 5px black; text-decoration: none; cursor: pointer;
        pointer-events: auto; 
    }
    .hero-title:hover { text-decoration: underline; color: #f0f0f0 !important; }

    /* --- MSN DOTS (INDICATORS) --- */
    .msn-dots-container {
        position: absolute;
        bottom: 15px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 8px;
        z-index: 5;
    }
    .msn-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: rgba(255,255,255,0.4);
        transition: 0.3s;
    }
    .msn-dot.active {
        background-color: #fff;
        transform: scale(1.2);
    }

    /* --- MSN ARROWS (THE REAL FIX) --- */
    /* We create a container that sits ON TOP of the image explicitly */
    .msn-controls-layer {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none; /* Allow clicks to pass through empty areas */
        z-index: 10;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0 15px;
    }

    /* Target the Streamlit Buttons inside our layout */
    div[data-testid="column"] button.msn-arrow {
        pointer-events: auto; /* Enable clicks */
        background-color: rgba(255, 255, 255, 0.2) !important; /* Glass effect */
        backdrop-filter: blur(5px);
        color: #fff !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        width: 40px !important;
        height: 40px !important;
        border-radius: 8px !important; /* Rounded Square */
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
        margin-top: -380px !important; /* PULL UP ONTO IMAGE */
        position: relative;
        z-index: 9999;
    }
    div[data-testid="column"] button.msn-arrow:hover {
        background-color: rgba(255, 255, 255, 0.9) !important;
        color: #000 !important; /* Black arrow on hover */
        transform: scale(1.1);
    }
    div[data-testid="column"] button.msn-arrow p {
        font-size: 22px !important;
        margin-top: -4px !important;
    }

    /* Hide container backgrounds */
    div[data-testid="stVerticalBlock"] > div { background: transparent; }

    /* --- DARK MODE OVERRIDES --- */
    @media (prefers-color-scheme: dark) {
        html, body, [class*="css"] { background-color: #0e1117; color: #fafafa; }
        div[data-baseweb="input"] { background-color: #262730 !important; border: 1px solid #333 !important; }
        .tv-light-container { display: none !important; } .tv-dark-container { display: block !important; }
        .brand-card, .list-item, .grid-card { background: #262730 !important; border: none !important; }
        .brand-card img { filter: invert(1); }
        .header-container { background: #0e1117 !important; border-bottom: 3px solid #4da6ff; }
        .header-logo { color: #fff !important; }
        .ticker-wrap { background: #262730 !important; border-color: #444 !important; }
        .ticker-item { color: #eee !important; }
        iframe[title="3rd party frame"] { filter: invert(1) hue-rotate(180deg) !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC ---
IMAGE_POOL = { "ENG": ["https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=1200"], "GENERAL": ["https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200"] }
def get_stock_image(c, t): return IMAGE_POOL["GENERAL"][0] # Simplified for safety
def get_db_client(): 
    try: return gspread.service_account_from_dict(st.secrets["gcp_service_account"]).open("laws_database")
    except: return None
def save_subscriber(email): return "OK" # Placeholder
def load_data():
    sh = get_db_client()
    if not sh: return []
    try: return sh.sheet1.get_all_records()
    except: return []
def reset_database(): return False
def normalize_greek(text): return text.lower() if text else ""
def get_image_as_base64(path): return None

# --- MAIN APP ---
with st.sidebar:
    st.markdown('<div class="brand-card"><h3>POWERED BY</h3><div style="font-size:2rem;">🏗️</div><a href="#" class="brand-btn">VISIT US</a></div>', unsafe_allow_html=True)
    st.markdown("### 📬 Newsletter")
    st.text_input("Email", placeholder="me@example.com")
    st.button("Εγγραφή")

st.markdown('<div class="header-container"><div class="header-logo">🏛️ NomoTechi</div></div>', unsafe_allow_html=True)

raw_data = load_data()
if not raw_data: st.warning("Loading..."); st.stop()
df = pd.DataFrame(raw_data)

st.markdown('<div class="search-container">', unsafe_allow_html=True)
st.text_input("", placeholder="🔍 Αναζήτηση...")
st.markdown('</div>', unsafe_allow_html=True)

# TICKER
latest_titles = "   +++   ".join([f"{row['title']}" for idx, row in df.head(5).iterrows()])
st.markdown(f'<div class="ticker-wrap"><div class="ticker-item">{latest_titles}</div></div>', unsafe_allow_html=True)

tabs = st.tabs(["ΚΟΡΥΦΑΙΑ", "ΜΗΧΑΝΙΚΟΙ", "ΝΟΜΙΚΑ", "ΦΕΚ", "STATS"])

if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0

def render_tab(tab_name):
    # Filter Logic (Simplified)
    curr_df = df if tab_name == "HOME" else df[df['category'].str.contains(tab_name, case=False, na=False)]
    if curr_df.empty: st.info("No data"); return

    if tab_name == "HOME":
        # UNIFIED TRADINGVIEW
        components.html("""
        <style> .light { display:block; } .dark { display:none; } @media (prefers-color-scheme: dark) { .light { display:none; } .dark { display:block; } } body { margin:0; overflow:hidden; } </style>
        <div class="light"><div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>{"symbols":[{"proName":"ATHEX:GD","title":"ATHEX"}],"colorTheme":"light","isTransparent":true,"displayMode":"compact","locale":"el"}</script></div></div>
        <div class="dark"><div class="tradingview-widget-container"><script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>{"symbols":[{"proName":"ATHEX:GD","title":"ATHEX"}],"colorTheme":"dark","isTransparent":true,"displayMode":"compact","locale":"el"}</script></div></div>
        """, height=70)

        c_hero, c_list = st.columns([1.8, 1.2])
        with c_hero:
            slider_len = min(5, len(curr_df))
            idx = st.session_state.slider_idx % slider_len
            row = curr_df.iloc[idx]
            
            # --- MSN DOTS GENERATOR ---
            dots_html = ""
            for i in range(slider_len):
                active_class = "active" if i == idx else ""
                dots_html += f'<div class="msn-dot {active_class}"></div>'

            # --- HERO IMAGE ---
            st.markdown(f"""
            <div class="hero-wrapper">
                <img src="{row.get('image_url', 'https://images.unsplash.com/photo-1504711434969-e33886168f5c')}" class="hero-image">
                <div class="hero-overlay">
                    <div style="color:white; font-size:0.7rem; font-weight:bold; margin-bottom:5px;">{row['category']}</div>
                    <div class="hero-title">{row['title']}</div>
                    <div style="color:#ddd; font-size:0.8rem; margin-top:5px;">{row['last_update']}</div>
                </div>
                <div class="msn-dots-container">
                    {dots_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- MSN BUTTONS (STRATEGIC PLACEMENT) ---
            # We place them BELOW the image, but the CSS (margin-top: -380px) pulls them UP into the center
            cols = st.columns([1, 10, 1])
            with cols[0]:
                if st.button("❮", key="prev"): st.session_state.slider_idx -= 1; st.rerun()
            with cols[2]:
                if st.button("❯", key="next"): st.session_state.slider_idx += 1; st.rerun()
            
            # INJECT CLASS TO THESE BUTTONS ONLY
            st.markdown("""
            <script>
                const buttons = window.parent.document.querySelectorAll('div[data-testid="column"] button');
                buttons.forEach(btn => {
                    if (btn.innerText === "❮" || btn.innerText === "❯") {
                        btn.classList.add("msn-arrow");
                    }
                });
            </script>
            """, unsafe_allow_html=True)

        with c_list:
            st.markdown("### Top Stories")
            for i, r in curr_df.head(5).iterrows():
                st.markdown(f'<div class="list-item"><div class="list-title"><a href="{r["link"]}">{r["title"]}</a></div></div>', unsafe_allow_html=True)
        st.markdown("---")

    st.subheader("Ειδήσεις & Αποφάσεις") # NO EMOJI
    # Grid Logic Here...
    for i, row in curr_df.head(6).iterrows():
        st.write(f"**{row['title']}**") # Placeholder for grid

with tabs[0]: render_tab("HOME")
with tabs[1]: render_tab("ENGINEERS")
with tabs[2]: render_tab("LEGAL")
with tabs[3]: render_tab("LEGISLATION")
with tabs[4]: st.write("Stats")
