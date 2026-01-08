import feedparser
import json
import os
import datetime
import time

# Αρχείο βάσης δεδομένων
DB_FILE = 'laws_db.json'

# Λίστα με πραγματικές πηγές RSS (Ειδήσεις για Μηχανικούς & Νομικά)
RSS_FEEDS = {
    "Taxheaven": "https://www.taxheaven.gr/rss",
    "Lawspot": "https://www.lawspot.gr/nomika-nea/feed",
    "B2Green": "https://news.b2green.gr/feed"
}

def load_data():
    """Φορτώνει την υπάρχουσα βάση."""
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_data(data):
    """Αποθηκεύει τη βάση."""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def run_bot():
    print("🤖 Το ρομποτάκι ξεκίνησε και σκανάρει το ίντερνετ...")
    current_data = load_data()
    new_entries_count = 0

    # Σκανάρισμα κάθε πηγής
    for source_name, url in RSS_FEEDS.items():
        print(f"📡 Έλεγχος πηγής: {source_name}...")
        try:
            feed = feedparser.parse(url)
            
            # Έλεγχος αν το feed κατέβηκε σωστά
            if feed.bozo:
                print(f"⚠️ Πρόβλημα με το feed του {source_name}")
                continue

            # Παίρνουμε τα 5 πιο πρόσφατα άρθρα από κάθε πηγή
            for entry in feed.entries[:5]:
                title = entry.title
                link = entry.link
                # Καθαρισμός ημερομηνίας (αν υπάρχει)
                published = entry.get('published', datetime.datetime.now().strftime("%Y-%m-%d"))
                
                # Έλεγχος αν υπάρχει ήδη στη βάση μας (με βάση το Link)
                if any(d.get('link') == link for d in current_data):
                    continue  # Το έχουμε ήδη, προχωράμε
                
                # Δημιουργία νέας εγγραφής
                new_article = {
                    "id": len(current_data) + 1 + new_entries_count,
                    "law": source_name,  # Πηγή αντί για Νόμο
                    "article": "RSS Feed",
                    "category": "Επικαιρότητα",
                    "title": title,
                    "content": f"{entry.summary[:200]}... [Διαβάστε περισσότερα]({link})",
                    "link": link, # Αποθηκεύουμε και το link
                    "last_update": published,
                    "status": "ΝΕΟ"
                }
                
                current_data.append(new_article)
                new_entries_count += 1
                print(f"   ✅ Βρέθηκε νέο άρθρο: {title[:50]}...")

        except Exception as e:
            print(f"❌ Σφάλμα κατά τη σύνδεση με {source_name}: {e}")

    if new_entries_count > 0:
        save_data(current_data)
        print(f"\n🎉 Ολοκληρώθηκε! Προστέθηκαν {new_entries_count} νέα θέματα στη βάση.")
    else:
        print("\n💤 Δεν βρέθηκαν νέα θέματα. Η βάση είναι ενημερωμένη.")

if __name__ == "__main__":
    run_bot()