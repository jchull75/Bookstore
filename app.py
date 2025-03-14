from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database_helper import DatabaseHelper
import os
import logging
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import re

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # TODO: Move to .env in production
app.permanent_session_lifetime = timedelta(minutes=30)  # Session timeout
db_helper = DatabaseHelper()

sort_options = {
    'default': 'Default',
    'title_asc': 'Title (A-Z)',
    'title_desc': 'Title (Z-A)',
    'price_asc': 'Price (Low to High)',
    'price_desc': 'Price (High to Low)'
}

def get_context():
    is_admin = False
    if 'user' in session:
        is_admin = db_helper.get_user_role(session['user']) == 'admin'
    return {'is_admin': is_admin}

def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return False, "Password must contain letters and numbers."
    return True, ""

@app.route('/')
def home():
    return render_template('index.html', **get_context())

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        username = request.form['username']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zipcode = request.form['zipcode']
        mailing_street = request.form.get('mailing_street')
        mailing_city = request.form.get('mailing_city')
        mailing_state = request.form.get('mailing_state')
        mailing_zipcode = request.form.get('mailing_zipcode')
        favorite_genre = request.form.get('favorite_genre')

        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message, 'danger')
            return render_template('signup.html', **get_context())

        if db_helper.register_user(first_name, last_name, email, username, password, street, city, state, zipcode, mailing_street, mailing_city, mailing_state, mailing_zipcode, favorite_genre):
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('customer_login'))
        flash('Signup failed—email or username may already be in use.', 'danger')
    return render_template('signup.html', **get_context())

@app.route('/bookstore', methods=['GET', 'POST'])
def bookstore():
    page = request.args.get('page', 1, type=int)
    per_page = 9
    search_query = request.form.get('search') if request.method == 'POST' else None
    sort = request.args.get('sort', 'default')
    books, total_books = db_helper.get_all_books(page, per_page, search_query, sort)
    
    books_with_reviews_and_images = []
    for book in books:
        book_dict = dict(book)
        book_dict['reviews'] = db_helper.get_book_reviews(book['book_id'])
        isbn = book_dict.get('isbn', '').replace('-', '')
        if isbn:
            book_dict['image_url'] = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"
        else:
            book_dict['image_url'] = "https://via.placeholder.com/200x300?text=No+Image+Available"
        books_with_reviews_and_images.append(book_dict)
    
    return render_template(
        'bookstore.html',
        books=books_with_reviews_and_images,
        page=page,
        total_pages=(total_books + per_page - 1) // per_page,
        sort=sort,
        sort_options=sort_options,
        **get_context()
    )

@app.route('/book_details/<int:book_id>', methods=['GET'])
def book_details(book_id):
    if 'user' not in session:
        flash("Please log in to view book details and perform actions.", 'warning')
        return redirect(url_for('customer_login'))
    
    book = db_helper.get_book_by_id(book_id)
    if not book:
        flash("Book not found.", 'danger')
        return redirect(url_for('bookstore'))
    
    book['reviews'] = db_helper.get_book_reviews(book_id)
    isbn = book.get('isbn', '').replace('-', '')
    book['image_url'] = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg" if isbn else "https://via.placeholder.com/200x300?text=No+Image+Available"
    return render_template('book_details_modal.html', book=book, **get_context())

