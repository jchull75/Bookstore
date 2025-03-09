import sqlite3

conn = sqlite3.connect("bookstore.db")
cursor = conn.cursor()
cursor.execute("SELECT title, isbn FROM Books ORDER BY title")
books = cursor.fetchall()
print("All books:")
for book in books:
    print(f"Title: {book[0]}, ISBN: {book[1]}")
cursor.execute("SELECT COUNT(*) FROM Books")
print(f"Total books: {cursor.fetchone()[0]}")
conn.close()