import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class DatabaseHelper:
    def __init__(self, db_path='bookstore.db'):
        self.db_path = db_path
        self._initialize_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                street TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                zipcode TEXT NOT NULL,
                mailing_street TEXT,
                mailing_city TEXT,
                mailing_state TEXT,
                mailing_zipcode TEXT,
                favorite_genre TEXT,
                role TEXT DEFAULT 'customer'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT,
                price REAL NOT NULL,
                quantity INTEGER DEFAULT 0,
                cover_image TEXT,
                isbn TEXT,
                description TEXT,
                publisher TEXT,
                date_published TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Wishlist (
                wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (customer_email) REFERENCES Users(email),
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        ''')
        cursor.execute('DROP TABLE IF EXISTS Cart')
        cursor.execute('''
            CREATE TABLE Cart (
                cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (customer_email) REFERENCES Users(email),
                FOREIGN KEY (book_id) REFERENCES Books(book_id),
                UNIQUE (customer_email, book_id)
            )
        ''')
        cursor.execute('DROP TABLE IF EXISTS Orders')
        cursor.execute('''
            CREATE TABLE Orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                shipping_street TEXT,
                shipping_city TEXT,
                shipping_state TEXT,
                shipping_zipcode TEXT,
                payment_method TEXT,
                quantity INTEGER NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                FOREIGN KEY (customer_email) REFERENCES Users(email),
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        ''')
        cursor.execute('DROP TABLE IF EXISTS SupplierOrders')
        cursor.execute('''
            CREATE TABLE SupplierOrders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                FOREIGN KEY (book_id) REFERENCES Books(book_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_email TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                review_date TEXT NOT NULL,
                FOREIGN KEY (customer_email) REFERENCES Users(email),
                FOREIGN KEY (book_id) REFERENCES Books(book_id),
                UNIQUE (customer_email, book_id)
            )
        ''')
        cursor.execute("DELETE FROM Users WHERE username = 'admin'")
        admin_password = generate_password_hash('admintest')
        cursor.execute("""
            INSERT INTO Users (first_name, last_name, email, username, password, street, city, state, zipcode, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('Admin', 'User', 'admin@example.com', 'admin', admin_password, '123 Admin St', 'Admin City', 'AS', '12345', 'admin'))
        cursor.execute("DELETE FROM Users WHERE username = 'testuser'")
        customer_password = generate_password_hash('testpass')
        cursor.execute("""
            INSERT INTO Users (first_name, last_name, email, username, password, street, city, state, zipcode, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('Test', 'User', 'test@example.com', 'testuser', customer_password, '456 Test St', 'Test City', 'TS', '67890', 'customer'))
        cursor.execute("SELECT COUNT(*) as count FROM Books")
        book_count = cursor.fetchone()['count']
        if book_count == 0:
            cursor.execute("""
                INSERT INTO Books (title, author, genre, price, quantity, isbn, publisher, date_published)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ('Sample Book', 'Jane Doe', 'Fiction', 9.99, 10, '978-0-7475-3269-9', 'Penguin Books', '2020-01-15'))
            print("Added Sample Book to empty Books table")
        conn.commit()
        cursor.execute("SELECT username, password, role FROM Users WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        if admin_user:
            print(f"Admin user created: username={admin_user['username']}, password_hash={admin_user['password']}, role={admin_user['role']}")
        else:
            print("ERROR: Admin user not created!")
        cursor.execute("SELECT username, password, role FROM Users WHERE username = 'testuser'")
        test_user = cursor.fetchone()
        if test_user:
            print(f"Test user created: username={test_user['username']}, password_hash={test_user['password']}, role={test_user['role']}")
        else:
            print("ERROR: Test user not created!")
        conn.close()
        print("Database initialized successfully")

    def get_all_books(self, page, per_page, search_query=None, sort='default'):
        conn = self._get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM Books"
        count_query = "SELECT COUNT(*) as total FROM Books"
        params = []
        if search_query:
            search_term = f"%{search_query}%"
            where_clause = " WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?"
            query += where_clause
            count_query += where_clause
            params.extend([search_term, search_term, search_term])
        if sort == 'title_asc':
            query += " ORDER BY title ASC"
        elif sort == 'title_desc':
            query += " ORDER BY title DESC"
        elif sort == 'price_asc':
            query += " ORDER BY price ASC"
        elif sort == 'price_desc':
            query += " ORDER BY price DESC"
        offset = (page - 1) * per_page
        query += " LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        cursor.execute(count_query, params[:3] if search_query else [])
        total_books = cursor.fetchone()['total']
        cursor.execute(query, params)
        books = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return books, total_books

    def get_book_by_id(self, book_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Books WHERE book_id = ?", (book_id,))
        book = cursor.fetchone()
        conn.close()
        return dict(book) if book else None

    def login_user(self, identifier, password):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email = ? OR username = ?", (identifier, identifier))
        user = cursor.fetchone()
        conn.close()
        if user:
            print(f"DEBUG: Found user - username: {user['username']}, role: {user['role']}, password hash: {user['password']}")
            if check_password_hash(user['password'], password):
                print(f"DEBUG: Password match for {identifier}")
                return dict(user)
            else:
                print(f"DEBUG: Password mismatch for {identifier} - entered: {password}")
        else:
            print(f"DEBUG: No user found for identifier {identifier}")
        return None

    def get_user_role(self, identifier):
        user = self.get_user_profile_by_identifier(identifier)
        return user.get('role', 'customer') if user else 'customer'

    def get_user_profile_by_identifier(self, identifier):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email = ? OR username = ?", (identifier, identifier))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    def register_user(self, first_name, last_name, email, username, password, street, city, state, zipcode, mailing_street=None, mailing_city=None, mailing_state=None, mailing_zipcode=None, favorite_genre=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO Users (first_name, last_name, email, username, password, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode, favorite_genre, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'customer')
            """, (first_name, last_name, email, username, hashed_password, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode, favorite_genre))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def add_to_wishlist(self, customer_email, book_id, quantity=1):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Wishlist (customer_email, book_id, quantity) VALUES (?, ?, ?)", 
                           (customer_email, book_id, quantity))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def remove_from_wishlist(self, customer_email, book_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Wishlist WHERE customer_email = ? AND book_id = ?", (customer_email, book_id))
        conn.commit()
        conn.close()

    def get_user_wishlist(self, customer_email):
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

    def add_to_cart(self, customer_email, book_id, quantity):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Cart (customer_email, book_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT (customer_email, book_id) DO UPDATE SET quantity = quantity + ?
        """, (customer_email, book_id, quantity, quantity))
        conn.commit()
        conn.close()

    def get_user_cart(self, customer_email):
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

    def update_cart_quantity(self, customer_email, book_id, quantity):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Cart SET quantity = ? WHERE customer_email = ? AND book_id = ?", (quantity, customer_email, book_id))
        conn.commit()
        conn.close()

    def remove_from_cart(self, customer_email, book_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Cart WHERE customer_email = ? AND book_id = ?", (customer_email, book_id))
        conn.commit()
        conn.close()

    def clear_cart(self, customer_email):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Cart WHERE customer_email = ?", (customer_email,))
        conn.commit()
        conn.close()

    def get_user_orders(self, customer_email):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.*, b.title, b.price 
            FROM Orders o 
            JOIN Books b ON o.book_id = b.book_id
            WHERE o.customer_email = ?
        ''', (customer_email,))
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders

    def update_user_profile(self, old_email, first_name, last_name, new_email, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode, favorite_genre=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Users 
            SET first_name = ?, last_name = ?, email = ?, street = ?, city = ?, state = ?, zipcode = ?, 
                mailing_street = ?, mailing_city = ?, mailing_state = ?, mailing_zipcode = ?, favorite_genre = ?
            WHERE email = ?
        """, (first_name, last_name, new_email, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode, favorite_genre, old_email))
        conn.commit()
        conn.close()

    def get_all_orders(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.*, b.title, b.price 
            FROM Orders o 
            JOIN Books b ON o.book_id = b.book_id
        ''')
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders

    def get_all_supplier_orders(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT so.*, b.title 
            FROM SupplierOrders so 
            JOIN Books b ON so.book_id = b.book_id
        ''')
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return orders

    def add_book(self, title, author, genre, price, quantity, isbn, description, publisher, date_published):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Books (title, author, genre, price, quantity, isbn, description, publisher, date_published)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, author, genre, price, quantity, isbn, description, publisher, date_published))
        conn.commit()
        conn.close()

    def update_book(self, book_id, title, author, genre, price, quantity, isbn, description, publisher, date_published):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Books 
            SET title = ?, author = ?, genre = ?, price = ?, quantity = ?, isbn = ?, description = ?, publisher = ?, date_published = ?
            WHERE book_id = ?
        """, (title, author, genre, price, quantity, isbn, description, publisher, date_published, book_id))
        conn.commit()
        conn.close()

    def update_book_quantity(self, book_id, quantity):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Books SET quantity = ? WHERE book_id = ?", (quantity, book_id))
        conn.commit()
        conn.close()

    def remove_book(self, book_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Wishlist WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM Cart WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM Orders WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM SupplierOrders WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM Books WHERE book_id = ?", (book_id,))
        conn.commit()
        conn.close()

    def add_supplier_order(self, supplier, book_id, quantity, price):
        conn = self._get_connection()
        cursor = conn.cursor()
        total = quantity * price
        print(f"DEBUG: Adding supplier order - Supplier: {supplier}, Book ID: {book_id}, Quantity: {quantity}, Price: {price}, Total: {total}")
        cursor.execute("""
            INSERT INTO SupplierOrders (supplier, book_id, quantity, price, total, order_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (supplier, book_id, quantity, price, total, datetime.now().isoformat(), 'Pending'))
        conn.commit()
        conn.close()
        return total

    def cancel_supplier_order(self, order_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM SupplierOrders WHERE order_id = ?", (order_id,))
        order = cursor.fetchone()
        if order and order['status'] == 'Pending':
            cursor.execute("UPDATE SupplierOrders SET status = 'Canceled' WHERE order_id = ?", (order_id,))
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False

    def get_all_wishlists(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.customer_email, b.title
            FROM Wishlist w
            JOIN Books b ON w.book_id = b.book_id
        ''')
        wishlists = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return wishlists

    def get_all_users(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email, first_name, last_name, street, city, state, zipcode FROM Users WHERE role = 'customer'")
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users

    def add_review(self, customer_email, book_id, rating, comment):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Reviews (customer_email, book_id, rating, comment, review_date)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (customer_email, book_id) DO UPDATE SET 
                rating = excluded.rating,
                comment = excluded.comment,
                review_date = excluded.review_date
        """, (customer_email, book_id, rating, comment, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_book_reviews(self, book_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, u.first_name, u.last_name
            FROM Reviews r
            JOIN Users u ON r.customer_email = u.email
            WHERE r.book_id = ?
        ''', (book_id,))
        reviews = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return reviews

    def get_all_reviews(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, u.first_name, u.last_name, b.title
            FROM Reviews r
            JOIN Users u ON r.customer_email = u.email
            JOIN Books b ON r.book_id = b.book_id
            ORDER BY r.review_date DESC
        ''')
        reviews = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return reviews

if __name__ == "__main__":
    db = DatabaseHelper()
    print("Database initialized successfully")