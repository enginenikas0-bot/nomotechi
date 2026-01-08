import streamlit as st
import pandas as pd
import json
import os
import bot_updater  # <--- ΕΙΣΑΓΟΥΜΕ ΤΟ ΡΟΜΠΟΤΑΚΙ ΕΔΩ

# Ρυθμίσεις σελίδας
st.set_page_config(page_title="NomoTechi Live", layout="wide")

# --- ΣΥΝΑΡΤΗΣΗ ΦΟΡΤΩΣΗΣ ΔΕΔΟΜΕΝΩΝ ---
def load_data():
    if not os.path.exists('laws_db.json'):
        return []
    with open('laws_db.json', 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return []

# --- SIDEBAR ---
st.sidebar.title("🏗️ NomoTechi Live")

# ΚΟΥΜΠΙ ΑΝΑΝΕΩΣΗΣ (ΝΕΟ)
if st.sidebar.button("🔄 Λήψη Νέων Ειδήσεων Τώρα"):
    with st.spinner('Το ρομποτάκι ψάχνει για ειδήσεις...'):
        bot_updater.run_bot() # Τρέχει το ρομποτάκι
    st.success("Η ενημέρωση ολοκληρώθηκε!")
    st.rerun() # Κάνει επανεκκίνηση τη σελίδα για να δείξει τα νέα

menu = st.sidebar.radio("Μενού", ["Νέα Ροή (Live)", "Αναζήτηση"])

# Φόρτωση δεδομένων
data = load_data()
df = pd.DataFrame(data) if data else pd.DataFrame()

# --- ΚΥΡΙΩΣ ΕΦΑΡΜΟΓΗ ---
if menu == "Νέα Ροή (Live)":
    st.title("⚡ Τελευταίες Ενημερώσεις")
    
    if not df.empty:
        # Ταξινόμηση: Τα πιο πρόσφατα πάνω-πάνω
        df_sorted = df.sort_values(by="id", ascending=False)
        
        for index, row in df_sorted.iterrows():
            with st.container():
                st.subheader(f"{row['title']}")
                st.caption(f"Πηγή: {row['law']} | {row['last_update']}")
                st.write(row['content'])
                if 'link' in row:
                    st.markdown(f"[Διαβάστε το άρθρο εδώ]({row['link']})")
                st.divider()
    else:
        st.info("Δεν υπάρχουν ειδήσεις ακόμα. Πατήστε το κουμπί ανανέωσης!")

elif menu == "Αναζήτηση":
    st.header("🔍 Αναζήτηση")
    search = st.text_input("Λέξη κλειδί")
    if search and not df.empty:
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        st.table(df[mask][['title', 'last_update']])
    