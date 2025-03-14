import sqlite3

# Connect to the database
conn = sqlite3.connect('bookstore.db')
cursor = conn.cursor()

# Check current schema
cursor.execute("PRAGMA table_info(Books)")
columns = [col[1] for col in cursor.fetchall()]
print("Current columns in Books table:", columns)

# Add publisher if not exists
if 'publisher' not in columns:
    cursor.execute("ALTER TABLE Books ADD COLUMN publisher TEXT")
    print("Added 'publisher' column.")
else:
    print("'publisher' column already exists.")

# Add date_published if not exists
if 'date_published' not in columns:
    cursor.execute("ALTER TABLE Books ADD COLUMN date_published TEXT")
    print("Added 'date_published' column.")
else:
    print("'date_published' column already exists.")

# Update Sample Book with sample data
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