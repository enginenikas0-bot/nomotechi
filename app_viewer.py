import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime
import time

# --- 1. SETUP ΣΕΛΙΔΑΣ ---
st.set_page_config(
    page_title="NomoTechi | Το Portal του Επαγγελματία",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS (MSN / PROFESSIONAL STYLE) ---
st.markdown("""
<style>
    /* Γενική Τυπογραφία - Segoe UI για MSN look */
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #F3F3F3; /* Απαλό γκρι φόντο όπως τα portals */
        color: #262626;
    }
    
    /* HEADER */
    .header-container {
        background-color: white;
        padding: 15px 0;
        border-bottom: 4px solid #004B87; /* Official Blue */
        margin-bottom: 20px;
    }
    .header-logo {
        font-size: 2.5rem;
        font-weight: 800;
        color: #003366;
        letter-spacing: -1px;
        text-align: center;
    }
    .header-sub {
        text-align: center;
        color: #666;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* NEWS TICKER (Κυλιόμενη Μπάρα) */
    .ticker-wrap {
        width: 100%;
        background-color: #003366;
        color: white;
        height: 40px;
        overflow: hidden;
        white-space: nowrap;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .ticker-item {
        display: inline-block;
        padding-left: 100%;
        animation: ticker 30s linear infinite;
        font-weight: 600;
        font-size: 0.95rem;
    }
    @keyframes ticker {
        0%   { transform: translate3d(0, 0, 0); }
        100% { transform: translate3d(-100%, 0, 0); }
    }

    /* CAROUSEL / HERO SECTION (Το πλαίσιο πάνω αριστερά) */
    .hero-container {
        position: relative;
        background-color: black;
        border-radius: 4px;
        overflow: hidden;
        height: 400px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    .hero-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 0.7; /* Για να φαίνονται τα γράμματα */
        transition: opacity 0.3s;
    }
    .hero-image:hover { opacity: 0.8; }
    
    .hero-overlay {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        padding: 30px;
        background: linear-gradient(to top, rgba(0,0,0,0.9), transparent);
    }
    .hero-cat {
        color: #FFD700; /* Χρυσό για την κατηγορία */
        font-size: 0.8rem;
        font-weight: 800;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .hero-title {
        color: white;
        font-size: 1.8rem;
        font-weight: 700;
        line-height: 1.2;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.5);
    }
    .hero-title a { color: white !important; text-decoration: none; }
    .hero-title a:hover { text-decoration: underline; }

    /* NEWS LIST (Δεξιά Στήλη) */
    .list-item {
        background: white;
        padding: 15px;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        flex-direction: column;
        transition: background 0.2s;
    }
    .list-item:hover { background-color: #f9f9f9; }
    .list-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #003366;
        margin-bottom: 5px;
        line-height: 1.4;
    }
    .list-title a { color: #003366 !important; text-decoration: none; }
    .list-title a:hover { color: #0056b3 !important; text-decoration: underline; }
    .list-meta {
        font-size: 0.8rem;
        color: #888;
        display: flex;
        gap: 10px;
    }

    /* GRID CARDS (Κάτω μέρος) */
    .grid-card {
        background: white;
        border: 1px solid #ddd;
        border-radius: 4px;
        overflow: hidden;
        height: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .grid-img {
        height: 140px;
        background-color: #eee;
        overflow: hidden;
    }
    .grid-img img { width: 100%; height: 100%; object-fit: cover; }
    .grid-content { padding: 15px; }
    .grid-cat { font-size: 0.7rem; font-weight: 800; color: #cc0000; text-transform: uppercase; margin-bottom: 5px; }
    .grid-title { font-size: 1rem; font-weight: 700; color: #222; margin-bottom: 10px; line-height: 1.3; }
    .grid-text { font-size: 0.9rem; color: #555; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }

    /* STYLING THE TABS */
    .stTabs [data-baseweb="tab-list"] {
        background-color: white;
        padding: 10px;
        border-radius: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        gap: 20px;
    }
    .stTabs [aria-selected="true"] {
        color: #cc0000 !important;
        border-bottom-color: #cc0000 !important;
        font-weight: 800;
    }
    
    /* Navigation Buttons for Slider */
    .nav-btn {
        background: rgba(255,255,255,0.2);
        border: 1px solid white;
        color: white;
        padding: 5px 15px;
        cursor: pointer;
        font-weight: bold;
        border-radius: 20px;
    }
    .nav-btn:hover { background: white; color: black; }
</style>
""", unsafe_allow_html=True)

# --- 3. DATA & FUNCTIONS ---
RSS_FEEDS = {
    "📜 E-Nomothesia": "https://www.e-nomothesia.gr/rss.xml",
    "⚖️ ΔΣΑ": "https://www.dsa.gr/rss.xml",
    "⚖️ Lawspot": "https://www.lawspot.gr/nomika-nea/feed",
    "🎓 Dikaiologitika": "https://www.dikaiologitika.gr/feed", 
    "💼 Taxheaven": "https://www.taxheaven.gr/rss",
    "🏛️ ΤΕΕ": "https://web.tee.gr/feed/",
    "🏗️ Ypodomes": "https://ypodomes.com/feed/",
    "🌿 B2Green": "https://news.b2green.gr/feed",
    "⚡ EnergyPress": "https://energypress.gr/feed",
    "🚜 PEDMEDE": "https://www.pedmede.gr/feed/",
    "👷 Michanikos": "https://www.michanikos-online.gr/feed/",
    "🌍 GreenAgenda": "https://greenagenda.gr/feed/",
    "🏠 POMIDA": "https://www.pomida.gr/feed/",
    "📐 Archetypes": "https://www.archetypes.gr/feed/",
    "💰 Capital": "https://www.capital.gr/rss/oikonomia"
}

def remove_accents(input_str):
    replacements = {'ά':'α','έ':'ε','ή':'η','ί':'ι','ό':'ο','ύ':'υ','ώ':'ω','Ά':'Α','Έ':'Ε','Ή':'Η','Ί':'Ι','Ό':'Ο','Ύ':'Υ','Ώ':'Ω','ϊ':'ι','ϋ':'υ'}
    for char, rep in replacements.items(): input_str = input_str.replace(char, rep)
    return input_str.lower()

# --- Ο ΕΞΥΠΝΟΣ ΑΛΓΟΡΙΘΜΟΣ ---
def guess_category_smart(title, summary, source_name):
    full_text = remove_accents(title + " " + summary)
    source_clean = remove_accents(source_name)
    
    fek_keywords = ['φεκ', 'εγκυκλιος', 'κυα', 'προεδρικο διαταγμα', 'νομοσχεδιο', 'τροπολογια', 'αποφαση υπουργου', 'δημοσιευθηκε στο φεκ']
    is_fek = any(w in full_text for w in fek_keywords) or "e-nomothesia" in source_clean

    if is_fek:
        eng_relevant_words = ['αυθαιρετα', '4495', 'πολεοδομ', 'δομηση', 'κτιριοδομ', 'αδειες', 'οικοδομ', 'νοκ', 'δημοσια εργα', 'αναθεση', 'συμβαση', 'υποδομες', 'μετρο', 'πεδμεδε', 'μηχανικ', 'τεε', 'ενεργειακ', 'εξοικονομω', 'αντικειμενικ']
        if any(w in full_text for w in eng_relevant_words):
            return "📜 Νομοθεσία: Μηχανικών & Έργων" 
        return "📜 Νομοθεσία & ΦΕΚ"

    scores = {"eng_poleodomia": 0, "eng_energy": 0, "eng_projects": 0, "law_realestate": 0, "law_justice": 0, "finance": 0, "news_general": 0}

    if "b2green" in source_clean or "greenagenda" in source_clean or "energypress" in source_clean:
        scores["eng_energy"] += 3
    elif "ypodomes" in source_clean or "pedmede" in source_clean:
        scores["eng_projects"] += 3
    elif "pomida" in source_clean:
        scores["law_realestate"] += 3
    elif "lawspot" in source_clean or "dsa" in source_clean:
        scores["law_justice"] += 3
    elif "taxheaven" in source_clean or "capital" in source_clean:
        scores["finance"] += 3

    # ΔΙΟΡΘΩΜΕΝΟΙ ΒΡΟΓΧΟΙ ΓΙΑ ΑΠΟΦΥΓΗ SYNTAX ERROR
    poleodomia_words = ['αυθαιρετα', '4495', 'πολεοδομ', 'δομηση', 'κτιριοδομ', 'αδειες', 'οικοδομ', 'νοκ', 'τοπογραφικ', 'ταυτοτητα κτιριου', 'συντελεστης', 'υδομ']
    for w in poleodomia_words:
        if w in full_text:
            scores["eng_poleodomia"] += 2
            
    energy_words = ['εξοικονομω', 'φωτοβολταικ', 'ενεργεια', 'απε', 'ραε', 'υδρογονο', 'κλιματικ', 'περιβαλλον', 'ανακυκλωση', 'αποβλητα', 'net metering']
    for w in energy_words:
        if w in full_text:
            scores["eng_energy"] += 2
            
    project_words = ['διαγωνισμ', 'δημοσια εργα', 'αναθεση', 'συμβαση', 'υποδομες', 'μετρο', 'οδικος', 'πεδμεδε', 'μειοδοτ', 'αναδοχος', 'εργοταξιο', 'κατασκευαστικ', 'γεφυρα', 'αυτοκινητοδρομος', 'σιδηροδρομ']
    for w in project_words:
        if w in full_text:
            scores["eng_projects"] += 2
            
    estate_words = ['συμβολαιογραφ', 'μεταβιβαση', 'γονικη παροχη', 'κληρονομι', 'διαθηκη', 'αντικειμενικ', 'enfia', 'υποθηκοφυλακ', 'κτηματολογιο', 'ε9', 'ακινητ']
    for w in estate_words:
        if w in full_text:
            scores["law_realestate"] += 2

    disaster_words = ['ηφαιστειο', 'σεισμος', 'χιονια', 'κακοκαιρια', 'πυρκαγια', 'φωτια', 'πλημμυρα', 'καιρος']
    is_disaster = any(w in full_text for w in disaster_words)
    justice_words = ['δικαστηρι', 'αρεοπαγ', 'στε', 'ποινικ', 'αστικ', 'δικη', 'αγωγη', 'δικηγορ', 'ολομελεια', 'παραβαση', 'κατηγορουμεν', 'εφετειο', 'νομικο συμβουλιο']
    found_justice_words = sum(1 for w in justice_words if w in full_text)
    
    if is_disaster and found_justice_words < 2:
        scores["law_justice"] = -10 
    else:
        scores["law_justice"] += (found_justice_words * 2)

    fin_words = ['φορολογ', 'ααδε', 'mydata', 'εφορια', 'φπα', 'μισθοδοσια', 'τραπεζ', 'δανει', 'εφκα', 'συνταξ', 'τεκμηρια', 'οφειλ']
    for w in fin_words:
        if w in full_text:
            scores["finance"] += 2

    best_category = max(scores, key=scores.get)
    if scores[best_category] < 2:
        if any(w in full_text for w in ['εκλογες', 'παραταση', 'ανακοινωση']):
            return "📢 Θεσμικά & Ανακοινώσεις"
        return "🌐 Γενική Ενημέρωση"

    category_map = {
        "eng_poleodomia": "📐 Μηχανικοί: Πολεοδομία",
        "eng_energy": "🌱 Μηχανικοί: Ενέργεια & Περιβάλλον",
        "eng_projects": "✒️ Μηχανικοί: Έργα",
        "law_realestate": "🖋️ Συμβολαιογραφικά & Ακίνητα",
        "law_justice": "⚖️ Νομικά Θέματα",
        "finance": "💼 Φορολογικά & Οικονομία",
        "news_general": "🌐 Γενική Ενημέρωση"
    }
    return category_map[best_category]

# --- IMAGE PLACEHOLDER LOGIC ---
def get_category_image(category):
    if "Πολεοδομία" in category: return "https://images.unsplash.com/photo-1503387762-592deb58ef4e?q=80&w=1600&auto=format&fit=crop"
    if "Ενέργεια" in category: return "https://images.unsplash.com/photo-1509391366360-2e959784a276?q=80&w=1600&auto=format&fit=crop"
    if "Έργα" in category: return "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?q=80&w=1600&auto=format&fit=crop"
    if "Νομοθεσία" in category or "ΦΕΚ" in category: return "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=1600&auto=format&fit=crop"
    if "Νομικά" in category or "Δικαιοσύνη" in category: return "https://images.unsplash.com/photo-1505664194779-8beaceb93744?q=80&w=1600&auto=format&fit=crop"
    if "Συμβολαιο" in category or "Ακίνητα" in category: return "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1600&auto=format&fit=crop"
    if "Οικονομία" in category: return "https://images.unsplash.com/photo-1554224155-98406894d009?q=80&w=1600&auto=format&fit=crop"
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1600&auto=format&fit=crop" # General

def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        return gc.open("laws_database").sheet1
    except: return None

def load_data():
    sheet = get_db_connection()
    return sheet.get_all_records() if sheet else []

def reset_database():
    sheet = get_db_connection()
    if not sheet: return False
    try:
        sheet.batch_clear(["A2:G5000"])
        return True
    except: return False

def run_force_scan():
    sheet = get_db_connection()
    if not sheet: return 0
    try:
        existing_data = sheet.get_all_records()
        existing_links = [row['link'] for row in existing_data]
    except:
        existing_data = []
        existing_links = []
        
    count = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    progress_bar = st.progress(0)
    status = st.empty()
    total = len(RSS_FEEDS)
    current = 0
    
    for source, url in RSS_FEEDS.items():
        current += 1
        progress_bar.progress(current / total)
        status.text(f"Scanning: {source}...")
        try:
            feed = feedparser.parse(url, agent=headers['User-Agent'])
            if not feed.entries and feed.bozo: continue
            for entry in feed.entries[:3]:
                if entry.link not in existing_links:
                    summary = entry.summary.replace("<p>", "").replace("</p>", "")[:200] + "..." if 'summary' in entry else ""
                    cat = guess_category_smart(entry.title, summary, source)
                    new_row = [len(existing_data)+count+1, source, entry.title, summary, entry.link, datetime.now().strftime("%Y-%m-%d"), cat]
                    sheet.append_row(new_row)
                    existing_links.append(entry.link)
                    count += 1
        except: pass
        
    progress_bar.empty()
    status.empty()
    return count

# --- 4. RENDER UI ---

# Header Section
st.markdown("""
<div class="header-container">
    <div class="header-logo">🏛️ NomoTechi</div>
    <div class="header-sub">Η Ενιαία Πύλη για Μηχανικούς, Δικηγόρους & Συμβολαιογράφους</div>
</div>
""", unsafe_allow_html=True)

# Load Data
data = load_data()
df = pd.DataFrame(data)

# Ticker (Automatic Flow)
if not df.empty:
    latest_titles = "   +++   ".join([f"{row['title']} ({row['law']})" for idx, row in df.head(10).iterrows()])
    st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker-item">
            {latest_titles}
        </div>
    </div>
    <br>
    """, unsafe_allow_html=True)

# Tabs
tabs = st.tabs(["🏠 ΡΟΗ ΕΙΔΗΣΕΩΝ", "📐 ΜΗΧΑΝΙΚΟΙ & ΕΡΓΑ", "⚖️ ΝΟΜΙΚΑ & ΑΚΙΝΗΤΑ", "📜 ΦΕΚ & ΝΟΜΟΘΕΣΙΑ", "⚙️ ADMIN"])

if not df.empty:
    df = df.iloc[::-1].reset_index(drop=True)
    
    # Session State for Slider
    if 'slider_idx' not in st.session_state: st.session_state.slider_idx = 0

    def get_filtered_df(tab_name):
        if tab_name == "HOME": return df
        if tab_name == "ENG": return df[df['category'].str.contains("Μηχανικ|Πολεοδομ|Ενέργεια|Έργα|Θεσμικά", case=False)]
        if tab_name == "LAW": return df[df['category'].str.contains("Νομικ|Συμβολαιο|Δικηγόρ|Φορολογ", case=False)]
        if tab_name == "FEK": return df[df['category'].str.contains("Νομοθεσία|ΦΕΚ", case=False)]
        return df

    def render_tab_content(tab_code):
        current_df = get_filtered_df(tab_code).reset_index(drop=True)
        if current_df.empty:
            st.info("Δεν υπάρχουν ειδήσεις σε αυτή την κατηγορία.")
            return

        # --- MSN STYLE SLIDER (TOP LEFT) & LIST (RIGHT) ---
        col_hero, col_list = st.columns([1.8, 1.2]) # 60% - 40% split
        
        with col_hero:
            # Slider Logic
            slider_len = min(5, len(current_df))
            current_slide = st.session_state.slider_idx % slider_len
            hero_article = current_df.iloc[current_slide]
            hero_img = get_category_image(hero_article['category'])
            
            st.markdown(f"""
            <div class="hero-container">
                <img src="{hero_img}" class="hero-image">
                <div class="hero-overlay">
                    <div class="hero-cat">{hero_article['category']}</div>
                    <div class="hero-title">
                        <a href="{hero_article['link']}" target="_blank">{hero_article['title']}</a>
                    </div>
                    <div style="color:white; margin-top:5px; font-size:0.9rem;">{hero_article['law']} • {hero_article['last_update']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Arrows
            c_prev, c_txt, c_next = st.columns([1, 4, 1])
            if c_prev.button("⬅️", key=f"prev_{tab_code}"):
                st.session_state.slider_idx -= 1
                st.rerun()
            if c_next.button("➡️", key=f"next_{tab_code}"):
                st.session_state.slider_idx += 1
                st.rerun()

        with col_list:
            st.markdown(f"### 📰 Τελευταία {tab_code if tab_code != 'HOME' else 'Ροή'}")
            # List items
            for idx, row in current_df.head(6).iterrows():
                st.markdown(f"""
                <div class="list-item">
                    <div class="list-title"><a href="{row['link']}" target="_blank">{row['title']}</a></div>
                    <div class="list-meta">
                        <span style="color:#cc0000; font-weight:bold;">{row['category'].split(':')[0]}</span>
                        <span>{row['law']}</span>
                        <span>{row['last_update']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        
        # --- GRID SECTION (ALL NEWS) ---
        st.subheader("📌 Περισσότερα Θέματα")
        
        # Grid logic
        grid_df = current_df.iloc[6:] # Skip top 6
        if not grid_df.empty:
            rows = len(grid_df) // 3 + 1
            for i in range(rows):
                c1, c2, c3 = st.columns(3)
                for j, col in enumerate([c1, c2, c3]):
                    idx = i * 3 + j
                    if idx < len(grid_df):
                        row = grid_df.iloc[idx]
                        card_img = get_category_image(row['category'])
                        with col:
                            st.markdown(f"""
                            <div class="grid-card">
                                <div class="grid-img"><img src="{card_img}"></div>
                                <div class="grid-content">
                                    <div class="grid-cat">{row['category'].split(':')[0]}</div>
                                    <div class="grid-title">{row['title']}</div>
                                    <div class="grid-text">{row['content']}</div>
                                    <div style="margin-top:10px; font-size:0.75rem; color:#888;">
                                        {row['law']} | <a href="{row['link']}" target="_blank" style="color:#003366; font-weight:bold;">Διαβάστε περισσότερα ></a>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

    # Render Tabs
    with tabs[0]: render_tab_content("HOME")
    with tabs[1]: render_tab_content("ENG")
    with tabs[2]: render_tab_content("LAW")
    with tabs[3]: render_tab_content("FEK")
    
    # Admin Tab
    with tabs[4]:
        st.header("Διαχείριση")
        pw = st.text_input("Κωδικός Διαχειριστή", type="password")
        if pw == st.secrets.get("admin_password", ""):
            st.success("Admin Access: OK")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚀 Force Scan", type="primary"):
                    with st.spinner("Σάρωση..."): run_force_scan(); st.success("Done!"); time.sleep(1); st.rerun()
            with c2:
                if st.button("🧹 Clear Cache"): st.cache_data.clear(); st.rerun()
                if st.button("🔴 RESET DATABASE"): reset_database(); st.cache_data.clear(); st.rerun()
            st.dataframe(df)

else:
    st.warning("Η βάση είναι κενή. Πηγαίνετε στο Admin -> Force Scan.")
