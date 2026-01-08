import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime
import time

# --- 1. SETUP ΣΕΛΙΔΑΣ ---
st.set_page_config(
    page_title="NomoTechi | Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. PREMIUM CSS DESIGN (Smart & Clean) ---
st.markdown("""
<style>
    /* Google Fonts Import (Inter Font για μοντέρνο look) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #334155; /* Slate 700 - Ξεκούραστο γκρι */
        background-color: #F8FAFC; /* Πολύ απαλό γκρι-μπλε φόντο */
    }

    /* HEADER: Μοντέρνο Gradient */
    .header-bar {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        padding: 20px 30px;
        color: white;
        border-radius: 12px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-title {font-size: 1.8rem; font-weight: 800; letter-spacing: -0.5px;}
    .header-subtitle {font-size: 0.9rem; opacity: 0.8; font-weight: 400;}

    /* HERO SECTION (Η μεγάλη είδηση) */
    .hero-card {
        background-color: white;
        padding: 40px;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        margin-bottom: 40px;
        border-left: 5px solid #3B82F6; /* Bright Blue Accent */
        transition: transform 0.2s;
    }
    .hero-card:hover {transform: translateY(-2px);}
    .hero-cat {
        color: #3B82F6; 
        font-weight: 700; 
        text-transform: uppercase; 
        font-size: 0.85rem; 
        letter-spacing: 1px; 
        margin-bottom: 10px;
    }
    .hero-title a {
        font-size: 2rem; 
        font-weight: 800; 
        color: #0F172A !important; 
        text-decoration: none;
        line-height: 1.2;
    }
    .hero-title a:hover {color: #2563EB !important;}
    .hero-summary {
        font-size: 1.1rem; 
        color: #475569; 
        margin-top: 15px; 
        line-height: 1.6;
    }

    /* GRID CARDS (Οι μικρές κάρτες) */
    .news-card {
        background-color: white;
        border-radius: 12px;
        padding: 25px;
        height: 100%;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
        border: 1px solid #F1F5F9;
    }
    .news-card:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        transform: translateY(-5px);
        border-color: #E2E8F0;
    }
    .card-meta {
        font-size: 0.75rem; 
        color: #64748B; 
        margin-bottom: 10px; 
        display: flex; 
        justify-content: space-between;
    }
    .card-badge {
        background-color: #EFF6FF; 
        color: #2563EB; 
        padding: 4px 8px; 
        border-radius: 6px; 
        font-weight: 600;
        font-size: 0.7rem;
    }
    .card-title {
        font-size: 1.15rem; 
        font-weight: 700; 
        margin-top: 10px; 
        margin-bottom: 10px; 
        line-height: 1.4;
    }
    .card-title a {color: #1E293B !important; text-decoration: none;}
    .card-title a:hover {color: #2563EB !important;}
    
    /* LIST ITEMS (Ροή) */
    .list-container {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .list-item {
        padding: 15px 0; 
        border-bottom: 1px solid #F1F5F9;
        display: flex;
        flex-direction: column;
    }
    .list-item:last-child {border-bottom: none;}
    .list-title a {font-weight: 600; color: #334155 !important; font-size: 1rem; text-decoration: none;}
    .list-title a:hover {color: #0F172A !important; text-decoration: underline;}
    
    /* SIDEBAR WIDGETS */
    .widget-box {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #E2E8F0;
        margin-bottom: 20px;
    }
    .widget-title {font-weight: 800; color: #0F172A; margin-bottom: 15px; font-size: 1rem;}
    
    /* Button Override */
    .stButton button {
        background-color: white;
        color: #0F172A;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        transition: all 0.2s;
    }
    .stButton button:hover {
        border-color: #3B82F6;
        color: #3B82F6;
        background-color: #EFF6FF;
    }
    
    .footer {text-align: center; color: #94A3B8; font-size: 0.85rem; margin-top: 60px; padding-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC ---
def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        sh = gc.open("laws_database")
        return sh.sheet1
    except Exception as e:
        return None

def load_data():
    sheet = get_db_connection()
    if sheet:
        try:
            return sheet.get_all_records()
        except:
            return []
    return []

# Run Manual Scan Logic (Hidden from UI usually)
def run_bot_update_manual():
    # ... (Ίδια λογική με πριν για τη χειροκίνητη σάρωση αν χρειαστεί)
    pass 

# --- 4. UI RENDERING ---

# DATA LOADING
data = load_data()
df = pd.DataFrame(data)

# HEADER UI
st.markdown("""
<div class="header-bar">
    <div>
        <div class="header-title">🏛️ NomoTechi</div>
        <div class="header-subtitle">Intelligence for Modern Engineers</div>
    </div>
    <div style="font-size: 0.8rem; opacity: 0.8;">v2.0 • Live Feed</div>
</div>
""", unsafe_allow_html=True)

# MENU (Simple & Clean)
col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 1, 1, 5])
with col_nav1:
    if st.button("🏠 Home"): st.rerun()
with col_nav2:
    if st.button("📊 Stats"): 
        st.toast("Statistics coming soon!")
with col_nav3:
    with st.expander("🔐"): # Minimal Admin Icon
        pw = st.text_input("Pass", type="password", label_visibility="collapsed")
        if pw == st.secrets.get("admin_password", ""):
            st.success("Admin OK")
            if st.button("Scan Now"):
                st.info("Scanner activated via Backend")

st.markdown("<br>", unsafe_allow_html=True)

if df.empty:
    st.info("System initializing... No articles found yet.")
else:
    # Sort Data
    df = df.iloc[::-1].reset_index(drop=True)
    
    # --- HERO SECTION ---
    hero = df.iloc[0]
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-cat">{hero['category']}</div>
        <div class="hero-title">
            <a href="{hero['link']}" target="_blank">{hero['title']}</a>
        </div>
        <div class="hero-summary">{hero['content']}</div>
        <div style="margin-top: 20px; font-size: 0.9rem; color: #64748B;">
            📅 {hero['last_update']}  •  🔗 <b>{hero['law']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- GRID SECTION ---
    st.markdown("### 📌 Top Picks")
    c1, c2, c3 = st.columns(3)
    
    def render_card(col, row):
        with col:
            st.markdown(f"""
            <div class="news-card">
                <div class="card-meta">
                    <span class="card-badge">{row['category'].split(' ')[0]}</span>
                    <span>{row['last_update']}</span>
                </div>
                <div class="card-title">
                    <a href="{row['link']}" target="_blank">{row['title']}</a>
                </div>
                <div style="font-size: 0.9rem; color: #64748B; line-height: 1.5;">
                    {row['content'][:110]}...
                </div>
                <div style="margin-top: 15px; font-size: 0.8rem; font-weight: 600; color: #94A3B8;">
                    Source: {row['law']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    if len(df) > 1: render_card(c1, df.iloc[1])
    if len(df) > 2: render_card(c2, df.iloc[2])
    if len(df) > 3: render_card(c3, df.iloc[3])
    
    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- FEED SECTION ---
    main_feed, sidebar = st.columns([2, 1])
    
    with main_feed:
        st.markdown("### 📰 Latest Feed")
        st.markdown('<div class="list-container">', unsafe_allow_html=True)
        
        for index, row in df.iloc[4:15].iterrows():
            st.markdown(f"""
            <div class="list-item">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div class="list-title">
                        <a href="{row['link']}" target="_blank">{row['title']}</a>
                    </div>
                    <span style="font-size: 0.7rem; background: #F1F5F9; padding: 2px 6px; border-radius: 4px; white-space: nowrap; margin-left: 10px;">
                        {row['law']}
                    </span>
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 5px;">
                   {row['category']} • {row['last_update']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

    with sidebar:
        st.markdown("### 🎯 For You")
        
        # Widget 1: Trending
        st.markdown("""
        <div class="widget-box">
            <div class="widget-title">🔥 Trending Topics</div>
            <div style="font-size: 0.9rem; color: #475569;">
                • Εξοικονομώ 2025<br>
                • Κτηματολόγιο Προθεσμίες<br>
                • Ψηφιακή Κάρτα Εργασίας<br>
                • Νέος Οικοδομικός Κανονισμός
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Widget 2: Sources
        st.markdown("""
        <div class="widget-box">
            <div class="widget-title">📡 Live Sources</div>
            <span style="background:#DBEAFE; color:#1E40AF; padding:2px 8px; border-radius:10px; font-size:0.8rem; margin:2px; display:inline-block;">ΤΕΕ</span>
            <span style="background:#DCFCE7; color:#166534; padding:2px 8px; border-radius:10px; font-size:0.8rem; margin:2px; display:inline-block;">B2Green</span>
            <span style="background:#FEF3C7; color:#92400E; padding:2px 8px; border-radius:10px; font-size:0.8rem; margin:2px; display:inline-block;">Taxheaven</span>
            <span style="background:#F3E8FF; color:#6B21A8; padding:2px 8px; border-radius:10px; font-size:0.8rem; margin:2px; display:inline-block;">Ypodomes</span>
        </div>
        """, unsafe_allow_html=True)

# FOOTER
st.markdown('<div class="footer">Built with intelligence by NomoTechi © 2026</div>', unsafe_allow_html=True)