@app.route('/customer_login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        user = db_helper.login_user(identifier, password)
        if user:
            role = user.get('role', 'customer')
            if role == 'customer':
                session.permanent = True
                session['user'] = identifier
                cart_items = db_helper.get_user_cart(identifier)
                session['cart_count'] = sum(item['quantity'] for item in cart_items)
                flash('Login successful!', 'success')
                return redirect(url_for('customer_home'))
            else:
                flash('This is an admin account. Use Admin Login.', 'danger')
        else:
            flash('Invalid credentials', 'danger')
    return render_template('customer_login.html', **get_context())

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        user = db_helper.login_user(identifier, password)
        if user:
            role = user.get('role', 'customer')
            if role == 'admin':
                session.permanent = True
                session['user'] = identifier
                logger.debug(f"Admin login successful - User: {identifier}")
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('This is not an admin account. Use Customer Login.', 'danger')
        else:
            flash('Invalid credentials', 'danger')
            logger.debug(f"Admin login failed - Identifier: {identifier}")
    return render_template('admin_login.html', **get_context())

@app.route('/customer_home', methods=['GET'])
def customer_home():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('customer_login'))
    
    user = db_helper.get_user_profile_by_identifier(session['user'])
    if not user:
        flash('User not found. Please log in again.', 'danger')
        session.pop('user', None)
        return redirect(url_for('customer_login'))
    
    orders = db_helper.get_user_orders(user['email'])
    wishlist = db_helper.get_user_wishlist(user['email'])
    cart_items = db_helper.get_user_cart(user['email'])
    cart_total = sum(item['price'] * item['quantity'] for item in cart_items) if cart_items else 0

    # Fetch book recommendations using DatabaseHelper connection
    recommendations = []
    conn = db_helper._get_connection()  # Use DatabaseHelper's connection with row_factory
    cursor = conn.cursor()

    # 1. Recommendations based on favorite genre
    favorite_genre = user.get('favorite_genre')
    if favorite_genre:
        cursor.execute("""
            SELECT b.book_id, b.title, b.author, b.genre, b.price, b.isbn
            FROM Books b
            WHERE b.genre = ? AND b.quantity > 0
            ORDER BY RANDOM()
            LIMIT 5
        """, (favorite_genre,))
        genre_books = cursor.fetchall()
        recommendations.extend([
            {
                'book_id': book['book_id'],
                'title': book['title'],
                'author': book['author'],
                'genre': book['genre'],
                'price': book['price'],
                'image_url': f"https://covers.openlibrary.org/b/isbn/{book['isbn'].replace('-', '')}-M.jpg" if book['isbn'] else "https://via.placeholder.com/200x300?text=No+Image+Available"
            } for book in genre_books
        ])

    # 2. Recommendations based on past orders
    cursor.execute("""
        SELECT DISTINCT b.book_id, b.title, b.author, b.genre, b.price, b.isbn
        FROM Orders o
        JOIN Books b ON o.book_id = b.book_id
        WHERE o.customer_email = ? AND b.quantity > 0 AND b.genre IS NOT NULL
    """, (user['email'],))
    ordered_books = cursor.fetchall()
    ordered_genres = set(book['genre'] for book in ordered_books if book['genre'])
    
    if ordered_genres:
        placeholders = ','.join('?' for _ in ordered_genres)
        cursor.execute(f"""
            SELECT b.book_id, b.title, b.author, b.genre, b.price, b.isbn
            FROM Books b
            WHERE b.genre IN ({placeholders}) AND b.quantity > 0
            AND b.book_id NOT IN (
                SELECT book_id FROM Orders WHERE customer_email = ?
            )
            ORDER BY RANDOM()
            LIMIT 5
        """, tuple(ordered_genres) + (user['email'],))
        related_books = cursor.fetchall()
        recommendations.extend([
            {
                'book_id': book['book_id'],
                'title': book['title'],
                'author': book['author'],
                'genre': book['genre'],
                'price': book['price'],
                'image_url': f"https://covers.openlibrary.org/b/isbn/{book['isbn'].replace('-', '')}-M.jpg" if book['isbn'] else "https://via.placeholder.com/200x300?text=No+Image+Available"
            } for book in related_books
        ])

    conn.close()

    # Remove duplicates and limit to 5 recommendations
    seen_ids = set()
    unique_recommendations = []
    for rec in recommendations:
        if rec['book_id'] not in seen_ids:
            unique_recommendations.append(rec)
            seen_ids.add(rec['book_id'])
        if len(unique_recommendations) >= 5:
            break

    return render_template('customer_home.html', 
                           profile=user, 
                           orders=orders, 
                           wishlist=wishlist, 
                           cart_items=cart_items, 
                           cart_total=cart_total, 
                           recommendations=unique_recommendations, 
                           **get_context())

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    return redirect(url_for('customer_home'))

