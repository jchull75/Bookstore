from flask import Flask, render_template, request, redirect, url_for, session, flash
from database_helper import DatabaseHelper
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
db_helper = DatabaseHelper()

# Sorting options for books
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

        if db_helper.register_user(first_name, last_name, email, username, password):
            flash('Signup successful! Please log in.')
            return redirect(url_for('customer_login'))
        flash('Signup failed—email or username may already be in use.')
    return render_template('signup.html', **get_context())

@app.route('/bookstore', methods=['GET', 'POST'])
def bookstore():
    """Fetch and display all books in the store."""
    page = request.args.get('page', 1, type=int)
    per_page = 9
    search_query = request.form.get('search', None) if request.method == 'POST' else None
    sort = request.args.get('sort', 'default')

    books, total_books = db_helper.get_all_books(page, per_page, search_query, sort)

    return render_template(
        'bookstore.html',
        books=books,
        page=page,
        total_pages=(total_books // per_page) + (1 if total_books % per_page > 0 else 0),
        sort=sort,
        sort_options=sort_options,
        **get_context()
    )

@app.route('/customer_login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']
        user = db_helper.login_user(identifier, password)
        if user:
            session['user'] = identifier
            return redirect(url_for('profile'))
        flash('Invalid credentials')
    return render_template('customer_login.html', **get_context())

@app.route('/profile', methods=['GET'])
def profile():
    """User Profile Page"""
    if 'user' not in session:
        return redirect(url_for('customer_login'))

    user = db_helper.get_user_profile_by_identifier(session['user'])
    if not user:
        flash('User not found. Please log in again.')
        return redirect(url_for('customer_login'))

    orders = db_helper.get_user_orders(user['email'])
    wishlist = db_helper.get_user_wishlist(user['email'])

    return render_template('profile.html', profile=user, orders=orders, wishlist=wishlist, **get_context())

@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    """Fix: Add missing route to add books to wishlist"""
    if 'user' not in session:
        flash("You must be logged in to add books to your wishlist.", "warning")
        return redirect(url_for('customer_login'))

    customer_email = session['user']
    book_id = request.form.get('book_id')

    if not book_id:
        flash("Invalid book selection.", "danger")
        return redirect(url_for('bookstore'))

    db_helper.add_to_wishlist(customer_email, book_id)
    flash("Book added to your wishlist!", "success")
    return redirect(url_for('bookstore'))

@app.route('/cart')
def cart():
    """Fix: Add missing cart page route"""
    if 'user' not in session:
        return redirect(url_for('customer_login'))

    customer_email = session['user']
    cart_items = db_helper.get_user_cart(customer_email)

    return render_template('cart.html', cart=cart_items, **get_context())

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
