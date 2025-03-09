import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseHelper:
    def __init__(self, db_path='bookstore.db'):
        self.db_path = db_path
        self._initialize_db()

    def _get_connection(self):
        """Establish a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self):
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Wishlist (
                wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                FOREIGN KEY (customer_email) REFERENCES Users(email),
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Cart (
                cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (customer_email) REFERENCES Users(email),
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        ''')

        conn.commit()
        conn.close()

    def add_to_wishlist(self, customer_email, book_id):
        """Fix: Add books to wishlist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Wishlist (customer_email, book_id) VALUES (?, ?)", 
                           (customer_email, book_id))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Ignore duplicate entries
        finally:
            conn.close()

    def get_user_wishlist(self, customer_email):
        """Retrieve user wishlist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.*, b.title, b.price 
            FROM Wishlist w 
            JOIN Books b ON w.book_id = b.book_id
            WHERE w.customer_email = ?
        ''', (customer_email,))
        wishlist = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return wishlist

    def get_user_cart(self, customer_email):
        """Retrieve all cart items for a specific user by email."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, b.title, b.price 
            FROM Cart c 
            JOIN Books b ON c.book_id = b.book_id
            WHERE c.customer_email = ?
        ''', (customer_email,))
        cart_items = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return cart_items

if __name__ == "__main__":
    db = DatabaseHelper()
    print("✅ Database initialized successfully!")