@app.route('/customer_info', methods=['GET', 'POST'])
def customer_info():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('customer_login'))
    
    user = db_helper.get_user_profile_by_identifier(session['user'])
    if not user:
        flash('User not found. Please log in again.', 'danger')
        session.pop('user', None)
        return redirect(url_for('customer_login'))
    
    if request.method == 'POST':
        try:
            db_helper.update_user_profile(
                user['email'],
                request.form['first_name'],
                request.form['last_name'],
                request.form['email'],
                request.form['street'],
                request.form['city'],
                request.form['state'],
                request.form['zipcode'],
                request.form.get('mailing_street', user['mailing_street']),
                request.form.get('mailing_city', user['mailing_city']),
                request.form.get('mailing_state', user['mailing_state']),
                request.form.get('mailing_zipcode', user['mailing_zipcode']),
                request.form.get('favorite_genre', user.get('favorite_genre'))
            )
            session['user'] = request.form['email']  # Update session if email changes
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating profile: {e}', 'danger')
        return redirect(url_for('customer_home'))
    
    # Fetch unique genres from Books table for dropdown
    conn = sqlite3.connect('bookstore.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT genre FROM Books WHERE genre IS NOT NULL ORDER BY genre")
    genres = [row[0] for row in cursor.fetchall()]
    conn.close()

    return render_template('customer_info.html', profile=user, genres=genres, **get_context())

@app.route('/order_tracking', methods=['GET'])
def order_tracking():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('customer_login'))
    
    user = db_helper.get_user_profile_by_identifier(session['user'])
    if not user:
        flash('User not found. Please log in again.', 'danger')
        session.pop('user', None)
        return redirect(url_for('customer_login'))
    
    orders = db_helper.get_user_orders(user['email'])
    return render_template('order_tracking.html', orders=orders, **get_context())

@app.route('/wishlist', methods=['GET', 'POST'])
def wishlist():
    if 'user' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('customer_login'))
    
    user = db_helper.get_user_profile_by_identifier(session['user'])
    if not user:
        flash('User not found. Please log in again.', 'danger')
        session.pop('user', None)
        return redirect(url_for('customer_login'))
    
    if request.method == 'POST':
        book_id = request.form.get('book_id')
        if not book_id:
            flash('Invalid book selection.', 'danger')
            return redirect(url_for('wishlist'))
        
        if 'add_to_cart' in request.form:
            quantity = int(request.form.get('quantity', 1))
            if quantity > 0:
                db_helper.add_to_cart(user['email'], book_id, quantity)
                session['cart_count'] = sum(item['quantity'] for item in db_helper.get_user_cart(user['email']))
                flash('Book added to cart!', 'success')
            else:
                flash('Quantity must be positive!', 'danger')
        elif 'remove' in request.form:
            db_helper.remove_from_wishlist(user['email'], book_id)
            flash('Book removed from wishlist!', 'success')
        
        return redirect(url_for('customer_home'))
    
    wishlist = db_helper.get_user_wishlist(user['email'])
    return render_template('wishlist.html', wishlist=wishlist, **get_context())

