import sqlite3

# Connect to the database
conn = sqlite3.connect('bookstore.db')
cursor = conn.cursor()

# Add new columns if they don’t exist
try:
    cursor.execute("ALTER TABLE Books ADD COLUMN publisher TEXT")
    print("Added 'publisher' column.")
except sqlite3.OperationalError as e:
    print(f"'publisher' column already exists or error: {e}")

try:
    cursor.execute("ALTER TABLE Books ADD COLUMN date_published TEXT")
    print("Added 'date_published' column.")
except sqlite3.OperationalError as e:
    print(f"'date_published' column already exists or error: {e}")

# Optional: Update Sample Book with sample data
cursor.execute("""
    UPDATE Books 
    SET publisher = 'Sample Publisher', 
        date_published = '2023-01-15',
        cover_image = 'https://via.placeholder.com/150',
        description = 'A thrilling tale of adventure and mystery in a secret-filled world.'
    WHERE title = 'Sample Book'
""")
print("Updated 'Sample Book' with publisher, date_published, cover_image, and description.")

# Commit changes and close
conn.commit()
conn.close()

print("Database updated successfully!")