import sqlite3
import os

# Use the path from find_db.py (adjust if different)
db_path = r"C:\Users\jchul\BookstoreFE\bookstore.db"  # Update this if find_db.py shows a different path
if not os.path.exists(db_path):
    print(f"Error: {db_path} does not exist! Check your app’s database location.")
    exit()

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Debug: List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables found:", cursor.fetchall())

# Add cover_image column if missing
try:
    cursor.execute("ALTER TABLE Books ADD COLUMN cover_image TEXT")
    print("Added 'cover_image' column to Books table.")
except sqlite3.OperationalError:
    print("'cover_image' column already exists, skipping addition.")

# Update existing rows with ISBN-based URLs
cursor.execute("UPDATE Books SET cover_image = 'http://covers.openlibrary.org/b/isbn/' || isbn || '-M.jpg' WHERE cover_image IS NULL")
print(f"Updated {cursor.rowcount} books with cover image URLs.")

# Commit and close
conn.commit()
conn.close()

print("Database migration complete!")