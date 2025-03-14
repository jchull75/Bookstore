import re
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from database_helper import DatabaseHelper

db_helper = DatabaseHelper()

def register_routes(app):
    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/customer_login", methods=["GET", "POST"])
    def customer_login():
        if request.method == "POST":
            email = request.form["email"]
            password = request.form["password"]
            login_result = db_helper.login_user(email, password)
            if login_result:
                is_admin = login_result.get('is_admin', 0)
                if not is_admin:  # Customer account
                    session['email'] = email
                    session['role'] = db_helper.get_user_role(email)
                    session['cart'] = []
                    flash("✅ Login successful!", "success")
                    return redirect(url_for("bookstore"))
                else:
                    flash("❌ This is an admin account! Use Admin Login.", "error")
            else:
                flash("❌ Invalid credentials!", "error")
        return render_template("customer_login.html")

    @app.route("/admin_login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            login_result = db_helper.login_user(username, password)
            if login_result:
                is_admin = login_result.get('is_admin', 0)
                if is_admin and db_helper.get_user_role(username) == "admin":  # Admin account
                    session['username'] = username
                    session['role'] = "admin"
                    session['cart'] = []
                    flash("✅ Login successful!", "success")
                    return redirect(url_for("admin_dashboard"))
                else:
                    flash("❌ This is not an admin account! Use Customer Login.", "error")
            else:
                flash("❌ Invalid credentials!", "error")
        return render_template("admin_login.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            first_name = request.form["first_name"]
            last_name = request.form["last_name"]
            email = request.form["email"]
            password = request.form["password"]
            street = request.form["street"]
            city = request.form["city"]
            state = request.form["state"]
            zipcode = request.form["zipcode"]
            mailing_street = request.form.get("mailing_street") or None
            mailing_city = request.form.get("mailing_city") or None
            mailing_state = request.form.get("mailing_state") or None
            mailing_zipcode = request.form.get("mailing_zipcode") or None
            favorite_genre = request.form.get("favorite_genre") or None
            if email == "admin@example.com":
                flash("❌ The email 'admin@example.com' is reserved!", "error")
                return render_template("signup.html")
            if db_helper.register_user(first_name, email, password, favorite_genre=favorite_genre, 
                                      street=street, city=city, state=state, zipcode=zipcode,
                                      mailing_street=mailing_street, mailing_city=mailing_city,
                                      mailing_state=mailing_state, mailing_zipcode=mailing_zipcode,
                                      last_name=last_name):
                flash("✅ Signup successful! Please log in.", "success")
                return redirect(url_for("customer_login"))
            else:
                flash("❌ Signup failed! Email may already be in use.", "error")
        return render_template("signup.html")

    @app.route("/bookstore", methods=["GET", "POST"])
    def bookstore():
        if 'email' not in session and 'username' not in session:
            flash("❌ Please log in to access the bookstore.", "error")
            return redirect(url_for("customer_login"))
        
        first_name = None
        if 'email' in session and session.get('role') != 'admin':
            user_profile = db_helper.get_user_profile(session['email'])
            if user_profile:
                first_name = user_profile["first_name"]

        page = int(request.args.get("page", 1))
        per_page = 10
        search_query = request.args.get("search", None)
        books = []
        total_books = 0
        cart = session.get('cart', [])
        if request.method == "POST":
            if "search" in request.form:
                search_query = request.form.get("search_query", "").strip()
                if search_query:
                    books, total_books = db_helper.get_all_books(page=1, per_page=per_page, search_query=search_query)
                    page = 1
                else:
                    books, total_books = db_helper.get_all_books(page=1, per_page=per_page)
                    page = 1
            elif "browse" in request.form:
                search_query = None
                _, total_books = db_helper.get_all_books(page=1, per_page=1)
                books, _ = db_helper.get_all_books(page=1, per_page=total_books or 50)
                per_page = total_books
                page = 1
            elif "add_to_cart" in request.form:
                book_id = int(request.form["book_id"])
                quantity = int(request.form.get("quantity", 1))
                book = db_helper.get_book_by_id(book_id)
                if book and book["quantity"] >= quantity:
                    if 'cart' not in session:
                        session['cart'] = []
                    cart_item = next((item for item in session['cart'] if item["book_id"] == book_id), None)
                    if cart_item:
                        cart_item["quantity"] += quantity
                    else:
                        session['cart'].append({"book_id": book_id, "title": book["title"], "price": book["price"], "quantity": quantity})
                    session.modified = True
                    flash(f"✅ Added {quantity} x {book['title']} to cart!", "success")
                else:
                    flash("❌ Not enough stock available!", "error")
                books, total_books = db_helper.get_all_books(page, per_page, search_query)
            elif "add_to_wishlist" in request.form:
                book_id = int(request.form["book_id"])
                quantity = int(request.form.get("quantity", 1))
                book = db_helper.get_book_by_id(book_id)
                if book:
                    identifier = session.get('email') or session.get('username')
                    db_helper.add_to_wishlist(identifier, book_id, quantity)
                    flash(f"✅ Added {quantity} x {book['title']} to wishlist!", "success")
                else:
                    flash("❌ Book not found!", "error")
                books, total_books = db_helper.get_all_books(page, per_page, search_query)
            elif "remove_from_cart" in request.form:
                book_id = int(request.form["book_id"])
                if 'cart' in session:
                    session['cart'] = [item for item in session['cart'] if item["book_id"] != book_id]
                    session.modified = True
                    book = db_helper.get_book_by_id(book_id)
                    if book:
                        flash(f"✅ Removed {book['title']} from cart!", "success")
                    else:
                        flash("❌ Book not found in cart!", "error")
                books, total_books = db_helper.get_all_books(page, per_page, search_query)
        else:
            books, total_books = db_helper.get_all_books(page, per_page, search_query)
        total_pages = (total_books + per_page - 1) // per_page if total_books > 0 else 1
        return render_template("bookstore.html", books=books, cart=cart, page=page, total_pages=total_pages, 
                              search_query=search_query, per_page=per_page, first_name=first_name)

    @app.route("/cart", methods=["GET"])
    def cart():
        if 'email' not in session and 'username' not in session:
            flash("❌ Please log in to view your cart.", "error")
            return redirect(url_for("customer_login"))
        cart_items = session.get('cart', [])
        total = sum(item["price"] * item["quantity"] for item in cart_items)
        return render_template("cart.html", cart=cart_items, total=total)

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        if request.method == "GET":
            flash("❌ Please use the cart to checkout.", "error")
            return redirect(url_for("cart"))
        if 'email' not in session and 'username' not in session:
            flash("❌ Please log in to checkout.", "error")
            return redirect(url_for("customer_login"))
        if 'cart' not in session or not session['cart']:
            flash("❌ Your cart is empty!", "error")
            return redirect(url_for("cart"))
        payment_method = request.form.get("payment_method")
        if not payment_method or payment_method not in ["Credit Card", "PayPal", "Cash on Delivery"]:
            flash("❌ Please select a valid payment method!", "error")
            return redirect(url_for("cart"))
        if payment_method == "Credit Card":
            card_number = request.form.get("card_number", "").strip()
            expiry_date = request.form.get("expiry_date", "").strip()
            cvv = request.form.get("cvv", "").strip()
            if not (card_number and expiry_date and cvv):
                flash("❌ Please fill in all credit card details!", "error")
                return redirect(url_for("cart"))
            if len(card_number.replace(" ", "")) < 16 or len(cvv) < 3:
                flash("❌ Invalid credit card details!", "error")
                return redirect(url_for("cart"))
        elif payment_method == "PayPal":
            paypal_email = request.form.get("paypal_email", "").strip()
            if not paypal_email or "@" not in paypal_email:
                flash("❌ Please provide a valid PayPal email!", "error")
                return redirect(url_for("cart"))
        identifier = session.get('email') or session.get('username')
        user_profile = db_helper.get_user_profile(identifier if 'email' in session else db_helper.get_user_profile_by_username(identifier)["email"])
        if not user_profile:
            flash("❌ User profile not found!", "error")
            return redirect(url_for("customer_login"))
        shipping_street = user_profile["mailing_street"] or user_profile["street"] or "TBD"
        shipping_city = user_profile["mailing_city"] or user_profile["city"] or "TBD"
        shipping_state = user_profile["mailing_state"] or user_profile["state"] or "TBD"
        shipping_zipcode = user_profile["mailing_zipcode"] or user_profile["zipcode"] or "TBD"
        for item in session['cart']:
            book = db_helper.get_book_by_id(item["book_id"])
            if not book:
                flash(f"❌ Book with ID {item['book_id']} not found!", "error")
                return redirect(url_for("cart"))
            if book["quantity"] >= item["quantity"]:
                order_id = db_helper.add_order(
                    identifier if 'email' in session else db_helper.get_user_profile_by_username(identifier)["email"],
                    item["book_id"],
                    shipping_street,
                    shipping_city,
                    shipping_state,
                    shipping_zipcode,
                    payment_method,
                    item["quantity"]
                )
                if not order_id:
                    flash(f"❌ Failed to order {item['title']} - out of stock!", "error")
                    return redirect(url_for("cart"))
            else:
                flash(f"❌ Not enough stock for {item['title']}!", "error")
                return redirect(url_for("cart"))
        session['cart'] = []
        session.modified = True
        flash("✅ Order placed successfully!", "success")
        return redirect(url_for("bookstore"))

    @app.route("/order_from_wishlist", methods=["POST"])
    def order_from_wishlist():
        if 'email' not in session and 'username' not in session:
            flash("❌ Please log in to place an order.", "error")
            return redirect(url_for("customer_login"))
        book_id = int(request.form["book_id"])
        quantity = int(request.form["quantity"])
        payment_method = request.form.get("payment_method")
        if not payment_method:
            flash("❌ Please select a payment method!", "error")
            return redirect(url_for("profile"))
        identifier = session.get('email') or session.get('username')
        user_profile = db_helper.get_user_profile(identifier if 'email' in session else db_helper.get_user_profile_by_username(identifier)["email"])
        shipping_street = user_profile["mailing_street"] or user_profile["street"] or "TBD"
        shipping_city = user_profile["mailing_city"] or user_profile["city"] or "TBD"
        shipping_state = user_profile["mailing_state"] or user_profile["state"] or "TBD"
        shipping_zipcode = user_profile["mailing_zipcode"] or user_profile["zipcode"] or "TBD"
        book = db_helper.get_book_by_id(book_id)
        if book and book["quantity"] >= quantity:
            order_id = db_helper.add_order(
                identifier if 'email' in session else db_helper.get_user_profile_by_username(identifier)["email"],
                book_id,
                shipping_street,
                shipping_city,
                shipping_state,
                shipping_zipcode,
                payment_method,
                quantity
            )
            if order_id:
                db_helper.remove_from_wishlist(identifier, book_id)
                flash(f"✅ Ordered {quantity} x {book['title']} successfully!", "success")
            else:
                flash(f"❌ Failed to order {book['title']} - out of stock!", "error")
        else:
            flash(f"❌ Not enough stock for {book['title']}!", "error")
        return redirect(url_for("profile"))

    @app.route("/cancel_order", methods=["POST"])
    def cancel_order():
        if 'email' not in session and 'username' not in session:
            flash("❌ Please log in to cancel an order.", "error")
            return redirect(url_for("customer_login"))
        order_id = int(request.form["order_id"])
        if db_helper.cancel_order(order_id):
            flash("✅ Order canceled successfully!", "success")
        else:
            flash("❌ Could not cancel order - it may already be processed or not found!", "error")
        return redirect(url_for("admin_dashboard" if session.get('role') == 'admin' else "profile"))

    @app.route("/remove_from_wishlist", methods=["POST"])
    def remove_from_wishlist():
        if 'email' not in session and 'username' not in session:
            flash("❌ Please log in to manage your wishlist.", "error")
            return redirect(url_for("customer_login"))
        book_id = int(request.form["book_id"])
        identifier = session.get('email') or session.get('username')
        db_helper.remove_from_wishlist(identifier, book_id)
        flash("✅ Item removed from wishlist!", "success")
        return redirect(url_for("profile"))

    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        if 'email' not in session and 'username' not in session:
            flash("❌ Please log in to view your profile.", "error")
            return redirect(url_for("customer_login"))
        
        identifier = session.get('email') or session.get('username')
        if not identifier:
            flash("❌ Session invalid. Please log in again.", "error")
            return redirect(url_for("customer_login"))
        
        email = identifier if 'email' in session else db_helper.get_user_profile_by_username(identifier)["email"]
        user_profile = db_helper.get_user_profile(email)
        
        if not user_profile:
            flash("❌ User profile not found. Please log in again.", "error")
            return redirect(url_for("customer_login"))

        if request.method == "POST" and "update_profile" in request.form:
            first_name = request.form["first_name"].strip()
            last_name = request.form["last_name"].strip()
            email_new = request.form["email"].strip()
            street = request.form["street"].strip()
            city = request.form["city"].strip()
            state = request.form["state"].strip()
            zipcode = request.form["zipcode"].strip()
            mailing_street = request.form.get("mailing_street", "").strip() or None
            mailing_city = request.form.get("mailing_city", "").strip() or None
            mailing_state = request.form.get("mailing_state", "").strip() or None
            mailing_zipcode = request.form.get("mailing_zipcode", "").strip() or None
            if not (first_name and email_new and street and city and state and zipcode):
                flash("❌ All required fields must be filled!", "error")
            else:
                db_helper.update_user_profile(
                    email, first_name, last_name, email_new, street, city, state, zipcode,
                    mailing_street, mailing_city, mailing_state, mailing_zipcode
                )
                if 'email' in session:
                    session['email'] = email_new
                flash("✅ Profile updated successfully!", "success")

        orders = db_helper.get_user_orders(email)
        wishlist = db_helper.get_user_wishlist(email)
        wishlist_with_details = []
        for item in wishlist:
            book = db_helper.get_book_by_id(item["book_id"])
            if book:
                wishlist_with_details.append({
                    "book_id": item["book_id"],
                    "title": book["title"],
                    "author": book["author"],
                    "price": book["price"],
                    "quantity": item["quantity"]
                })
        return render_template("profile.html", profile=user_profile, orders=orders, wishlist=wishlist_with_details,
                              first_name=user_profile["first_name"], last_name=user_profile["last_name"])

    @app.route("/logout")
    def logout():
        session.pop('email', None)
        session.pop('username', None)
        session.pop('role', None)
        session.pop('cart', None)
        flash("✅ You have been logged out.", "success")
        return redirect(url_for("index"))

    def admin_required(func):
        def wrapper(*args, **kwargs):
            if 'email' not in session and 'username' not in session:
                flash("❌ Admin access required.", "error")
                return redirect(url_for("admin_login"))
            if session.get('role') != 'admin':
                flash("❌ Admin access required.", "error")
                return redirect(url_for("admin_login"))
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper

    @app.route("/admin", methods=["GET", "POST"])
    @admin_required
    def admin_dashboard():
        if request.method == "POST" and "cancel_order" in request.form:
            order_id = int(request.form["order_id"])
            if db_helper.cancel_order(order_id):
                flash("✅ Order canceled successfully!", "success")
            else:
                flash("❌ Could not cancel order - it may already be processed or not found!", "error")
            return redirect(url_for("admin_dashboard"))
        
        conn = db_helper._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email, wishlist FROM Users WHERE role = 'customer' AND wishlist != '[]'")
        wishlist_data = cursor.fetchall()
        conn.close()
        all_wishlists = []
        for email, wishlist_json in wishlist_data:
            wishlist = json.loads(wishlist_json)
            for item in wishlist:
                book = db_helper.get_book_by_id(item["book_id"])
                if book:
                    all_wishlists.append({
                        "email": email,
                        "book_id": item["book_id"],
                        "title": book["title"],
                        "author": book["author"],
                        "quantity": item["quantity"]
                    })
        
        customer_orders = db_helper.get_all_orders()
        supplier_orders = db_helper.get_all_supplier_orders()
        
        return render_template("admin_dashboard.html", wishlists=all_wishlists, customer_orders=customer_orders, supplier_orders=supplier_orders)

    @app.route("/admin/inventory", methods=["GET", "POST"])
    @admin_required
    def admin_inventory():
        if request.method == "POST":
            if "add_book" in request.form:
                title = request.form["title"]
                author = request.form["author"]
                genre = request.form["genre"]
                price = float(request.form["price"])
                quantity = int(request.form["quantity"])
                isbn = request.form["isbn"]
                description = request.form["description"]
                db_helper.add_book(title, author, genre, price, quantity, isbn, description)
                flash(f"✅ Book '{title}' added to inventory successfully!", "success")
            elif "adjust_quantity" in request.form:
                book_id = int(request.form["book_id"])
                new_quantity = int(request.form["quantity"])
                db_helper.update_book_quantity(book_id, new_quantity)
                flash("✅ Inventory quantity updated successfully!", "success")
            return redirect(url_for("admin_inventory"))
        books, _ = db_helper.get_all_books(page=1, per_page=50)
        return render_template("admin_inventory.html", books=books)

    @app.route("/admin/orders", methods=["GET", "POST"])
    @admin_required
    def admin_orders():
        if request.method == "POST" and "cancel_order" in request.form:
            order_id = int(request.form["order_id"])
            if db_helper.cancel_order(order_id):
                flash("✅ Order canceled successfully!", "success")
            else:
                flash("❌ Could not cancel order - it may already be processed or not found!", "error")
            return redirect(url_for("admin_orders"))
        orders = db_helper.get_all_orders()
        return render_template("admin_dashboard.html", orders=orders)

    @app.route("/admin/suppliers", methods=["GET", "POST"])
    @admin_required
    def admin_suppliers():
        if request.method == "POST":
            if "order_book" in request.form:
                book_id = int(request.form["book_id"])
                supplier = request.form["supplier"]
                quantity = int(request.form["quantity"])
                price = float(request.form["price"])
                total = db_helper.add_supplier_order(supplier, book_id, quantity, price)
                flash(f"✅ Ordered {quantity} x book ID {book_id} from {supplier}! Total: ${total:.2f}", "success")
            elif "cancel_supplier_order" in request.form:
                order_id = int(request.form["order_id"])
                if db_helper.cancel_supplier_order(order_id):
                    flash("✅ Supplier order canceled successfully!", "success")
                else:
                    flash("❌ Could not cancel order - it may already be processed or not found!", "error")
            return redirect(url_for("admin_suppliers"))
        books, _ = db_helper.get_all_books(page=1, per_page=50)
        supplier_orders = db_helper.get_all_supplier_orders()
        return render_template("admin_suppliers.html", books=books, supplier_orders=supplier_orders)

if __name__ == "__main__":
    app = Flask(__name__)
    app.secret_key = 'your_secret_key'  # Replace with a secure key
    register_routes(app)
    app.run(host='0.0.0.0', debug=True)