import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime
import time

# --- 1. SETUP ---
st.set_page_config(
    page_title="NomoTechi | Professional Hub",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif; color: #334155; background-color: #F8FAFC;}
    .header-bar {background: linear-gradient(135deg, #0F172A 0%, #334155 100%); padding: 25px; color: white; border-radius: 12px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);}
    .stTabs [data-baseweb="tab-list"] {gap: 20px; justify-content: center;}
    .stTabs [data-baseweb="tab"] {height: 50px; background-color: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);}
    .stTabs [aria-selected="true"] {background-color: #EFF6FF; color: #2563EB; font-weight: bold; border-bottom: 2px solid #2563EB;}
    .news-card {background: white; border-radius: 12px; padding: 20px; height: 100%; border: 1px solid #F1F5F9; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: transform 0.2s; display: flex; flex-direction: column; justify-content: space-between;}
    .news-card:hover {transform: translateY(-3px); border-color: #cbd5e1; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);}
    .cat-badge {display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-bottom: 10px; width: fit-content;}
    .badge-eng {background: #E0F2FE; color: #0284C7;}
    .badge-law {background: #FEF2F2; color: #DC2626;}
    .badge-fek {background: #F0FDF4; color: #16A34A;}
    .badge-gen {background: #F1F5F9; color: #475569;}
    a {text-decoration: none; color: #1E293B !important; font-weight: 700;}
    a:hover {color: #2563EB !important;}
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC ---
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

# --- Ο ΕΞΥΠΝΟΣ ΑΛΓΟΡΙΘΜΟΣ (ΙΔΙΟΣ ΜΕ ΠΡΙΝ) ---
def guess_category_smart(title, summary, source_name):
    full_text = remove_accents(title + " " + summary)
    source_clean = remove_accents(source_name)
    
    fek_keywords = ['φεκ', 'εγκυκλιος', 'κυα', 'προεδρικο διαταγμα', 'νομοσχεδιο', 'τροπολογια', 'αποφαση υπουργου']
    if any(w in full_text for w in fek_keywords): return "📜 Νομοθεσία & ΦΕΚ"
    if "e-nomothesia" in source_clean: return "📜 Νομοθεσία & ΦΕΚ"

    scores = {"eng_poleodomia": 0, "eng_energy": 0, "eng_projects": 0, "law_realestate": 0, "law_justice": 0, "finance": 0, "news_general": 0}

    if "b2green" in source_clean or "greenagenda" in source_clean or "energypress" in source_clean: scores["eng_energy"] += 3
    elif "ypodomes" in source_clean or "pedmede" in source_clean: scores["eng_projects"] += 3
    elif "pomida" in source_clean: scores["law_realestate"] += 3
    elif "lawspot" in source_clean or "dsa" in source_clean: scores["law_justice"] += 3
    elif "taxheaven" in source_clean or "capital" in source_clean: scores["finance"] += 3

    poleodomia_words = ['αυθαιρετα', '4495', 'πολεοδομ', 'δομηση', 'κτιριοδομ', 'αδειες', 'οικοδομ', 'νοκ', 'τοπογραφικ', 'ταυτοτητα κτιριου', 'συντελεστης', 'υδομ']
    for w in poleodomia_words: 
        if w in full_text: scores["eng_poleodomia"] += 2

    energy_words = ['εξοικονομω', 'φωτοβολταικ', 'ενεργεια', 'απε', 'ραε', 'υδρογονο', 'κλιματικ', 'περιβαλλον', 'ανακυκλωση', 'αποβλητα', 'net metering']
    for w in energy_words: 
        if w in full_text: scores["eng_energy"] += 2

    project_words = ['διαγωνισμ', 'δημοσια εργα', 'αναθεση', 'συμβαση', 'υποδομες', 'μετρο', 'οδικος', 'πεδμεδε', 'μειοδοτ', 'αναδοχος', 'εργοταξιο', 'κατασκευαστικ', 'γεφυρα', 'αυτοκινητοδρομος', 'σιδηροδρομ']
    for w in project_words: 
        if w in full_text: scores["eng_projects"] += 2

    estate_words = ['συμβολαιογραφ', 'μεταβιβαση', 'γονικη παροχη', 'κληρονομι', 'διαθηκη', 'αντικειμενικ', 'enfia', 'υποθηκοφυλακ', 'κτηματολογιο', 'ε9', 'ακινητ']
    for w in estate_words: 
        if w in full_text: scores["law_realestate"] += 2

    disaster_words = ['ηφαιστειο', 'σεισμος', 'χιονια', 'κακοκαιρια', 'πυρκαγια', 'φωτια', 'πλημμυρα', 'καιρος']
    is_disaster = any(w in full_text for w in disaster_words)
    justice_words = ['δικαστηρι', 'αρεοπαγ', 'στε', 'ποινικ', 'αστικ', 'δικη', 'αγωγη', 'δικηγορ', 'ολομελεια', 'παραβαση', 'κατηγορουμεν', 'εφετειο', 'νομικο συμβουλιο']
    found_justice_words = sum(1 for w in justice_words if w in full_text)
    
    if is_disaster and found_justice_words < 2: scores["law_justice"] = -10 
    else: scores["law_justice"] += (found_justice_words * 2)

    fin_words = ['φορολογ', 'ααδε', 'mydata', 'εφορια', 'φπα', 'μισθοδοσια', 'τραπεζ', 'δανει', 'εφκα', 'συνταξ', 'τεκμηρια', 'οφειλ']
    for w in fin_words: 
        if w in full_text: scores["finance"] += 2

    best_category = max(scores, key=scores.get)
    if scores[best_category] < 2:
        if any(w in full_text for w in ['εκλογες', 'παραταση', 'ανακοινωση']): return "📢 Θεσμικά & Ανακοινώσεις"
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

# --- 4. BACKEND FUNCTIONS ---
def get_db_connection():
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        gc = gspread.service_account_from_dict(credentials_dict)
        return gc.open("laws_database").sheet1
    except: return None

def load_data():
    sheet = get_db_connection()
    return sheet.get_all_records() if sheet else []

def get_badge_class(category):
    if "Μηχανικοί" in category: return "badge-eng"
    if "Νομικά" in category or "Συμβολαιο" in category: return "badge-law"
    if "Νομοθεσία" in category: return "badge-fek"
    return "badge-gen"

def reset_database():
    """ΣΒΗΝΕΙ ΤΑ ΠΑΝΤΑ ΕΚΤΟΣ ΑΠΟ ΤΟΥΣ ΤΙΤΛΟΥΣ"""
    sheet = get_db_connection()
    if not sheet: return False
    try:
        # Καθαρίζει τα περιεχόμενα από τη 2η γραμμή και κάτω (A2:G1000)
        sheet.batch_clear(["A2:G5000"])
        return True
    except:
        return False

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

# --- 5. UI LAYOUT ---
st.markdown("""
<div class="header-bar">
    <div style="font-size: 2.2rem; font-weight: 800;">🏛️ NomoTechi</div>
    <div style="font-size: 1rem; opacity: 0.9;">Η Ενιαία Πύλη για Μηχανικούς, Δικηγόρους & Συμβολαιογράφους</div>
</div>
""", unsafe_allow_html=True)

data = load_data()
df = pd.DataFrame(data)

tabs = st.tabs(["🏠 Όλα (Ροή)", "📐 Μηχανικοί", "⚖️ Νομικοί / Συμβ.", "📜 Νομοθεσία (ΦΕΚ)", "⚙️ Admin"])

if not df.empty:
    df = df.iloc[::-1].reset_index(drop=True)

    with tabs[0]: # HOME
        hero = df.iloc[0]
        badge_style = get_badge_class(hero['category'])
        st.markdown(f"""
        <div style="background:white; padding:30px; border-radius:15px; border-left:5px solid #0F172A; box-shadow:0 10px 15px -3px rgba(0,0,0,0.1); margin-bottom:30px;">
            <span class="cat-badge {badge_style}">{hero['category']}</span>
            <div style="font-size:1.8rem; font-weight:800; margin-top:10px; line-height:1.2;">
                <a href="{hero['link']}" target="_blank">{hero['title']}</a>
            </div>
            <div style="color:#475569; margin-top:10px; font-size:1.1rem;">{hero['content']}</div>
            <div style="margin-top:15px; font-size:0.9rem; color:#94A3B8;">📅 {hero['last_update']} • Πηγή: {hero['law']}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### 🔔 Πρόσφατη Ενημέρωση")
        cols = st.columns(3)
        for i, col in enumerate(cols):
            if i + 1 < len(df):
                row = df.iloc[i+1]
                badge = get_badge_class(row['category'])
                with col:
                    st.markdown(f"""
                    <div class="news-card">
                        <div>
                            <span class="cat-badge {badge}">{row['category'].split(':')[0]}</span>
                            <div style="font-weight:700; font-size:1.1rem; margin-bottom:10px;"><a href="{row['link']}" target="_blank">{row['title']}</a></div>
                            <div style="font-size:0.9rem; color:#64748B;">{row['content'][:100]}...</div>
                        </div>
                        <div style="font-size:0.8rem; color:#94A3B8; margin-top:15px; border-top:1px solid #f1f5f9; padding-top:10px;">{row['law']} • {row['last_update']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    with tabs[1]: # ENGINEERS
        st.caption("Πολεοδομία, Ενέργεια, Δημόσια Έργα & Τεχνική Νομοθεσία")
        eng_df = df[df['category'].str.contains("Μηχανικ|Πολεοδομ|Ενέργεια|Έργα|Θεσμικά", case=False)]
        for idx, row in eng_df.iterrows():
            st.markdown(f"""<div style="padding:15px; border-bottom:1px solid #E2E8F0; background:white;"><span class="cat-badge badge-eng">{row['category']}</span><span style="font-size:1.1rem; font-weight:700; margin-left:10px;"><a href="{row['link']}" target="_blank">{row['title']}</a></span><div style="color:#64748B; font-size:0.9rem; margin-top:5px;">{row['law']} • {row['last_update']}</div></div>""", unsafe_allow_html=True)

    with tabs[2]: # LAWYERS
        st.caption("Νομικά Θέματα, Δικαστήρια, Κτηματολόγιο, Συμβόλαια")
        law_df = df[df['category'].str.contains("Νομικ|Συμβολαιο|Δικηγόρ|Φορολογ", case=False)]
        for idx, row in law_df.iterrows():
            st.markdown(f"""<div style="padding:15px; border-bottom:1px solid #E2E8F0; background:white;"><span class="cat-badge badge-law">{row['category']}</span><span style="font-size:1.1rem; font-weight:700; margin-left:10px;"><a href="{row['link']}" target="_blank">{row['title']}</a></span><div style="color:#64748B; font-size:0.9rem; margin-top:5px;">{row['law']} • {row['last_update']}</div></div>""", unsafe_allow_html=True)

    with tabs[3]: # FEK
        st.info("📜 Εμφάνιση αποκλειστικά ΦΕΚ, Εγκυκλίων και Νομοθεσίας.")
        fek_df = df[df['category'].str.contains("Νομοθεσία|ΦΕΚ", case=False)]
        for idx, row in fek_df.iterrows():
            st.markdown(f"""<div style="background:#F0FDF4; padding:20px; border-radius:10px; margin-bottom:10px; border:1px solid #BBF7D0;"><span style="color:#16A34A; font-weight:800;">ΦΕΚ / ΑΠΟΦΑΣΗ</span> | <span style="font-size:0.9rem; color:#666;">{row['law']}</span><div style="font-size:1.2rem; font-weight:700; margin-top:5px;"><a href="{row['link']}" target="_blank" style="color:#14532D!important;">{row['title']}</a></div><div style="margin-top:10px; color:#374151;">{row['content']}</div></div>""", unsafe_allow_html=True)

with tabs[4]: # ADMIN
    st.header("Διαχείριση")
    pw = st.text_input("Κωδικός Διαχειριστή", type="password")
    
    if pw == st.secrets.get("admin_password", ""):
        st.success("Admin Access: OK")
        
        col1, col2 = st.columns(2)
        
        # ΚΟΥΜΠΙ 1: ΣΑΡΩΣΗ
        with col1:
            st.subheader("🔄 Ενημέρωση (Update)")
            st.write("Ψάχνει ΜΟΝΟ για νέα άρθρα (δεν πειράζει τα παλιά).")
            if st.button("🚀 Force Scan", type="primary"):
                with st.spinner("Γίνεται σάρωση..."):
                    new_count = run_force_scan()
                if new_count > 0:
                    st.success(f"Βρέθηκαν {new_count} νέα άρθρα!")
                    time.sleep(1)
                    st.rerun()
                else: st.info("Δεν βρέθηκαν νέα άρθρα.")

        # ΚΟΥΜΠΙ 2: ΟΛΙΚΗ ΕΠΑΝΕΚΚΙΝΗΣΗ (ΤΟ ΝΕΟ ΚΟΥΜΠΙ)
        with col2:
            st.subheader("🗑️ Διαγραφή & Επανεκκίνηση")
            st.write("⚠️ Σβήνει ΟΛΑ τα άρθρα για να τα ξανα-κατεβάσει σωστά.")
            if st.button("🔴 RESET DATABASE (Ολική Διαγραφή)"):
                with st.spinner("Καθαρισμός βάσης..."):
                    success = reset_database()
                    st.cache_data.clear()
                if success:
                    st.warning("Η βάση άδειασε! Πατήστε τώρα 'Force Scan' για να γεμίσει σωστά.")
                else:
                    st.error("Σφάλμα κατά τη διαγραφή.")

        st.divider()
        st.subheader("Raw Data Preview")
        st.dataframe(df)