@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'user' not in session:
        flash("You must be logged in to add books to your wishlist.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    book_id = request.form.get('book_id')
    if not book_id:
        flash("Invalid book selection.", 'danger')
        return redirect(url_for('bookstore'))
    db_helper.add_to_wishlist(customer_email, book_id)
    flash("Book added to your wishlist!", 'success')
    return redirect(url_for('bookstore'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user' not in session:
        flash("You must be logged in to add books to your cart.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    book_id = request.form.get('book_id')
    quantity = int(request.form.get('quantity', 1))
    if not book_id or quantity < 1:
        flash("Invalid book or quantity.", 'danger')
        return redirect(url_for('bookstore'))
    db_helper.add_to_cart(customer_email, book_id, quantity)
    cart_items = db_helper.get_user_cart(customer_email)
    session['cart_count'] = sum(item['quantity'] for item in cart_items)
    flash("Book added to your cart!", 'success')
    return redirect(url_for('bookstore'))

@app.route('/add_to_cart_from_wishlist', methods=['POST'])
def add_to_cart_from_wishlist():
    if 'user' not in session:
        flash("You must be logged in to add books to your cart.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    book_id = request.form.get('book_id')
    quantity = int(request.form.get('quantity', 1))
    if not book_id or quantity < 1:
        flash("Invalid book or quantity.", 'danger')
        return redirect(url_for('customer_home'))
    db_helper.add_to_cart(customer_email, book_id, quantity)
    cart_items = db_helper.get_user_cart(customer_email)
    session['cart_count'] = sum(item['quantity'] for item in cart_items)
    flash("Book added to your cart!", 'success')
    return redirect(url_for('customer_home'))

@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'user' not in session:
        flash("You must be logged in to manage your wishlist.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    book_id = request.form.get('book_id')
    if not book_id:
        flash("Invalid book selection.", 'danger')
        return redirect(url_for('customer_home'))
    db_helper.remove_from_wishlist(customer_email, book_id)
    flash('Book removed from wishlist!', 'success')
    return redirect(url_for('customer_home'))

@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    if 'user' not in session:
        flash("You must be logged in to cancel orders.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    order_id = request.form.get('order_id')
    if not order_id:
        flash("Invalid order selection.", 'danger')
        return redirect(url_for('customer_home'))

    conn = sqlite3.connect('bookstore.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status, book_id, quantity FROM Orders WHERE order_id = ? AND customer_email = ?", (order_id, customer_email))
    order = cursor.fetchone()
    if order and order['status'] == 'Pending':
        cursor.execute("UPDATE Orders SET status = 'Canceled' WHERE order_id = ?", (order_id,))
        cursor.execute("UPDATE Books SET quantity = quantity + ? WHERE book_id = ?", (order['quantity'], order['book_id']))
        conn.commit()
        flash('Order canceled successfully!', 'success')
    else:
        flash('Order cannot be canceled—it is not pending.', 'danger')
    conn.close()
    return redirect(url_for('customer_home'))

@app.route('/buy_now', methods=['POST'])
def buy_now():
    if 'user' not in session:
        flash("You must be logged in to buy books.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    book_id = request.form.get('book_id')
    quantity = 1
    payment_method = request.form.get('payment_method')
    card_number = request.form.get('card_number')
    expiry_date = request.form.get('expiry_date')
    cvv = request.form.get('cvv')
    
    if not book_id:
        flash("Invalid book selection.", 'danger')
        return redirect(url_for('bookstore'))
    
    if not payment_method:
        flash("Please select a payment method.", 'danger')
        return redirect(url_for('bookstore'))
    
    book = db_helper.get_book_by_id(book_id)
    if book and book['quantity'] >= quantity:
        user = db_helper.get_user_profile_by_identifier(customer_email)
        if not user:
            flash("User not found.", 'danger')
            return redirect(url_for('customer_login'))
        shipping_street = user['street']
        shipping_city = user['city']
        shipping_state = user['state']
        shipping_zipcode = user['zipcode']
        conn = sqlite3.connect('bookstore.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Orders (customer_email, book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method, card_number, expiry_date, cvv, quantity, order_date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (customer_email, book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method, card_number if payment_method == 'Credit Card' else None, expiry_date if payment_method == 'Credit Card' else None, cvv if payment_method == 'Credit Card' else None, quantity, datetime.now().isoformat(), 'Completed'))
        cursor.execute("UPDATE Books SET quantity = quantity - ? WHERE book_id = ?", (quantity, book_id))
        conn.commit()
        conn.close()
        db_helper.clear_cart(customer_email)
        session['cart_count'] = 0
        flash("Purchase successful! Thank you for your order.", 'success')
    else:
        flash("Insufficient stock!", 'danger')
    return redirect(url_for('customer_home'))

@app.route('/cart')
def cart():
    if 'user' not in session:
        flash("You must be logged in to access your cart.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    cart_items = db_helper.get_user_cart(customer_email)
    total = sum(item['price'] * item['quantity'] for item in cart_items) if cart_items else 0
    session['cart_count'] = sum(item['quantity'] for item in cart_items)
    return render_template('cart.html', cart=cart_items, total=total, **get_context())

@app.route('/update_cart', methods=['POST'])
def update_cart():
    if 'user' not in session:
        flash("You must be logged in to update your cart.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    book_id = request.form.get('book_id')
    quantity = int(request.form.get('quantity', 1))
    if quantity < 1:
        db_helper.remove_from_cart(customer_email, book_id)
        flash('Item removed from cart.', 'success')
    else:
        db_helper.update_cart_quantity(customer_email, book_id, quantity)
        flash('Cart updated successfully!', 'success')
    return redirect(url_for('customer_home'))

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user' not in session:
        flash("You must be logged in to remove items from your cart.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    book_id = request.form.get('book_id')
    if not book_id:
        flash("Invalid book selection.", 'danger')
        return redirect(url_for('customer_home'))
    db_helper.remove_from_cart(customer_email, book_id)
    flash('Item removed from cart.', 'success')
    return redirect(url_for('customer_home'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user' not in session:
        flash("You must be logged in to checkout.", 'warning')
        return redirect(url_for('customer_login'))
    
    customer_email = session['user']
    cart_items = db_helper.get_user_cart(customer_email)

    if not cart_items:
        flash("Your cart is empty.", 'danger')
        return redirect(url_for('customer_home'))

    payment_method = request.form.get('payment_method')
    card_number = request.form.get('card_number')
    expiry_date = request.form.get('expiry_date')
    cvv = request.form.get('cvv')
    paypal_email = request.form.get('paypal_email')
    paypal_password = request.form.get('paypal_password')

    if not payment_method:
        flash("Please select a payment method.", 'danger')
        return redirect(url_for('customer_home'))
    
    # Simulated Payment Validation
    if payment_method == "Credit Card":
        if not (card_number and expiry_date and cvv):
            flash("Please fill in all credit card details.", 'danger')
            return redirect(url_for('customer_home'))

        if not re.fullmatch(r"\d{16}", card_number):  # 16-digit card number
            flash("Invalid credit card number format!", 'danger')
            return redirect(url_for('customer_home'))

        if not re.fullmatch(r"\d{3,4}", cvv):  # CVV must be 3 or 4 digits
            flash("Invalid CVV format!", 'danger')
            return redirect(url_for('customer_home'))

    elif payment_method == "PayPal":
        if not (paypal_email and paypal_password):
            flash("Please fill in all PayPal details.", 'danger')
            return redirect(url_for('customer_home'))

    # Ensure stock is available
    insufficient_stock = False
    for item in cart_items:
        book = db_helper.get_book_by_id(item['book_id'])
        if not book or book['quantity'] < item['quantity']:
            insufficient_stock = True
            break

    if insufficient_stock:
        flash("One or more items are out of stock!", 'danger')
        return redirect(url_for('customer_home'))

    user = db_helper.get_user_profile_by_identifier(customer_email)
    if not user:
        flash("User not found.", 'danger')
        return redirect(url_for('customer_login'))

    shipping_street = user['street']
    shipping_city = user['city']
    shipping_state = user['state']
    shipping_zipcode = user['zipcode']

    conn = sqlite3.connect('bookstore.db')
    cursor = conn.cursor()
    
    for item in cart_items:
        cursor.execute("""
            INSERT INTO Orders (customer_email, book_id, shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method, quantity, order_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (customer_email, item['book_id'], shipping_street, shipping_city, shipping_state, shipping_zipcode, payment_method, item['quantity'], datetime.now().isoformat(), 'Completed'))

        cursor.execute("UPDATE Books SET quantity = quantity - ? WHERE book_id = ?", (item['quantity'], item['book_id']))

    conn.commit()
    conn.close()

    db_helper.clear_cart(customer_email)
    session['cart_count'] = 0

    flash("Purchase successful! Thank you for your order.", 'success')
    return redirect(url_for('customer_home'))

@app.route('/leave_review', methods=['GET', 'POST'])
def leave_review():
    if 'user' not in session:
        flash("You must be logged in to leave a review.", 'warning')
        return redirect(url_for('customer_login'))
    customer_email = session['user']
    book_id = request.args.get('book_id') if request.method == 'GET' else request.form.get('book_id')
    if not book_id:
        flash("Invalid book selection.", 'danger')
        return redirect(url_for('bookstore'))
    
    book = db_helper.get_book_by_id(book_id)
    if not book:
        flash("Book not found.", 'danger')
        return redirect(url_for('bookstore'))
    
    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()
        if not rating or rating < 1 or rating > 5:
            flash("Rating must be between 1 and 5.", 'danger')
        else:
            db_helper.add_review(customer_email, book_id, rating, comment)
            flash("Review submitted successfully!", 'success')
            return redirect(url_for('bookstore'))
    
    return render_template('leave_review.html', book=book, **get_context())

@app.route('/admin_dashboard', methods=['GET'])
def admin_dashboard():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
    
    supplier_orders = db_helper.get_all_supplier_orders()
    customer_orders = db_helper.get_all_orders()
    books = db_helper.get_all_books(page=1, per_page=1000)[0]
    wishlists = db_helper.get_all_wishlists()
    users = db_helper.get_all_users()
    reviews = db_helper.get_all_reviews()
    
    total_sales = sum(order['price'] * order['quantity'] for order in customer_orders if order['status'] == 'Completed')
    total_supplier_spend = sum(order['total'] for order in supplier_orders if order['total'] is not None)
    profit = total_sales - total_supplier_spend
    
    analytics = {
        'total_sales': total_sales,
        'total_orders': len(customer_orders),
        'pending_supplier_orders': len([o for o in supplier_orders if o['status'] == 'Pending']),
        'total_supplier_orders': len(supplier_orders),
        'total_supplier_spend': total_supplier_spend,
        'profit': profit,
        'total_books': len(books),
        'low_stock_books': len([b for b in books if b['quantity'] < 5]),
        'wishlist_items': len(wishlists),
        'total_users': len(users),
        'total_reviews': len(reviews),
        'average_rating': sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0
    }
    
    return render_template('admin_dashboard.html', 
                           supplier_orders=supplier_orders, 
                           customer_orders=customer_orders, 
                           books=books, 
                           wishlists=wishlists, 
                           users=users, 
                           reviews=reviews, 
                           analytics=analytics, 
                           **get_context())

@app.route('/admin_supplier_orders', methods=['GET', 'POST'])
def admin_supplier_orders():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
    
    supplier_orders = db_helper.get_all_supplier_orders()
    books = db_helper.get_all_books(page=1, per_page=1000)[0]
    suppliers = ["Supplier A", "Supplier B"]
    
    if request.method == 'POST' and 'order_book' in request.form:
        print("Form data:", dict(request.form))
        supplier = request.form.get('supplier')
        print("Supplier:", supplier)
        
        if not supplier:
            flash('Supplier is required!', 'danger')
            return redirect(url_for('admin_supplier_orders'))
        
        total_order_price = 0
        book_orders = []
        i = 0
        while True:
            book_id_key = f'book_id_{i}'
            quantity_key = f'quantity_{i}'
            if book_id_key not in request.form or quantity_key not in request.form:
                break
            book_id = request.form.get(book_id_key)
            quantity = request.form.get(quantity_key)
            print(f"Book ID {i}: {book_id}, Quantity {i}: {quantity}")
            
            if book_id and book_id.strip() and quantity and quantity.strip():
                try:
                    quantity = int(quantity)
                    if quantity <= 0:
                        flash(f'Quantity must be positive for book {i+1}!', 'danger')
                        return redirect(url_for('admin_supplier_orders'))
                    book = db_helper.get_book_by_id(book_id)
                    if not book or book.get('price') is None:
                        flash(f'Book {i+1} not found or invalid price!', 'danger')
                        return redirect(url_for('admin_supplier_orders'))
                    retail_price = book['price']
                    supplier_price = retail_price * 0.6
                    item_total = supplier_price * quantity
                    total_order_price += item_total
                    book_orders.append({
                        'book_id': book_id,
                        'quantity': quantity,
                        'supplier_price': supplier_price,
                        'item_total': item_total
                    })
                except ValueError as e:
                    flash(f'Invalid quantity for book {i+1}: {e}', 'danger')
                    return redirect(url_for('admin_supplier_orders'))
            i += 1
        
        if not book_orders:
            flash('At least one valid book and quantity are required!', 'danger')
            return redirect(url_for('admin_supplier_orders'))
        
        conn = sqlite3.connect('bookstore.db')
        cursor = conn.cursor()
        for order in book_orders:
            cursor.execute("INSERT INTO SupplierOrders (supplier, book_id, quantity, price, total, order_date, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (supplier, order['book_id'], order['quantity'], order['supplier_price'], order['item_total'], datetime.now().isoformat(), 'Pending'))
        conn.commit()
        conn.close()
        
        flash(f'Supplier order added successfully! Total: ${total_order_price:.2f}', 'success')
        return redirect(url_for('admin_supplier_orders'))
    
    return render_template('admin_supplier_orders.html', supplier_orders=supplier_orders, books=books, suppliers=suppliers, **get_context())

@app.route('/admin_customer_orders', methods=['GET'])
def admin_customer_orders():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
    customer_orders = db_helper.get_all_orders()
    return render_template('admin_customer_orders.html', customer_orders=customer_orders, **get_context())

@app.route('/admin_customer_wishlist', methods=['GET'])
def admin_customer_wishlist():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
    wishlists = db_helper.get_all_wishlists()
    return render_template('admin_customer_wishlist.html', wishlists=wishlists, **get_context())

@app.route('/admin_customer_info', methods=['GET'])
def admin_customer_info():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
    users = db_helper.get_all_users()
    return render_template('admin_customer_info.html', users=users, **get_context())

@app.route('/admin_inventory', methods=['GET', 'POST'])
def admin_inventory():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        if 'add_book' in request.form:
            try:
                title = request.form['title']
                author = request.form['author']
                genre = request.form['genre']
                price = float(request.form['price'])
                quantity = int(request.form['quantity'])
                isbn = request.form['isbn']
                description = request.form['description']
                publisher = request.form['publisher']
                date_published = request.form['date_published']
                db_helper.add_book(title, author, genre, price, quantity, isbn, description, publisher, date_published)
                flash('Book added successfully!', 'success')
            except ValueError as e:
                flash(f'Invalid input: {e}', 'danger')
        elif 'quantity' in request.form and 'book_id' in request.form:
            try:
                book_id = request.form['book_id']
                quantity = int(request.form['quantity'])
                if quantity < 0:
                    flash('Quantity cannot be negative!', 'danger')
                else:
                    db_helper.update_book_quantity(book_id, quantity)
                    flash('Book quantity updated successfully!', 'success')
            except ValueError as e:
                flash(f'Invalid quantity: {e}', 'danger')
        return redirect(url_for('admin_inventory'))

    books = db_helper.get_all_books(page=1, per_page=1000)[0]
    return render_template('admin_inventory.html', books=books, **get_context())

@app.route('/edit_book', methods=['GET', 'POST'])
def edit_book():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))

    book_id = request.args.get('book_id') if request.method == 'GET' else request.form.get('book_id')
    if not book_id:
        flash('Invalid book ID.', 'danger')
        return redirect(url_for('admin_inventory'))

    book = db_helper.get_book_by_id(book_id)
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('admin_inventory'))

    if request.method == 'POST':
        try:
            title = request.form['title']
            author = request.form['author']
            genre = request.form['genre']
            price = float(request.form['price'])
            quantity = int(request.form['quantity'])
            isbn = request.form['isbn']
            description = request.form['description']
            publisher = request.form['publisher']
            date_published = request.form['date_published']
            db_helper.update_book(book_id, title, author, genre, price, quantity, isbn, description, publisher, date_published)
            flash('Book updated successfully!', 'success')
            return redirect(url_for('admin_inventory'))
        except ValueError as e:
            flash(f'Invalid input: {e}', 'danger')

    return render_template('admin_inventory.html', books=db_helper.get_all_books(page=1, per_page=1000)[0], edit_book=book, **get_context())

@app.route('/remove_book', methods=['POST'])
def remove_book():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))

    book_id = request.form.get('book_id')
    if book_id:
        db_helper.remove_book(book_id)
        flash('Book removed successfully!', 'success')
    else:
        flash('Invalid book ID.', 'danger')
    return redirect(url_for('admin_inventory'))

@app.route('/complete_supplier_order', methods=['POST'])
def complete_supplier_order():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))

    order_id = request.form.get('order_id')
    if not order_id:
        flash('Invalid order ID.', 'danger')
        return redirect(url_for('admin_supplier_orders'))

    # Use db_helper to fetch the order
    conn = db_helper._get_connection()  # Already has row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT book_id, quantity, status FROM SupplierOrders WHERE order_id = ?", (order_id,))
    order = cursor.fetchone()  # Now a Row object: {'book_id': '1', 'quantity': 10, 'status': 'Pending'}
    if order and order['status'] == 'Pending':
        cursor.execute("UPDATE SupplierOrders SET status = 'Completed' WHERE order_id = ?", (order_id,))
        cursor.execute("UPDATE Books SET quantity = quantity + ? WHERE book_id = ?", (order['quantity'], order['book_id']))
        conn.commit()
        flash('Supplier order completed successfully!', 'success')
    else:
        flash('Order not found or not pending.', 'danger')
    conn.close()
    return redirect(url_for('admin_supplier_orders'))

@app.route('/cancel_supplier_order', methods=['POST'])
def cancel_supplier_order():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        flash('Please log in as an admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))

    order_id = request.form.get('order_id')
    if order_id:
        if db_helper.cancel_supplier_order(order_id):
            flash('Supplier order canceled successfully!', 'success')
        else:
            flash('Failed to cancel order—order may not be pending.', 'danger')
    else:
        flash('Invalid order ID.', 'danger')
    return redirect(url_for('admin_supplier_orders'))

@app.route('/logout')
def logout():
    is_admin = 'user' in session and db_helper.get_user_role(session['user']) == 'admin'
    session.pop('user', None)
    session.pop('cart_count', None)
    flash("Logged out successfully!", 'success')
    return redirect(url_for('admin_login' if is_admin else 'home'))

@app.route('/get_low_stock_count', methods=['GET'])
def get_low_stock_count():
    if 'user' not in session or db_helper.get_user_role(session['user']) != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    books = db_helper.get_all_books(page=1, per_page=1000)[0]
    low_stock_count = len([b for b in books if b['quantity'] < 5])
    return jsonify({'low_stock_count': low_stock_count})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', **get_context()), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)