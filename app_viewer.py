import streamlit as st
import pandas as pd
import gspread
import feedparser
from datetime import datetime

# Ρυθμίσεις σελίδας
st.set_page_config(page_title="NomoTechi Live", layout="wide")

# --- ΣΥΝΔΕΣΗ ΜΕ GOOGLE SHEETS ---
def get_db_connection():
    # Παίρνουμε τα μυστικά κλειδιά από το Streamlit Cloud
    credentials_dict = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(credentials_dict)
    # Ανοίγουμε το Sheet με το όνομα που του έδωσες
    sh = gc.open("laws_database")
    return sh.sheet1

def load_data():
    try:
        sheet = get_db_connection()
        data = sheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης με τη βάση: {e}")
        return []

# --- ΛΕΙΤΟΥΡΓΙΑ ΡΟΜΠΟΤ (Μέσα στο App) ---
def run_bot_update():
    RSS_FEEDS = {
        "Taxheaven": "https://www.taxheaven.gr/rss",
        "B2Green": "https://news.b2green.gr/feed"
    }
    
    sheet = get_db_connection()
    existing_data = sheet.get_all_records()
    existing_links = [row['link'] for row in existing_data]
    
    new_items_found = 0
    
    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]: # Τα 3 πιο πρόσφατα
            if entry.link not in existing_links:
                # Ετοιμασία νέας γραμμής
                new_row = [
                    len(existing_data) + new_items_found + 1, # ID
                    source,
                    entry.title,
                    entry.summary[:200] + "...",
                    entry.link,
                    datetime.now().strftime("%Y-%m-%d")
                ]
                # Προσθήκη στο Google Sheet
                sheet.append_row(new_row)
                new_items_found += 1
                existing_links.append(entry.link)
    
    return new_items_found

# --- UI ΕΦΑΡΜΟΓΗΣ ---
st.sidebar.title("🏗️ NomoTechi Cloud")

if st.sidebar.button("🔄 Ενημέρωση από Google Sheets"):
    st.cache_data.clear() # Καθαρίζουμε τη μνήμη για να ξαναδιαβάσει
    st.rerun()

# Κουμπί για να τρέξει το ρομποτάκι
if st.sidebar.button("🤖 Τρέξε το Ρομποτάκι (Admin)"):
    with st.spinner("Το ρομποτάκι σκανάρει το ίντερνετ..."):
        count = run_bot_update()
    if count > 0:
        st.success(f"Βρέθηκαν {count} νέα άρθρα και γράφτηκαν στο Sheet!")
        st.cache_data.clear()
        st.rerun()
    else:
        st.info("Δεν βρέθηκαν νέες ειδήσεις.")

# Εμφάνιση Δεδομένων
st.title("📂 Νομοθεσία & Ειδήσεις")

data = load_data()
if data:
    df = pd.DataFrame(data)
    # Αντιστροφή για να δείχνει τα νέα πρώτα
    df = df.iloc[::-1]
    
    for index, row in df.iterrows():
        with st.expander(f"{row['last_update']} - {row['title']}"):
            st.write(f"**Πηγή:** {row['law']}")
            st.write(row['content'])
            st.markdown(f"[Διαβάστε το άρθρο]({row['link']})")
else:
    st.warning("Η βάση δεδομένων είναι κενή ή δεν συνδέθηκε.")
