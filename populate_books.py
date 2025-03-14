import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('bookstore.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all books
cursor.execute("SELECT book_id, title, author, publisher, date_published FROM Books")
books = [dict(row) for row in cursor.fetchall()]
print(f"Found {len(books)} books in the database:")

# Print current state
for book in books:
    print(f"ID: {book['book_id']}, Title: {book['title']}, Author: {book['author']}, "
          f"Publisher: '{book['publisher']}' (type: {type(book['publisher'])}), "
          f"Date Published: '{book['date_published']}' (type: {type(book['date_published'])})")

# Sample data
sample_publishers = ["Penguin Books", "HarperCollins", "Random House", "Simon & Schuster"]
sample_dates = ["2020-01-15", "2021-06-23", "2022-09-10", "2023-03-01"]

# Force update all books with sample data
for i, book in enumerate(books):
    publisher = sample_publishers[i % len(sample_publishers)]
    date_published = sample_dates[i % len(sample_dates)]
    cursor.execute("""
        UPDATE Books 
        SET publisher = ?, date_published = ?
        WHERE book_id = ?
    """, (publisher, date_published, book['book_id']))
    print(f"Updated ID {book['book_id']} - Set Publisher: '{publisher}', Date Published: '{date_published}'")

# Commit changes
conn.commit()

# Verify updates
cursor.execute("SELECT book_id, title, publisher, date_published FROM Books")
updated_books = [dict(row) for row in cursor.fetchall()]
print("\nAfter update:")
for book in updated_books:
    print(f"ID: {book['book_id']}, Title: {book['title']}, "
          f"Publisher: '{book['publisher']}', Date Published: '{book['date_published']}'")

conn.close()
print("Database update complete!")